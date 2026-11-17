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

## Starting it

```bash
jamai-musescore --install-plugin      # copies it into MuseScore's plugins folder (install.sh does it too)
```

Then in MuseScore, once: **Home → Plugins**, click **musescore-mcp-websocket** and **Enable**. Each
session: open a score, then start it from the **Plugins** menu. MuseScore 4.7 names it
musescore-mcp-websocket; older versions name it MuseScore API Server. The plugin must be running, not
only enabled, and it changes the score that is open.

**After updating the plugin, quit and reopen MuseScore.** MuseScore keeps its WebSocket with the copy
started first: starting the new copy only logs `QTcpServer::listen() called when already listening`, and
the old copy goes on answering. `jamai-musescore --live version` says which copy answers: an older one
replies `Unknown command: version`.

```bash
jamai-musescore --live ping           # "pong" when MuseScore is listening
jamai-musescore --live getScore
```

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
| `addInstrument` | `instrumentId` |
| `setStaffMute` | `staff`, `mute` |
| `setInstrumentSound` | `staff`, `instrumentId` |
| `processSequence` | `sequence`: a list of `{action, params}` applied in order |

The plugin's port is fixed at 8765 in its code. `JAMAI_MUSESCORE_LIVE_PORT` changes only where the
client looks, which the self-test uses to talk to a stand-in instead of a real MuseScore.
