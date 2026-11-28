---
name: jamai
description: Listen to a recording, and write, hear, check and publish music from ABC notation with the jamai-core tools. Use when a person asks to transcribe a recording or a video (tempo, chords, key, lyrics, melody, a lead sheet), for a melody, a score, a tablature, the chords of a MIDI file, a score video, or to publish a melody so they can listen to it. Also use when a jamai tool fails and the install needs checking.
---

# jamai — music from ABC notation

The tools come from jamai-core. They are on the PATH once `install.sh` has run, and the same
ones are offered as MCP tools named `jamai_*`. Prefer the MCP tools when they are listed.
Otherwise run the commands.

If a tool is missing or fails, run `jamai doctor` first. It names each missing program, the
package that brings it, and what stops working without it.

## The order of work

1. **Write the ABC.** Headers `X:`, `T:`, `M:`, `L:`, `Q:`, `K:`. No blank line inside a tune:
   a blank line ends it and the render stops early.
2. **Render before you say anything about it.** `jamai-render file.abc` (MCP: `jamai_render`)
   writes MIDI, WAV, MP3 and an SVG score into a work folder. It publishes nothing.
3. **Check what you wrote against what sounds.** `jamai-chords.py file.mid 4` names the chord on
   every beat. `jamai-midi.py file.mid` lists every note. Measure first, then claim. When a
   measurement did not decide something, say that you chose.
4. **Publish only when the person asked.** `jamai-publish-melody --slug <name> --note "<note>" file.abc`
   (MCP: `jamai_publish_melody`) adds the melody to their page and prints the listen address.
   Give them that address.

## Listening to a recording: the package's tools first

When a person asks what is in a recording (a take, a live video, a phone memo), use these
before writing any analysis script of your own. Each one was measured on a real take, and each
says what it cannot hear. The MCP names are in brackets.

0. **A song with singing: separate first.** `jamai-separe.py take.wav` (`jamai_separate`) writes
   `voix.wav` and `accompagnement.wav`. A melody under a guitar is lost (12 % of note onsets
   found instead of 70 %). CPU by default; the GPU only when the person said it is free.
1. **Measure.** `jamai-measure.py take.wav --temps beats.json` (`jamai_measure`): duration, where
   it plays, timbre, tempo and every beat. Any format ffmpeg reads.
2. **Chords, grid and key.** `jamai-chords-audio.py accompagnement.wav --temps beats.json`
   (`jamai_chords_audio`): chord changes, a bar grid with its pickup and irregular bars, and
   the key decided two ways. Trust the root and major/minor; check 7ths, 9ths and sus by ear.
3. **Lyrics.** `jamai-paroles.py voix.wav --langue fr --json p1.json` (`jamai_lyrics`). Several
   passes (voice and mix, with and without `--enchaine`, with an `--invite` holding the title),
   keep what they agree on, mark the rest `[incertain]` with its time. Never complete a line.
4. **Melody.** `jamai-melodie.py voix.wav --une-voix --mid ligne.mid` (`jamai_melody`): the
   notes, by basic-pitch, as MIDI, one at a time as jamai-grille expects.
5. **Grid of the melody, then the score.** `jamai-grille.py ligne.mid --bpm <tempo of step 1>
   --abc ligne.abc` (`jamai_grid`) chooses the meter and the note values before writing. Without
   `--bpm` it guesses the pulse from the sung onsets, and on a live take that guess misses. Then render, check the
   chords of the render against step 2 with `jamai-chords.py`, and export with
   `musescore_export` (MusicXML, PDF).

Steps 0, 3 and 4 need the optional libraries: `jamai listen-setup` installs them once, and
`jamai doctor` lists them under `listen+`. If they are missing, say so and run steps 1, 2 and 5;
do not assemble the libraries by hand in a scratch folder.

## What each tool is for

| a person asks | tool |
|---|---|
| "let me hear it" | `jamai-render` |
| "what did I play?" (MIDI) | `jamai-midi.py` |
| "which chords?" (MIDI) | `jamai-chords.py <mid> <beats-per-bar>` |
| "which chords, which key, which grid?" (recording) | `jamai-chords-audio.py` |
| "what tempo, what structure?" (recording) | `jamai-measure.py` |
| "the voice alone", "the guitar alone" | `jamai-separe.py` |
| "the lyrics" | `jamai-paroles.py`, several passes |
| "the melody", "what does she sing?" | `jamai-melodie.py` on the separated voice |
| "write it down in bars" | `jamai-grille.py`, before writing the score |
| "with the tablature" | `jamai-tab.py file.abc --voix 1 --out tab.png` |
| "a video of the score" | `jamai-scroll.py` (scrolls left to right, red playhead) or `jamai-score-video.py` (one system at a time) |
| "what did we write before?" | `jamai-legacy list <folder>` |
| "open it in MuseScore" | `jamai-musescore file.abc` (`--no-open` to convert only) |
| "a PDF / an MP3 / MusicXML of it", "transpose it", "a video of the score" | `musescore_export`, `musescore_video` (`jamai-musescore --export`, `--video`) |
| "change it in MuseScore while I watch", "forte on that note", "a trill here", "tempo 72 here" | `musescore_live_status`, then `musescore_live` (or `jamai-musescore --live <action>`) |
| "publish it" | `jamai-publish-melody` |
| "who receives my music?" | `jamai-hub subscriptions` |

## Changing the score open in MuseScore

When the person has MuseScore open with the plugin running, `musescore_live` changes their score as
they watch. Check first with `musescore_live_status`; if it is not listening, tell the person the two
clicks it names, do not guess. The full activation (install MuseScore with `jamai-musescore
--install-musescore`, enable, start, check, troubleshoot) is the README section "MuseScore: activate it,
step by step". What stays by hand, and how it could be reached later: musescore/VISION.md. Read with `musescore_get_score` before writing. Move with `goToMeasure`,
then `addNote` / `addRest`, which advance the cursor. Every change can be reversed with `undo`, and the
person can press Ctrl+Z. Change only what was asked.

Markings go on the element at the cursor: move first, then `addElement` with its `kind` (articulation,
ornament, fermata, breath, staffText, systemText, expression, rehearsalMark, fingering, tempo,
keySignature, layoutBreak, arpeggio) or `addDynamic`. Chord symbols, crescendo hairpins and octave
lines are refused in MuseScore 4.7.7: tell the person to add them in MuseScore. Read the reply's `attachedHere`: it is what
MuseScore holds there now. What the plugin cannot do (clefs, slurs, repeats, settings) is listed in
musescore/CAPABILITIES.md; say so to the person rather than trying.

## Publishing and subscribers

`jamai-publish-melody` announces one fact after a publication:

- `melody.published` when the slug is new
- `melody.revised` when the slug existed and the music changed (the MIDI differs)
- nothing when the MIDI is byte-identical, so an engraving fix does not notify anyone twice

The hub (`jamai-hub serve`) sends each fact once to every subscriber, signed. The session note
stays on the page and out of the fact unless the person set `JAMAI_PUBLISH_NOTE_PUBLIC=1`.
Pass `--no-announce` when the person wants a publication without a notification.

## Traps that cost a session each

- `abcm2ps` refuses a rest of five eighths (`z5`). Write `z4 z`.
- Under `clef=treble-8`, `abc2midi` sounds an octave below what is written, and `abcm2ps` does
  not move the notes. Write the part an octave up under that clef.
- A bare `Q:` line in the body of a tune is ignored. Put the tempo in the header.
- General MIDI program 31 is an electric guitar sample in FluidR3 and stays bright at any
  velocity. For a soft guitar use program 24 (nylon).
- A quiet arrangement publishes quiet: one measured −26.5 LUFS. Pass `--gain-db` to
  `jamai-render` and `jamai-publish-melody`. The gain is linear with no limiter, so check the
  peak (`ffmpeg -i f.wav -af ebur128=peak=true -f null -`) before publishing. A gain change
  alone is not announced to subscribers, because the MIDI is the same.

## Settings

`jamai config show` lists every setting and where its value comes from. `jamai setup` asks
for them again. Nothing about where a person publishes is built into the tools.
