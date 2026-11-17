# What jamai-core reaches in MuseScore, page by page

Every page of the [MuseScore Studio 4 handbook](https://handbook.musescore.org/) (153 pages, read on
2026-11-17), and how jamai-core reaches what it describes. MuseScore 4.7.7 was the version tried.

| mark | meaning |
|---|---|
| **live** | an agent does it in the score open in MuseScore, through the plugin (`musescore_live`, `jamai-musescore --live`) |
| **export** | done with no window, by MuseScore's own converter (`musescore_export`, `musescore_video`, `jamai-musescore --export / --video / --meta`) |
| **jamai** | done by jamai-core's own tools, without MuseScore |
| **in MuseScore** | done by the person in MuseScore's window: settings, panels, accounts. The plugin interface MuseScore 4.7 offers has no way in |
| **not yet** | MuseScore's plugin interface allows it and jamai-core does not do it yet |

A plugin in MuseScore 4.7 cannot run MenuBar commands: its interface has no `cmd()`, so a feature
that exists only as a menu item or a panel stays **in MuseScore**.

## Introduction and navigation

| page | how |
|---|---|
| Download and installation | **in MuseScore**. `jamai doctor` says whether MuseScore is installed, and `install.sh` puts the plugin in place |
| Create your first score | **live** `newScore {title, instrument, measures}`, then `setScoreText`, `addInstrument` |
| Upgrading from earlier versions | nothing to do |
| Accessibility, The user interface, Timeline, Braille | **in MuseScore** |
| Navigating your score | **live** `goToMeasure`, `goToBeginningOfScore`, `goToFinalMeasure`, `nextElement`, `prevElement`, `nextStaff`, `prevStaff`, `getCursorInfo` |

## Basics

| page | how |
|---|---|
| Setting up your score | **live** `newScore`, `setScoreText` (title, subtitle, composer, lyricist), `addInstrument`, `setTimeSignature`, `addElement keySignature`, `addElement tempo` |
| Entering notes and rests | **live** `addNote`, `addRest`. **jamai**: write ABC, then `jamai-musescore` opens it |
| Working with multiple voices | **not yet** |
| Input by duration mode, Alternative note input methods | **in MuseScore** (a MIDI keyboard, the mouse). An agent enters notes by action instead |
| Adding and removing measures | **live** `appendMeasure`, `insertMeasure`, `deleteSelection` |
| Selecting elements | **live** `selectCurrentMeasure`, `selectCustomRange` |
| Editing notes and rests | **live** `deleteSelection`, `undo`. Changing the pitch of a written note: **not yet** |
| Copy and paste | **not yet** |
| Using the palettes, Properties panel, Adjusting elements directly | **in MuseScore**. An agent adds the palette's markings with `addElement` |
| Parts | **export** `--parts`: every part after the full score, in one PDF |
| Default keyboard shortcuts | **in MuseScore** |

## Notation

| page | how |
|---|---|
| Instruments and system markings | **live** `addInstrument`, `setInstrumentSound`, `setStaffMute` |
| Showing staves only where needed, Implode and explode, Mid-score instrument changes, Staff type change, Staff/Part properties, Brackets | **in MuseScore** |
| Time signatures | **live** `setTimeSignature` |
| Stems and flags, Beams, Regroup rhythms | **in MuseScore** |
| Tuplets | **live** `addTuplet` |
| Barlines, Measure numbering, Measure and multimeasure rests, Pickup and non-metered measures, Measure properties | **in MuseScore** |
| Clefs | **not yet**: MuseScore 4.7 does not let a plugin create a clef |
| Key signatures | **live** `addElement {kind: keySignature, fifths}` |
| Transposition | **export** `--transpose-semitones N` (−12 to 12), key signatures and chord symbols included |
| Octave lines | **live** `addElement {kind: ottava, name: 8va…, beats}` |
| Noteheads, Ambitus, Respell pitches | **in MuseScore** |
| Articulations | **live** `addElement {kind: articulation, name}`: staccato, staccatissimo, tenuto, accent, marcato, portato, accent-staccato, marcato-staccato, stress, unstress, soft-accent, up-bow, down-bow, harmonic, snap-pizzicato, left-hand-pizzicato, open, stopped |
| Dynamics and hairpins | **live** `addDynamic` (pppp to ffff, mp, mf, fp, pf, sf, sfz, sff, sffz, sfp, sfpp, rf, rfz, fz). Hairpins: `addElement {kind: hairpin, name: crescendo, decrescendo, cresc-line, dim-line, beats}` |
| Slurs and ties, Laissez vibrer ties | **not yet** |
| Breaths and pauses | **live** `addElement {kind: breath}` (breath, tick, salzedo, caesura, short-caesura) and `{kind: fermata}` (fermata, short, long, very-short, very-long) |
| Ornaments | **live** `addElement {kind: ornament, name}`: trill, turn, inverted-turn, turn-slash, mordent, short-trill, tremblement, haydn |
| Arpeggios and glissandos | **live** arpeggio `addElement {kind: arpeggio}`. Glissandos: **not yet** |
| Grace notes, Tremolos and rolls, Other lines, Other symbols | **not yet** |
| Repeat signs, Voltas, Jumps and markers, Items across repeats and jumps, Changes and courtesies, Measure and multimeasure repeats | **not yet**. **export** `--unroll-repeats` is available from MuseScore's converter |

## Idiomatic and alternative notation

| page | how |
|---|---|
| Keyboard: pedal | **not yet** |
| Cross-staff notation, Accordion notation | **in MuseScore** |
| Guitar: tablature | **jamai** `jamai-tab.py` draws a tablature from ABC. A tablature staff in MuseScore: **in MuseScore** |
| Fretboard diagrams, Guitar techniques, Capos, Alternate string tunings, Bends and dives | **in MuseScore** |
| Harp, Percussion (all four pages) | **in MuseScore** |
| Mensural notation, Slash notation, Custom staff types | **in MuseScore** |

## Text

| page | how |
|---|---|
| Entering and editing text | **live** `addElement {kind: staffText, systemText or expression, text}` |
| Formatting text | **in MuseScore** |
| Staff, system, and expression text | **live**, as above |
| Tempo markings | **live** `addElement {kind: tempo, bpm, text?}` (it sets playback speed too) and `setTempo` |
| Lyrics | **live** `addLyrics {lyrics: [syllables], verse}` |
| Fingering | **live** `addElement {kind: fingering, text, note?}` |
| Chord symbols | **live** `addElement {kind: chordSymbol, text: "Am7"}`. **jamai** names chords from MIDI or audio: `jamai-chords.py`, `jamai-chords-audio.py` |
| Figured bass | **not yet** |
| Rehearsal marks | **live** `addElement {kind: rehearsalMark, text}` |
| Header and footer | **in MuseScore** |
| Text blocks | **live** `setScoreText {field: title, subtitle, composer, lyricist, part}` |

## Formatting

| page | how |
|---|---|
| Systems and horizontal spacing (line breaks), Using sections | **live** `addElement {kind: layoutBreak, name: line, page or section}` |
| Page layout concepts, Positioning, Score size and spacing, Pages and vertical spacing, Frames, Images | **in MuseScore** |

## File management

| page | how |
|---|---|
| Opening and saving scores | **live** `openScore {path}`, `saveScore {path}` (.mscz, .musicxml, .pdf, .png, .svg, .mid) |
| Convert a file, File export, Working with MusicXML | **export**: mscz, mscx, pdf, png, svg, mid, musicxml, mxl, mei, mp3, flac, ogg, wav, aac. Braille (brf) fails in MuseScore 4.7.7's converter |
| Project properties | **export** `--meta` reads them as JSON |
| Backup and recovered files | **in MuseScore** |
| Publish to MuseScore.com | **in MuseScore**: it needs the person's MuseScore.com account. jamai-core's own publication is `jamai-publish-melody` (your page) and `jamai-hub` (subscribers by webhook) |
| Share on Audio.com | **in MuseScore**: it needs the person's Audio.com account |

## Sound, playback and video

| page | how |
|---|---|
| Playback controls, Mixer, SoundFonts, Muse Sounds, Online sounds, VST and VSTi | **in MuseScore**. Exported audio uses the sounds installed in MuseScore, Muse Sounds included |
| Sound flags, Swing playback | **not yet** |
| Working with MIDI | **jamai** `jamai-midi.py`, `jamai-render`. **export** to .mid |
| Exporting video | **export** `--video` (MP4: 720p to 2160p, 24, 30 or 60 fps). **jamai** `jamai-scroll.py` and `jamai-score-video.py` |
| Installing FFmpeg | nothing to do: MuseScore 4.7.7 made video without a separate install |

## Customization, support, appendix

| page | how |
|---|---|
| Plugins | **jamai** `jamai-musescore --install-plugin` |
| Language, Appearance, Toolbars, Templates and styles, Palettes, Workspaces, Keyboard shortcuts, Preferences | **in MuseScore** |
| Getting help, Revert to factory settings, Troubleshooting | **in MuseScore** |
| Command line usage | **export**: jamai-musescore wraps MuseScore's converter |
| All keyboard shortcuts, Changes for MDL percussion, Upgrade from 3.x, Glossary, Music fonts | reference only |
