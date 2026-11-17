# musescore/ — live control of the score open in MuseScore

`musescore-mcp-websocket.qml` is a MuseScore plugin. Once started, it listens on
`ws://127.0.0.1:8765` and applies the commands it receives to the open score: add a note, a rest,
a tuplet, lyrics, measures, an instrument, change the tempo or the time signature, move the cursor,
undo. Each change appears in the score as it is made, and MuseScore's own undo reverses it.

It comes from [Gerico1007/mcp-musescore-gmusic](https://github.com/Gerico1007/mcp-musescore-gmusic),
a fork of George Chen's MuseScore MCP server, under the MIT licence in `LICENSE` beside it.

One change from that copy, marked `jamai-core:` in the file. `addNote`, `addRest` and `addTuplet`
with `advanceCursorAfterAction` failed on the last element of a score: the cursor had nowhere to go,
the plugin threw "Value is null" and MuseScore undid the note. Found on 2026-11-17, writing the last
note of a flute part in MuseScore 4.7.7. The plugin now stays on the element it just wrote.

Two actions added here, also marked `jamai-core:`: `addDynamic`, for dynamic markings, and `version`,
which tells this copy from an older one still running in MuseScore.

## Tried in MuseScore 4.7.7, 2026-11-17

On a blank flute score, each marking on its own note, then saved and read back from the MusicXML
and the page image.

| result | what |
|---|---|
| placed, and in the saved file | staff text, system text, expression text, rehearsal mark; staccato, accent, tenuto, marcato; trill, mordent, turn; fermata; breath; fingering; tempo marking (with its playback speed); arpeggio; key signature; line break; `addDynamic mf`; subtitle and composer; saving .musicxml, .pdf and .png |
| refused with a message | chord symbol: it crashed MuseScore (segmentation fault) in the first run |
| refused, nothing was placed | crescendo hairpin, octave line |
| refused, blocked MuseScore | saving .mscz: an error dialog stayed open until someone clicked Abort |
| same code as a tried one, name not tried | the other articulation, ornament, fermata and breath names; page and section breaks; the other dynamics |

The composer text was added beside the "Composer / arranger" placeholder of a new score rather than
in place of it.

## One window per score

MuseScore 4 runs each score in its own window, and each window is its own program. The plugin
changes the score of the window where it was started, and only that one. Found on 2026-11-17 with
MuseScore 4.7.7: `newScore` and `openScore` opened their score in a new window, File → New did the
same, and the plugin went on seeing the first score. To work on another score, start the plugin in
that score's window. Only one window can hold the plugin's port (8765) at a time, so close the
window where it runs first.

## Starting it

The steps (install or update MuseScore, put the plugin in place, enable it once, start it each
session, check it answers, what to do when it does not) are in the main README:
[MuseScore: activate it, step by step](../README.md#musescore-activate-it-step-by-step).

## With no window: export, video, metadata

```bash
jamai-musescore --export pdf,mp3,musicxml song.mscz        # any of: mscz mscx pdf png svg mid musicxml mxl mei mp3 flac ogg wav aac
jamai-musescore --export pdf --parts song.mscz             # every part after the full score
jamai-musescore --export musicxml --transpose-semitones 2 song.mscz
jamai-musescore --video --resolution 1080p song.mscz       # MP4 of the score scrolling, with its audio
jamai-musescore --meta song.mscz                           # title, key, measures, parts… as JSON
```

These run MuseScore's own converter and need no plugin. An agent has them as `musescore_export` and
`musescore_video`. What each handbook page maps to: [CAPABILITIES.md](CAPABILITIES.md).

## How an agent uses it

`jamai-mcp` offers three tools that reach the running plugin: `musescore_live_status`,
`musescore_get_score` and `musescore_live`, which sends any action below. The client in
`lib/jamai_ws.py` uses only Python's standard library.

| action | params |
|---|---|
| `ping`, `getScore`, `getCursorInfo`, `undo` | none |
| `goToBeginningOfScore`, `goToFinalMeasure`, `nextElement`, `prevElement`, `nextStaff`, `prevStaff`, `selectCurrentMeasure`, `insertMeasure`, `deleteSelection`, `syncStateToSelection` | none |
| `goToMeasure` | `measure` |
| `addNote` | `pitch` (MIDI, 60 is middle C), `duration` `{numerator, denominator}`, `advanceCursorAfterAction` |
| `addRest` | `duration`, `advanceCursorAfterAction` |
| `addTuplet` | `duration`, `ratio` `{numerator, denominator}`, `advanceCursorAfterAction` |
| `addLyrics` | `lyrics` (list of syllables), `verse` (0 first) |
| `appendMeasure` | `count` |
| `selectCustomRange` | `startTick`, `endTick`, `startStaff`, `endStaff` |
| `setTimeSignature` | `numerator`, `denominator` |
| `setTempo` | `bpm` |
| `addDynamic` | `dynamic`: `pppp` to `ffff`, `mp`, `mf`, `fp`, `pf`, `sf`, `sfz`, `sff`, `sffz`, `sfp`, `sfpp`, `rf`, `rfz`, `fz`, on the element at the cursor |
| `version` | none: answers which copy of the plugin is running |
| `addElement` | `kind` and its fields, on the element at the cursor: articulation, ornament, fermata, breath (`name`); staffText, systemText, expression, rehearsalMark (`text`); fingering (`text`, `note`); tempo (`bpm`, `text`); keySignature (`fifths`); layoutBreak (`name`: line, page, section); arpeggio. Refused, with the reason: chordSymbol, hairpin, ottava. Every name: [CAPABILITIES.md](CAPABILITIES.md) |
| `setScoreText` | `field` (title, subtitle, composer, lyricist, part), `text` |
| `newScore` | `title`, `instrument` (a MuseScore instrument id such as piano, flute, violin), `measures` |
| `openScore` | `path` |
| `saveScore` | `path`: the extension picks the format (.musicxml, .mxl, .pdf, .png, .svg, .mid). .mscz is refused: from a plugin it opened an error dialog that held MuseScore |
| `addInstrument` | `instrumentId` |
| `setStaffMute` | `staff`, `mute` |
| `setInstrumentSound` | `staff`, `instrumentId` |
| `processSequence` | `sequence`: a list of `{action, params}` applied in order |

The plugin's port is fixed at 8765 in its code. `JAMAI_MUSESCORE_LIVE_PORT` changes only where the
client looks, which the self-test uses to talk to a stand-in instead of a real MuseScore.
