import QtQuick 2.9
import MuseScore 3.0

MuseScore {
    id: root
    menuPath: "Plugins.MuseScore API Server"
    description: "Exposes MuseScore API via WebSocket (Clean Version)"
    version: "2.0"
    
    property var clientConnections: []
    property var selectionState: ({
        startStaff: 0,
        endStaff: 1,
        startTick: 0,
        elements: []
    })

    // ========================================
    // WEBSOCKET & MESSAGE PROCESSING
    // ========================================

    function processMessage(message, clientId) {
        console.log("Received message: " + message);
        try {
            var command = JSON.parse(message);
            var result = processCommand(command);
            api.websocketserver.send(clientId, JSON.stringify({
                status: "success",
                result: result
            }));
        } catch (e) {
            console.log("Error processing command: " + e.toString());
            api.websocketserver.send(clientId, JSON.stringify({
                status: "error",
                message: e.toString()
            }));
        }
    }

    // ========================================
    // jamai-core: MARKINGS, TEXT, SCORES (from the MuseScore Studio 4 handbook)
    // ========================================

    property var jamaiNames: ({
        articulation: {
            "staccato": "articStaccatoAbove", "staccatissimo": "articStaccatissimoAbove",
            "tenuto": "articTenutoAbove", "accent": "articAccentAbove", "marcato": "articMarcatoAbove",
            "portato": "articTenutoStaccatoAbove", "accent-staccato": "articAccentStaccatoAbove",
            "marcato-staccato": "articMarcatoStaccatoAbove", "stress": "articStressAbove",
            "unstress": "articUnstressAbove", "soft-accent": "articSoftAccentAbove",
            "up-bow": "stringsUpBow", "down-bow": "stringsDownBow", "harmonic": "stringsHarmonic",
            "snap-pizzicato": "pluckedSnapPizzicatoAbove", "left-hand-pizzicato": "pluckedLeftHandPizzicato",
            "open": "brassMuteOpen", "stopped": "brassMuteClosed"
        },
        ornament: {
            "trill": "ornamentTrill", "turn": "ornamentTurn", "inverted-turn": "ornamentTurnInverted",
            "turn-slash": "ornamentTurnSlash", "mordent": "ornamentMordent", "short-trill": "ornamentShortTrill",
            "tremblement": "ornamentTremblement", "haydn": "ornamentHaydn"
        },
        fermata: {
            "fermata": "fermataAbove", "short": "fermataShortAbove", "long": "fermataLongAbove",
            "very-short": "fermataVeryShortAbove", "very-long": "fermataVeryLongAbove"
        },
        breath: {
            "breath": "breathMarkComma", "tick": "breathMarkTick", "salzedo": "breathMarkSalzedo",
            "caesura": "caesura", "short-caesura": "caesuraShort"
        }
    })

    function jamaiAttached(cursor) {
        var found = [];
        try {
            var anns = cursor.segment.annotations;
            for (var i = 0; i < anns.length; i++) {
                if (anns[i].track === cursor.track) found.push({ name: anns[i].name, text: anns[i].text });
            }
        } catch (e) {}
        try {
            var el = cursor.element;
            if (el && el.articulations) {
                for (var j = 0; j < el.articulations.length; j++) found.push({ name: el.articulations[j].name, symbol: String(el.articulations[j].symbol) });
            }
            if (el && el.notes) {
                for (var k = 0; k < el.notes.length; k++) {
                    var subs = el.notes[k].elements || [];
                    for (var m = 0; m < subs.length; m++) found.push({ name: subs[m].name, text: subs[m].text, note: k });
                }
            }
        } catch (e2) {}
        return found;
    }

    // One marking on the element at the cursor. params.kind says which, see the table in musescore/README.md.
    function addElement(params) {
        var validation = validateParams(params, ["kind"]);
        if (!validation.valid) return validation;
        var kind = String(params.kind);
        var name = params.name !== undefined ? String(params.name) : "";

        return executeWithUndo(function() {
            syncStateToSelection();
            var cursor = createCursor();
            var target = cursor.element;
            if (!target) throw new Error("No element at the cursor");
            var el;
            var symbolKinds = { articulation: Element.ARTICULATION, ornament: Element.ORNAMENT,
                                fermata: Element.FERMATA, breath: Element.BREATH };
            var textKinds = { staffText: Element.STAFF_TEXT, systemText: Element.SYSTEM_TEXT,
                              expression: Element.EXPRESSION, rehearsalMark: Element.REHEARSAL_MARK,
                              chordSymbol: Element.HARMONY };

            if (symbolKinds[kind] !== undefined) {
                if (!name && (kind === "fermata" || kind === "breath")) name = kind;
                var table = jamaiNames[kind];
                if (!table[name]) throw new Error(kind + " name must be one of: " + Object.keys(table).join(", "));
                if ((kind === "articulation" || kind === "ornament") && target.type !== Element.CHORD)
                    throw new Error("an " + kind + " goes on a note, and the cursor is on a " + target.name);
                el = newElement(symbolKinds[kind]);
                el.symbol = table[name];
                cursor.add(el);
            } else if (textKinds[kind] !== undefined) {
                if (!params.text) throw new Error(kind + " needs text");
                el = newElement(textKinds[kind]);
                el.text = String(params.text);
                cursor.add(el);
            } else if (kind === "fingering") {
                if (!params.text) throw new Error("fingering needs text, such as 3");
                if (target.type !== Element.CHORD) throw new Error("fingering goes on a note, and the cursor is on a " + target.name);
                var which = params.note !== undefined ? Number(params.note) : 0;
                el = newElement(Element.FINGERING);
                el.text = String(params.text);
                target.notes[which].add(el);
            } else if (kind === "tempo") {
                var bpm = Number(params.bpm);
                if (!(bpm > 0)) throw new Error("tempo needs bpm");
                el = newElement(Element.TEMPO_TEXT);
                el.text = params.text ? String(params.text) : "<sym>metNoteQuarterUp</sym> = " + bpm;
                el.tempo = bpm / 60;
                el.tempoFollowText = false;
                cursor.add(el);
            } else if (kind === "keySignature") {
                var fifths = Number(params.fifths);
                if (!(fifths >= -7 && fifths <= 7)) throw new Error("keySignature needs fifths, from -7 (7 flats) to 7 (7 sharps)");
                el = newElement(Element.KEYSIG);
                el.concertKey = fifths;
                el.actualKey = fifths;
                cursor.add(el);
            } else if (kind === "layoutBreak") {
                var breaks = { "line": LayoutBreak.LINE, "page": LayoutBreak.PAGE, "section": LayoutBreak.SECTION };
                if (breaks[name || "line"] === undefined) throw new Error("layoutBreak name must be line, page or section");
                el = newElement(Element.LAYOUT_BREAK);
                el.layoutBreakType = breaks[name || "line"];
                cursor.add(el);
            } else if (kind === "arpeggio") {
                if (target.type !== Element.CHORD) throw new Error("an arpeggio goes on a chord");
                el = newElement(Element.ARPEGGIO);
                cursor.add(el);
            } else if (kind === "hairpin" || kind === "ottava") {
                el = newElement(kind === "hairpin" ? Element.HAIRPIN : Element.OTTAVA);
                if (kind === "hairpin") {
                    var hp = { "crescendo": 0, "decrescendo": 1, "cresc-line": 2, "dim-line": 3 };
                    if (hp[name || "crescendo"] === undefined) throw new Error("hairpin name must be crescendo, decrescendo, cresc-line or dim-line");
                    el.hairpinType = hp[name || "crescendo"];
                } else {
                    var ov = { "8va": 0, "8vb": 1, "15ma": 2, "15mb": 3, "22ma": 4, "22mb": 5 };
                    if (ov[name || "8va"] === undefined) throw new Error("ottava name must be 8va, 8vb, 15ma, 15mb, 22ma or 22mb");
                    el.ottavaType = ov[name || "8va"];
                }
                cursor.add(el);
                var beats = params.beats !== undefined ? Number(params.beats) : 4;
                try { el.spannerTicks = fraction(beats, 4); } catch (e3) {}
            } else {
                throw new Error("kind must be one of: articulation, ornament, fermata, breath, staffText, systemText, expression, rehearsalMark, chordSymbol, fingering, tempo, keySignature, layoutBreak, arpeggio, hairpin, ottava");
            }
            return { success: true, kind: kind, name: name, tick: cursor.tick, staff: cursor.staffIdx,
                     attachedHere: jamaiAttached(cursor) };
        });
    }

    // Title, subtitle, composer, lyricist or part name at the top of the score.
    function setScoreText(params) {
        var validation = validateParams(params, ["field", "text"]);
        if (!validation.valid) return validation;
        var fields = ["title", "subtitle", "composer", "lyricist", "part"];
        if (fields.indexOf(String(params.field)) < 0) return { error: "field must be one of: " + fields.join(", ") };
        return executeWithUndo(function() {
            curScore.addText(String(params.field), String(params.text));
            return { success: true, field: params.field, text: params.text };
        });
    }

    // A new score, which becomes the one the other actions change.
    function newScoreAction(params) {
        var title = params && params.title ? String(params.title) : "Untitled";
        var instrument = params && params.instrument ? String(params.instrument) : "piano";
        var measures = params && params.measures ? Number(params.measures) : 4;
        var score = newScore(title, instrument, measures);
        if (!score) return { error: "MuseScore did not create the score (instrument id " + instrument + "?)" };
        score.startCmd();
        score.addText("title", title);
        score.endCmd();
        return { success: true, title: title, instrument: instrument, measures: score.nmeasures,
                 note: "MuseScore 4 opens it in a window of its own, which this plugin does not reach: the other actions keep changing the score of the window the plugin was started in" };
    }

    // Open a file (mscz, musicxml, mid…) in MuseScore.
    function openScoreAction(params) {
        var validation = validateParams(params, ["path"]);
        if (!validation.valid) return validation;
        var score = readScore(String(params.path), false);
        if (!score) return { error: "MuseScore could not open " + params.path };
        return { success: true, path: params.path, note: "MuseScore 4 opens it in a window of its own, which this plugin does not reach: the other actions keep changing the score of the window the plugin was started in" };
    }

    // Save or export the active score. The format follows the extension: mscz, mscx, musicxml, mxl, pdf, png, svg, mid.
    function saveScoreAction(params) {
        var validation = validateParams(params, ["path"]);
        if (!validation.valid) return validation;
        if (!curScore) return { error: "No score open" };
        var path = String(params.path);
        var dot = path.lastIndexOf(".");
        if (dot < 0) return { error: "the path needs an extension, such as .mscz or .pdf" };
        var ext = path.substring(dot + 1).toLowerCase();
        var ok = writeScore(curScore, path.substring(0, dot), ext);
        return ok ? { success: true, path: path, format: ext } : { error: "MuseScore could not write " + path };
    }

    // jamai-core: the plugin's own version, so a client can tell this copy from an older one.
    function pluginVersion() {
        return { success: true, plugin: "musescore-mcp-websocket", variant: "jamai-core", version: "0.4.0",
                 actions: ["addDynamic", "addElement", "setScoreText", "newScore", "openScore", "saveScore", "version"] };
    }

    // jamai-core: a dynamic marking (f, mf, pp, sfz…) on the element at the cursor.
    function addDynamic(params) {
        var validation = validateParams(params, ["dynamic"]);
        if (!validation.valid) return validation;
        var name = String(params.dynamic);
        var allowed = ["pppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "ffff",
                       "fp", "pf", "sf", "sfz", "sff", "sffz", "sfp", "sfpp", "rf", "rfz", "fz"];
        if (allowed.indexOf(name) < 0) return { error: "dynamic must be one of: " + allowed.join(", ") };

        return executeWithUndo(function() {
            syncStateToSelection();
            var cursor = createCursor();
            if (!cursor.element) throw new Error("No element at the cursor");
            var glyph = { p: "dynamicPiano", m: "dynamicMezzo", f: "dynamicForte",
                          s: "dynamicSforzando", z: "dynamicZ", r: "dynamicRinforzando" };
            var text = "";
            for (var i = 0; i < name.length; i++) text += "<sym>" + glyph[name.charAt(i)] + "</sym>";

            var dyn = newElement(Element.DYNAMIC);
            dyn.text = text;
            // The type is what playback follows. Set it when this MuseScore exposes it.
            var typed = false;
            try {
                if (typeof DynamicType !== "undefined" && DynamicType[name.toUpperCase()] !== undefined) {
                    dyn.dynamicType = DynamicType[name.toUpperCase()];
                    typed = true;
                }
            } catch (e) {}
            cursor.add(dyn);

            // Read back what is now attached at this point of the score, as proof.
            var attached = [];
            try {
                var anns = cursor.segment.annotations;
                for (var j = 0; j < anns.length; j++) {
                    if (anns[j].track === cursor.track) attached.push({ name: anns[j].name, text: anns[j].text });
                }
            } catch (e2) {}
            return { success: true, dynamic: name, tick: cursor.tick, staff: cursor.staffIdx,
                     dynamicTypeSet: typed, attachedHere: attached };
        });
    }

    function processCommand(command) {
        console.log("Processing command: " + command.action);
        
        switch(command.action) {
            // Core operations
            case "getScore":                return getScore(command.params);
            case "syncStateToSelection":    return syncStateToSelection();
            case "ping":                    return "pong";
            case "undo":                    return undo();
            case "goToBeginningOfScore":    return goToBeginningOfScore();
            case "processSequence":         return processSequence(command.params);

            // Navigation
            case "getCursorInfo":           return getCursorInfo(command.params);
            case "goToMeasure":             return goToMeasure(command.params);
            case "goToFinalMeasure":        return goToFinalMeasure(command.params);
            case "nextElement":             return nextElement(command.params);
            case "prevElement":             return prevElement(command.params);
            case "nextStaff":               return nextStaff(command.params);
            case "prevStaff":               return prevStaff(command.params);

            // Selection
            case "selectCurrentMeasure":    return selectCurrentMeasure(command.params);
            case "selectCustomRange":       return selectCustomRange(command.params);

            // Notes & Music
            case "addNote":                 return addNote(command.params);
            case "addRest":                 return addRest(command.params);
            case "addTuplet":               return addTuplet(command.params);
            case "addLyrics":               return addLyrics(command.params);

            // Measures
            case "appendMeasure":           return appendMeasure(command.params);
            case "insertMeasure":           return insertMeasure(command.params);
            case "deleteSelection":         return deleteSelection(command.params);

            // Staff & Instruments
            case "addInstrument":           return addInstrument(command.params);
            case "setStaffMute":            return setStaffMute(command.params);
            case "setInstrumentSound":      return setInstrumentSound(command.params);
            case "setTimeSignature":        return setTimeSignature(command.params);
            case "setTempo":                return setTempo(command.params);
            case "addDynamic":              return addDynamic(command.params);
            case "version":                 return pluginVersion();
            case "addElement":              return addElement(command.params);
            case "setScoreText":            return setScoreText(command.params);
            case "newScore":                return newScoreAction(command.params);
            case "openScore":               return openScoreAction(command.params);
            case "saveScore":               return saveScoreAction(command.params);

            default:
                throw new Error("Unknown command: " + command.action);
        }
    }

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================

    function validateParams(params, required) {
        var missing = [];
        for (var i = 0; i < required.length; i++) {
            if (params[required[i]] === undefined) {
                missing.push(required[i]);
            }
        }
        return missing.length > 0 ? { error: "Missing required parameters: " + missing.join(", ") } : { valid: true };
    }

    function executeWithUndo(operation) {
        if (!curScore) return { error: "No score open" };
        
        curScore.startCmd();
        try {
            var result = operation();
            curScore.endCmd();
            return result;
        } catch (e) {
            curScore.endCmd(true);
            return { error: e.toString() };
        }
    }

    function getNoteName(note) {
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        return noteNames[note % 12];
    }

    function getDurationName(duration) {
        const durationNames = ["LONG","BREVE","WHOLE","HALF","QUARTER","EIGHTH","16TH","32ND","64TH","128TH","256TH","512TH","1024TH","ZERO","MEASURE","INVALID"];
        return durationNames[duration] || "UNKNOWN";
    }

    // ========================================
    // CURSOR MANAGEMENT
    // ========================================

    function createCursor(params) {
        if (!curScore) throw new Error("No score open");
        
        if (!params || Object.keys(params).length === 0) {
            params = selectionState;
        }
        
        var cursor = curScore.newCursor();
        cursor.inputStateMode = Cursor.INPUT_STATE_SYNC_WITH_SCORE;
        
        // Set track
        if (params.startStaff !== undefined) cursor.staffIdx = params.startStaff;
        if (params.voice !== undefined) cursor.voice = params.voice;
        
        // Position cursor
        if (params.rewindMode !== undefined) {
            cursor.rewind(params.rewindMode);
        } else if (params.startTick !== undefined) {
            try {
                cursor.rewindToTick(params.startTick);
            } catch (e) {
                console.log("rewindToTick failed, using manual navigation");
                cursor.rewind(0);
                while (cursor.tick < params.startTick && cursor.next()) {}
            }
        } else if (params.measure !== undefined) {
            cursor.rewind(0);
            for (var i = 0; i < params.measure && cursor.nextMeasure(); i++) {}
        } else {
            cursor.rewind(0);
        }
        
        // Set duration
        if (params.duration) {
            cursor.setDuration(params.duration.numerator || 1, params.duration.denominator || 4);
        }
        
        return cursor;
    }

    function initCursorState() {
        if (!curScore) return "No score open";
        
        return executeWithUndo(function() {
            var cursor = curScore.newCursor();
            cursor.rewind(0);

            var startTick = cursor.tick;
            cursor.next();
            var endTick = cursor.tick;
            var element = cursor.element;

            selectionState = {
                startStaff: cursor.staffIdx,
                endStaff: cursor.staffIdx + 1,
                startTick: startTick,
                elements: element ? [processElement(element)] : []
            };
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, endTick, 0, 0);
            
            return "Initialized at " + [startTick, endTick, 0, 0].join(',');
        });
    }

    // ========================================
    // ELEMENT PROCESSING
    // ========================================

    function processElement(element) {
        if (!element) return null;
        
        var base = {
            name: element.name,
            subtype: element.subtype,
            subtypeName: element.subtypeName,
            baseDuration: getDurationName(element.durationType ? element.durationType.type : 0),
            dotted: element.durationType ? element.durationType.dots : 0,
            durationTicks: element.actualDuration ? element.actualDuration.ticks : 0,
            tuplet: element.tuplet ? {   
                durationNumerator: element.tuplet.duration.numerator,
                durationDenominator: element.tuplet.duration.denominator,
            } : null
        };

        switch (element.name) {
            case "Note":
                return Object.assign(base, {
                    pitchMidi: element.pitch,
                    pitchName: getNoteName(element.pitch),
                    noteType: element.noteType,
                    accidental: element.accidental,
                    tieBack: element.tieBack,
                    tieForward: element.tieForward
                });
            
            case "Chord":
                return Object.assign(base, {
                    noteType: element.noteType,
                    notes: Object.keys(element.notes || {}).map(function(k) {
                        return {
                            pitchMidi: element.notes[k].pitch, 
                            pitchName: getNoteName(element.notes[k].pitch)
                        };
                    })
                });
                
            case "Rest":
                return base;
                
            default:
                return { name: element.name, properties: Object.keys(element) };
        }
    }

    // ========================================
    // CORE OPERATIONS
    // ========================================

    function undo() {
        return executeWithUndo(function() {
            cmd("undo");
            return { success: true, message: "Undo successful" };
        });
    }

    function goToBeginningOfScore() {
        var response = initCursorState();
        return { 
            success: true, 
            message: response, 
            currentSelection: selectionState,
            currentScore: getScoreSummary()
        };
    }

    function processSequence(params) {
        if (!curScore) return { error: "No score open" };
        if (!params.sequence) return { error: "No sequence specified" };

        var validCommands = [
            "getScore", "addNote", "addRest", "addTuplet", "appendMeasure", "deleteSelection",
            "getCursorInfo", "goToMeasure", "nextElement", "prevElement", "nextStaff", "prevStaff",
            "selectCurrentMeasure", "processSequence", "insertMeasure", "goToFinalMeasure",
            "goToBeginningOfScore", "setTimeSignature", "addLyrics", "addInstrument",    
            "setStaffMute", "setInstrumentSound", "setTempo", "addDynamic", "addElement", "setScoreText"
        ];

        try {
            for (var i = 0; i < params.sequence.length; i++) {
                var command = params.sequence[i];
                if (!validCommands.includes(command.action)) {
                    throw new Error("Invalid command: " + command.action);
                }
                processCommand(command);
            }
            return { success: true, message: "Sequence processed", currentSelection: selectionState };
        } catch (e) {
            return { error: e.toString() };
        }
    }

    // ========================================
    // NAVIGATION FUNCTIONS
    // ========================================

    function syncStateToSelection() {
        if (!curScore) return { error: "No score open" };

        try {
            var selection = curScore.selection;
            var startSegment = selection.startSegment;
            var endSegment = selection.endSegment;

            if (startSegment && endSegment) {
                var cursor = createCursor({
                    startTick: startSegment.tick,
                    startStaff: selection.startStaff    
                });

                var elements = [];
                while (cursor.tick < endSegment.tick && cursor.element) {
                    elements.push(processElement(cursor.element));
                    if (!cursor.next()) break;
                }

                selectionState = {
                    startStaff: selection.startStaff,
                    endStaff: selection.endStaff,
                    startTick: startSegment.tick,
                    elements: elements,
                    totalDuration: elements.reduce(function(a, b) { return a + (b.durationTicks || 0); }, 0)
                };

                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, error: "No valid selection found" };
            }
        } catch (e) {
            return { success: false, error: e.toString() };
        }
    }

    function getCursorInfo(params) {
        if (!curScore) return { error: "No score open" };
        
        syncStateToSelection();
        return { 
            success: true, 
            currentSelection: selectionState, 
            currentScore: params && params.verbose !== "false" ? getScoreSummary() : null
        };
    }

    function goToMeasure(params) {
        var validation = validateParams(params, ["measure"]);
        if (!validation.valid) return validation;

        return executeWithUndo(function() {
            var score = getScoreSummary();
            var measure = score.measures[params.measure - 1];
            var startTick = measure.startTick;
            
            var cursor = createCursor({ startTick: startTick, startStaff: selectionState.startStaff });
            var element = processElement(cursor.element);
            var staffIdx = selectionState.startStaff;
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };
            
            return { success: true, currentSelection: selectionState };
        });
    }

    function nextElement(params) {
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var numElements = params && params.numElements || 1;
            var success = true;
            for (var i = 0; i < numElements && success; i++) {
                success = cursor.next();
            }
            
            if (success) {
                var element = processElement(cursor.element);
                var startTick = cursor.tick;
                var staffIdx = cursor.staffIdx;
                
                // Check if we need to append a measure
                if (startTick + element.durationTicks >= curScore.lastSegment.tick) {
                    cmd("append-measure");
                }

                curScore.selection.clear();
                curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);

                selectionState = {
                    startStaff: staffIdx,
                    endStaff: staffIdx + 1,
                    startTick: startTick,
                    elements: [element],
                    totalDuration: element.durationTicks
                };
                
                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, message: "End of score reached" };
            }
        });
    }

    function prevElement(params) {
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var endTick = cursor.tick;
            var numElements = params && params.numElements || 1;
            var success = true;
            
            for (var i = 0; i < numElements && success; i++) {
                success = cursor.prev();
            }

            if (success) {
                var element = processElement(cursor.element);
                var startTick = cursor.tick;
                var staffIdx = cursor.staffIdx;
                
                curScore.selection.clear();
                curScore.selection.selectRange(startTick, endTick, staffIdx, staffIdx + 1);

                selectionState = {
                    startStaff: staffIdx,
                    endStaff: staffIdx + 1,
                    startTick: startTick,
                    elements: [element],
                    totalDuration: endTick - startTick
                };
                
                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, message: "Beginning of score reached" };
            }
        });
    }

    function nextStaff(params) {
        return executeWithUndo(function() {
            syncStateToSelection();

            if (selectionState.endStaff >= curScore.nstaves) {
                return { success: false, message: "Already at last staff" };
            }

            var newStaff = selectionState.endStaff;
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: newStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(
                selectionState.startTick, 
                selectionState.startTick + element.durationTicks, 
                newStaff, 
                newStaff + 1
            );

            selectionState = {
                startStaff: newStaff,
                endStaff: newStaff + 1,
                startTick: selectionState.startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, currentSelection: selectionState };
        });
    }

    function prevStaff(params) {
        return executeWithUndo(function() {
            syncStateToSelection();

            if (selectionState.startStaff <= 0) {
                return { success: false, message: "Already at first staff" };
            }

            var newStaff = selectionState.startStaff - 1;
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: newStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(
                selectionState.startTick, 
                selectionState.startTick + element.durationTicks, 
                newStaff, 
                newStaff + 1
            );

            selectionState = {
                startStaff: newStaff,
                endStaff: newStaff + 1,
                startTick: selectionState.startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, currentSelection: selectionState };
        });
    }

    function goToFinalMeasure(params) {
        return executeWithUndo(function() {
            var cursor = createCursor({ startTick: 0 });
            var count = 0;
            var startTick = 0;

            while (cursor.nextMeasure()) {
                startTick = cursor.tick;
                count++;
            }

            if (count === 0) {
                return { success: false, message: "Already at the last measure" };
            }

            cursor.rewindToTick(startTick);
            cursor.next();
            var endTick = cursor.tick;
            var staffIdx = cursor.staffIdx;
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, endTick, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [processElement(cursor.element)],
                totalDuration: endTick - startTick
            };

            return { success: true, currentSelection: selectionState };
        });
    }

    // ========================================
    // SELECTION FUNCTIONS
    // ========================================

    function selectCurrentMeasure() {
        return executeWithUndo(function() {
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var currTick = cursor.tick;
            var currStaff = cursor.staffIdx;
            var scoreSummary = getScoreSummary();

            var measureIdx = scoreSummary.measures.filter(function(measure) { 
                return measure.startTick <= currTick; 
            }).length - 1;
            
            var measure = scoreSummary.measures[measureIdx];
            var measureElements = measure.elements[`staff${currStaff}`];
            var totalDuration = measureElements.reduce(function(a, b) { 
                return a + (b.durationTicks || 0); 
            }, 0);
            var measureEndTick = measure.startTick + totalDuration;

            curScore.selection.clear();
            curScore.selection.selectRange(measure.startTick, measureEndTick, currStaff, currStaff + 1);

            selectionState = {
                startStaff: currStaff,
                endStaff: currStaff + 1,
                startTick: measure.startTick,
                elements: measureElements,
                totalDuration: totalDuration
            };

            return { 
                success: true, 
                message: `Selected measure ${measureIdx + 1}`, 
                currentSelection: selectionState
            };
        });
    }

    function selectCustomRange(params) {
        var validation = validateParams(params, ["startTick", "endTick", "startStaff", "endStaff"]);
        if (!validation.valid) return validation;

        return executeWithUndo(function() {
            var cursor = createCursor({ 
                startTick: params.startTick, 
                startStaff: params.startStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(params.startTick, params.endTick, params.startStaff, params.endStaff);

            selectionState = {
                startStaff: params.startStaff,
                endStaff: params.endStaff,
                startTick: params.startTick,
                elements: [element],
                totalDuration: params.endTick - params.startTick
            };

            return { success: true, message: "Selection updated", currentSelection: selectionState };
        });
    }

    // ========================================
    // NOTE & MUSIC OPERATIONS
    // ========================================

    function addNote(params) {
        var validation = validateParams(params, ["pitch", "duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.duration.numerator || !params.duration.denominator) {
            return { error: "Duration must be specified as { numerator: int, denominator: int }" };
        }

        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            
            // Check if current position has a rest
            var hasRest = selectionState.elements.some(function(element) { 
                return element.name === "Rest"; 
            });

            cursor.addNote(params.pitch, !hasRest);
            cursor.rewindToTick(selectionState.startTick);

            if (params.advanceCursorAfterAction) {
                cursor.next();
                // jamai-core: past the last element of the score there is nothing to move to.
                // Stay on what was just written, instead of failing and undoing it.
                if (!cursor.element) cursor.rewindToTick(selectionState.startTick);
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { 
                success: true, 
                message: "Note added with pitch " + params.pitch,
                currentSelection: selectionState
            };
        });
    }

    function addRest(params) {
        var validation = validateParams(params, ["duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.duration.numerator || !params.duration.denominator) {
            return { error: "Duration must be specified as { numerator: int, denominator: int }" };
        }

        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            cursor.addRest();
            cursor.rewindToTick(selectionState.startTick);

            if (params.advanceCursorAfterAction) {
                cursor.next();
                // jamai-core: past the last element of the score there is nothing to move to.
                // Stay on what was just written, instead of failing and undoing it.
                if (!cursor.element) cursor.rewindToTick(selectionState.startTick);
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);

            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, message: "Rest added", currentSelection: selectionState };
        });
    }

    function addTuplet(params) {
        var validation = validateParams(params, ["ratio", "duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.ratio.numerator || !params.ratio.denominator || 
            !params.duration.numerator || !params.duration.denominator) {
            return { error: "Ratio and duration must be specified as { numerator: int, denominator: int }" };
        }
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            
            var ratio = fraction(params.ratio.numerator, params.ratio.denominator);
            var duration = fraction(params.duration.numerator, params.duration.denominator);
            
            cursor.addTuplet(ratio, duration);
            cursor.next();

            if (params.advanceCursorAfterAction) {
                cursor.next();
                // jamai-core: past the last element of the score there is nothing to move to.
                // Stay on what was just written, instead of failing and undoing it.
                if (!cursor.element) cursor.rewindToTick(selectionState.startTick);
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { 
                success: true, 
                message: "Tuplet " + params.ratio.numerator + ":" + params.ratio.denominator + " added",
                currentSelection: selectionState
            };
        });
    }

    function addLyrics(params) {
        if (!params.lyrics || !Array.isArray(params.lyrics) || params.lyrics.length === 0) {
            return { error: "Lyrics must be specified as an array of strings" };
        }
        
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });
            
            var lyricsArray = params.lyrics.slice();
            var verse = params.verse || 0;
            var addedCount = 0;
            var skippedCount = 0;
            
            while (cursor.element && lyricsArray.length > 0) {
                var element = cursor.element;
                
                if (element.type === Element.CHORD || element.name === "Chord") {
                    var lyr = newElement(Element.LYRICS);
                    lyr.text = lyricsArray.shift();
                    lyr.verse = verse;
                    
                    cursor.add(lyr);
                    addedCount++;
                } else if (element.type === Element.REST || element.name === "Rest") {
                    skippedCount++;
                }
                
                if (!cursor.next()) break;
            }
            
            var finalElement = processElement(cursor.element) || selectionState.elements[0];
            var finalTick = cursor.tick;
            var staffIdx = cursor.staffIdx;
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: finalTick,
                elements: [finalElement],
                totalDuration: finalElement.durationTicks || selectionState.totalDuration
            };
            
            curScore.selection.clear();
            curScore.selection.selectRange(finalTick, finalTick + (finalElement.durationTicks || 0), staffIdx, staffIdx + 1);
            
            var message = `Added ${addedCount} lyrics`;
            if (skippedCount > 0) message += `, skipped ${skippedCount} rests`;
            if (lyricsArray.length > 0) message += `, ${lyricsArray.length} lyrics remaining`;
            
            return { 
                success: true, 
                message: message,
                addedCount: addedCount,
                skippedCount: skippedCount,
                remainingLyrics: lyricsArray,
                currentSelection: selectionState
            };
        });
    }

    // ========================================
    // MEASURE OPERATIONS
    // ========================================

    function appendMeasure(params) {
        return executeWithUndo(function() {
            var count = params && params.count || 1;
            
            for (var i = 0; i < count; i++) {
                cmd("append-measure");
            }
            
            return { 
                success: true, 
                message: count + " measure(s) appended",
                currentSelection: selectionState
            };
        });
    }

    function insertMeasure(params) {
        return executeWithUndo(function() {
            cmd("insert-measure");
            syncStateToSelection();
            
            return { 
                success: true, 
                message: "Measure inserted",
                currentSelection: selectionState
            };
        });
    }

    function deleteSelection(params) {
        return executeWithUndo(function() {
            if (params && params.measure) {
                createCursor({ measure: params.measure });
            }
            
            cmd("delete");
            
            return { 
                success: true, 
                message: "Selection deleted",
                currentSelection: selectionState
            };
        });
    }

    // ========================================
    // STAFF & INSTRUMENT OPERATIONS
    // ========================================

    function addInstrument(params) {
        var validation = validateParams(params, ["instrumentId"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            curScore.appendPart(params.instrumentId);
            return { success: true, message: "Instrument " + params.instrumentId + " added" };
        });
    }

    function setStaffMute(params) {
        var validation = validateParams(params, ["staff"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var staff = curScore.staves && curScore.staves[params.staff] || 
                       (typeof curScore.staff === "function" ? curScore.staff(params.staff) : null);
            
            if (staff) {
                staff.invisible = Boolean(params.mute);
                return { success: true, message: "Staff " + (params.mute ? "muted" : "unmuted") };
            } else {
                return { error: "Staff not found" };
            }
        });
    }

    function setInstrumentSound(params) {
        var validation = validateParams(params, ["staff", "instrumentId"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            cmd("instruments");
            return { success: true, message: "Instrument dialog opened, manual selection required" };
        });
    }

    function setTimeSignature(params) {
        var validation = validateParams(params, ["numerator", "denominator"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            var currTick = cursor.tick;
            var currStaff = cursor.staffIdx;

            var ts = newElement(Element.TIMESIG);
            ts.timesig = fraction(params.numerator, params.denominator);
            cursor.add(ts);

            return { 
                success: true, 
                message: "Time signature set to " + params.numerator + "/" + params.denominator
            };
        });
    }

    function setTempo(params) {
        var validation = validateParams(params, ["bpm"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            
            var tempo = newElement(Element.TEMPO_TEXT);
            tempo.tempo = params.bpm / 60.0;
            tempo.text = "♩ = " + params.bpm;
            
            cursor.add(tempo);
            
            return { success: true, message: "Tempo set to " + params.bpm + " BPM" };
        });
    }

    // ========================================
    // SCORE ANALYSIS
    // ========================================

    function getScore(params) {
        if (!curScore) return { error: "No score open" };
        
        try {
            return { success: true, analysis: getScoreSummary() };
        } catch (e) {
            return { error: e.toString() };
        }
    }

    function getScoreSummary() {
        if (!curScore) return { error: "No score open" };

        return executeWithUndo(function() {
            var tempState = selectionState;
            var score = {
                numMeasures: curScore.nmeasures,
                measures: [],
                staves: []
            };
            
            // Analyze staves
            for (var i = 0; i < curScore.nstaves; i++) {
                var staff = curScore.staves && curScore.staves[i] || 
                           (typeof curScore.staff === "function" ? curScore.staff(i) : null);
                
                score.staves.push({
                    name: `staff${i}`,
                    shortName: staff ? staff.shortName : "",
                    visible: staff ? !staff.invisible : true
                });
            }

            // Analyze measures
            var cursor = createCursor({startTick: 0});
            var measureBoundaries = [];

            // Get measure boundaries
            for (var i = 0; i < curScore.nmeasures; i++) {
                var measure = {
                    measure: i + 1, 
                    startTick: cursor.tick,
                    numElements: 0, 
                    elements: {}
                };

                for (var j = 0; j < curScore.nstaves; j++) {
                    measure.elements[`staff${j}`] = [];
                }

                measureBoundaries.push(cursor.tick);
                score.measures.push(measure);
                cursor.nextMeasure();
            }

            // Process elements for each staff
            for (var k = 0; k < curScore.nstaves; k++) {
                cursor.rewind(0);
                cursor.staffIdx = k;

                while (cursor.element) {
                    var measureIdx = measureBoundaries.filter(function(tick) {
                        return tick <= cursor.tick;
                    }).length - 1;

                    score.measures[measureIdx].numElements++;

                    var processedElement = processElement(cursor.element);
                    if (processedElement) {
                        processedElement.startTick = cursor.tick;
                        score.measures[measureIdx].elements[`staff${k}`].push(processedElement);
                    }

                    if (!cursor.next()) break;
                }
            }

            // Restore state
            selectionState = tempState;
            return score;
        });
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    onRun: {
        console.log("Starting MuseScore API Server (Clean Version) on port 8765");
        
        api.websocketserver.listen(8765, function(clientId) {
            console.log("Client connected with ID: " + clientId);
            clientConnections.push(clientId);
            
            api.websocketserver.onMessage(clientId, function(message) {
                processMessage(message, clientId);
            });
        });
    
        if (curScore) {
            initCursorState();
        }
    }
}