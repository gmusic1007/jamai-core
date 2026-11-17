# Vision: everything MuseScore does, reachable by asking

Written 2026-11-17, at Jerry's request, so that nothing left by hand today is forgotten.

## The outcome

A person asks in words for anything MuseScore Studio does, from the first note to the published score:
"put a slur over these four notes", "repeat measures 1 to 8 with a second ending", "save it and put it
on MuseScore.com". jamai-core does it in the score they see. When it cannot, it says why, in one
sentence, and what it would take.

## Where we stand (jamai-core 0.4.0, MuseScore 4.7.7)

- **Live, in the open score:** notes, rests, tuplets, lyrics, measures, instruments, time signature,
  tempo, dynamics, staff, system and expression text, rehearsal marks, articulations, ornaments,
  fermatas, breaths, fingering, key signatures, line breaks, arpeggios, subtitle and composer, saving
  MusicXML, PDF and PNG. Tried on 2026-11-17: [README.md](README.md#tried-in-musescore-477-2026-11-17).
- **With no window:** export to 14 formats, parts, transposition, MP4 video, metadata.
- **Still by hand in MuseScore:** settings, palettes, the mixer, Muse Sounds, layout, clefs, chord
  symbols, crescendos, octave lines, saving .mscz, publishing to MuseScore.com or Audio.com.
- **Not built yet:** slurs and ties, repeats and voltas, several voices, copy and paste, grace notes.

What stands in the way, as measured on 2026-11-17:

| limit | seen |
|---|---|
| A plugin cannot run menu commands | MuseScore 4.7.7's plugin interface has no `cmd()` |
| A plugin cannot draw a line between two notes | a crescendo and an octave line, added from the plugin, left nothing |
| A chord symbol from a plugin crashes MuseScore | segmentation fault, first live run |
| Saving .mscz from a plugin holds MuseScore | an error dialog stayed open until someone clicked Abort |
| One window per score | the plugin reaches only the window where it was started |
| Publishing needs the person's account | MuseScore.com and Audio.com sign-in happen in MuseScore's window |

## Four ways in

| route | what it is | strength | weakness |
|---|---|---|---|
| **R1 plugin** | what jamai-core uses today: the plugin changes the open score | the person sees each change; undo works | limited to what the plugin interface allows (table above) |
| **R2 file** | write or edit the score as MusicXML (or the `.mscx` inside a `.mscz`), then let MuseScore read it | MusicXML has a tag for nearly everything left: `<harmony>` chord symbols, `<slur>` and `<tied>`, `<wedge>` hairpins, `<octave-shift>`, `<repeat>` and `<ending>`, `<voice>`, `<grace/>`, `<clef>`, `<print>` for layout | not live: the score is saved, changed, and opened again; MuseScore-only settings can be lost on the way through MusicXML |
| **R3 keys** | press MuseScore's own shortcuts in its window for the person (Ctrl+K chord symbol, S slur, < and > hairpins) | reaches anything the window can do | fragile: needs the window in front and nobody else typing; hard on Wayland; asks for the person's consent each time |
| **R4 upstream** | ask MuseScore, or contribute, so the plugin interface gains what is missing: lines between notes, a working chord symbol, saving .mscz, menu commands | the clean fix, for everyone who uses MuseScore plugins | MuseScore's timeline, not ours; then each person updates MuseScore |

Publishing to an account (MuseScore.com, Audio.com) is a fifth question: whether either service
offers a way to upload from outside its window. Not checked yet. Until then, jamai-core's own
publication (`jamai-publish-melody` and `jamai-hub`) is the route it controls.

## Each item, and its most likely route

| item | today | most likely route | done when |
|---|---|---|---|
| Several voices | not built | **R1**: the plugin's cursor already has a voice; give `addNote` a `voice` | two voices written live, read back from the saved MusicXML |
| Copy and paste | not built | **R1**: read the notes with `getScore`, write them again with `addNote` at the new place | measures 1 to 4 copied to 5 to 8 live |
| Repeats and voltas | not built | **R1** if the plugin can set a measure's repeat marks, else **R2** `<repeat>`, `<ending>` | a repeat with first and second ending, played back correctly |
| Slurs and ties | not built | **R2** `<slur>`, `<tied>`; **R4** for live | a slur over four notes, in MuseScore and in the PDF |
| Grace notes | not built | **R2** `<grace/>`; **R1** if the plugin interface offers it | an acciaccatura before a note, played back |
| Chord symbols | by hand (crashed MuseScore) | **R2** `<harmony>`; **R3** Ctrl+K; **R4** the crash fix | Am7 over a note, no crash, read back |
| Crescendos and diminuendos | by hand (nothing placed) | **R2** `<wedge>`; **R4** | a crescendo over two beats, heard in playback |
| Octave lines | by hand (nothing placed) | **R2** `<octave-shift>`; **R4** | an 8va over a measure, sounding an octave up |
| Clefs | by hand | **R2** `<clef>`; **R4** | a bass clef from measure 5 |
| Saving .mscz | by hand live; works with no window | **R2**: save MusicXML live, then `--export mscz`; **R4** | the open score saved as .mscz without a dialog |
| Layout (page size, spacing) | by hand | **R2**: MuseScore style files, applied by its converter (`-S style.mss`) | a score exported with a chosen page size and staff size |
| The mixer (volume, pan) | by hand; mute works live | **R2**: `<sound>` and part settings in the file; **R4** | the flute 6 dB quieter in the exported MP3 |
| Muse Sounds | installed by hand through Muse Hub | the converter already takes `--sound-profile "Muse Sounds"`: let `--export` pass it | an MP3 exported with Muse Sounds |
| Settings, palettes | by hand | settings stay the person's; palettes are not needed by an agent, which places markings directly | nothing to build: say so when asked |
| Publishing to MuseScore.com, Audio.com | by hand, with the person's account | first find out whether either offers an upload interface; until then MuseScore's own Publish button | a score published to the person's account from a sentence |

## How one item gets built

1. Open an issue for the item on gmusic1007/jamai-core, naming the route tried first.
2. Try R1. If MuseScore refuses, try R2. Record what MuseScore did, as on 2026-11-17.
3. Try it live in MuseScore, on a blank score, with the score saved and read back after each step.
4. Add the self-test check, update [CAPABILITIES.md](CAPABILITIES.md) and the table above, release.

An item that needs R3 asks the person first, every time: it presses keys in their window.
An item that needs R4 is proposed to MuseScore, with the measurement that shows the limit.
