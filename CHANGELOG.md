# Changes

Notes for the documentation agent and for whoever releases the next version. Each entry says
what changed for a person or an agent using the package, and what was measured. The version
and the release are decided by Gérico.

## 0.5.0: listen/ hears a recording (2026-11-27)

Merged from branch `listen-analyse-261127` and pushed to `main` on Gérico's approval, the same
day. No apt package is built from it until a GitHub release is published for `v0.5.0`.

Why: on 2026-11-27 JamAI transcribed « Monde immonde » from a live video almost entirely
outside the package (faster-whisper and Demucs pip-installed into a scratch folder, librosa
borrowed from another project's Python, nine throwaway scripts). The audit is in
`~/.agents/briefs/jamai-core-analyse-261127/RAPPORT-AUDIT.md`. Three causes, each proved:
the MCP server offered no tool for a recording, the agent definition and the skill the agent
had loaded did not name them, and the two it found by chance were wrong on that take.

### Fixed

- **`jamai-measure.py` read a stereo WAV as mono.** On the live take (140 s, stereo) it said
  279.98 s and 64.6 BPM, with wrong pitch classes. It now reads any file ffmpeg reads (wav,
  m4a, mp3, mp4), mixed down to mono at 22 050 Hz: 139.99 s, 129.4 BPM (librosa: 129.2).
  The lines the drop watchers parse (`durée`, `pic`, `centroïde spectral`, the energy bands)
  keep their format, and their values move by less than 3 % on the recordings tried.
- **`jamai-chords-audio.py` chose between two chords made of the same notes alphabetically.**
  G6 and Em7, Asus4 and Dsus2: without the bass it could not do otherwise, and it called
  « Monde immonde » D major, « franc ». It now reads the bass apart from the chord, at 1.35 Hz
  per bin, and smooths the chord path (Viterbi). Chord roots right against the chart JamAI
  kept after listening and watching the video: 30 % → 68 % on the mix, 38 % → 73 % on the
  separated guitar (the session's librosa script: 58 %). Key: E minor, by two methods that agree.
- **Pitch-class profile of `jamai-measure.py`** came from 21.5 Hz bins: below 500 Hz a note
  landed on its neighbour's class. Now 1.35 Hz.

### Changed

- `jamai-chords-audio.py` works beat by beat by default (beats detected, or `--temps` from
  `jamai-measure.py --temps beats.json`), prints chord changes, a bar grid (`| Em | Em | B7 | B7 |`)
  with its pickup and its irregular bars, and the key two ways. `--fenetre <s>` keeps fixed
  windows, `--par-temps` adds one line per beat, `--json` gives everything as JSON. Its text
  output is not the same as before: nothing in the house parses it (checked).
- `jamai-measure.py` gives every beat, a local tempo per 10 s, `--temps <file>` and `--json`.
- `jamai-grille.py --bpm <n>` imposes the pulse measured by `jamai-measure.py`. On the
  separated voice of « Monde immonde » its own candidates (0.21, 0.42, 0.63 s) missed the
  beat (0.464 s). With `--bpm 129.4` it keeps 4/4 in eighths, the grid JamAI chose by hand.
- `jamai doctor` names ffmpeg for listen/ and lists the optional `listen+` libraries.
- New setting `JAMAI_LISTEN_VENV` (quiet, default `~/.local/share/jamai/listen-venv`).

### Added

- `jamai-separe.py`: the voice apart from the accompaniment, with Demucs (`voix.wav`,
  `accompagnement.wav`, or four stems). CPU by default: 6 min 47 s for 140 s with htdemucs_ft.
- `jamai-paroles.py`: lyrics word by word with times and confidence, with faster-whisper
  (large-v3 by default, CPU, about 3 min for 140 s). The docstring carries the several-pass
  method that worked on « Monde immonde ».
- `jamai-melodie.py`: the notes of a sung line, by basic-pitch (default) or pyin, written as
  MIDI for `jamai-grille.py`. On a line with 144 known notes: basic-pitch onset F1 0.70 and
  pitch 0.99 in 2 s, pyin 0.64 and 0.90 in 39 s, CREPE 0.43 and 0.95 in 459 s (not kept).
  Under a guitar every method fails (F1 ≤ 0.22). Separated first by `jamai-separe.py`, basic-pitch
  gets 0.44 back. `--une-voix` keeps one note at a time for `jamai-grille.py` (0.55 on the solo line).
- `jamai listen-setup [--dry-run]` installs those three tools' libraries, at the versions in
  `listen/requirements.txt`, into `JAMAI_LISTEN_VENV`. basic-pitch goes in with `--no-deps`
  so that TensorFlow (about 600 MB) is not pulled: its ONNX model runs on onnxruntime. The
  three tools re-run themselves in that environment, from a terminal or from `jamai-mcp`.
- `lib/jamai_audio.py` (numpy only: reading, onset envelope, tempo, beat tracking after Ellis
  2007, bass and treble chroma, chord scores, Viterbi smoothing, key two ways) and
  `lib/jamai_extras.py` (finding the listen environment).
- MCP: six tools, 16 → 22: `jamai_measure`, `jamai_chords_audio`, `jamai_grid`,
  `jamai_separate`, `jamai_lyrics`, `jamai_melody`. The server's instructions tell an agent to
  use them in order before writing a script of its own.
- Skill `jamai`: a section « Listening to a recording: the package's tools first ».
- Selftest: a `listen` section (10 checks, 13 with the MCP ones) on `tests/listen-grid.abc`,
  rendered stereo: length, 120 BPM, beats, 90 % of chord roots through a voice, the grid,
  E minor, an m4a, `listen-setup --dry-run`, the doctor line, the message when the libraries
  are missing. The old `jamai-measure.py` fails the measure check (75.05 s for a 37.52 s take).
  137 checks in all.

### Not done, on purpose

- music21 is not a dependency: its ABC import merges the voices and drops the lyrics (tested
  with music21 9.9.1), so it does not give the lead sheet JamAI built with it. The package's
  route is ABC → `musescore_export`. Lyrics and chord symbols still do not reach MusicXML
  through that route (they go through MIDI): an open item, see the audit.
- CREPE, essentia and madmom are not added (measured or reasoned in the audit).
- No tag and no GitHub release with the merge: the apt repository still serves 0.4.4.

### For the documentation agent

Documented facts that move: the number of commands (19 → 22), of MCP tools (16 → 22), of
selftest checks (137), the commands table (three listen/ rows, new wording for measure and
chords-audio), the new `jamai listen-setup` command and `JAMAI_LISTEN_VENV` setting, the
listen order of work in the skill. README.md is updated to match. The site is left to the
weekly documentation run.
