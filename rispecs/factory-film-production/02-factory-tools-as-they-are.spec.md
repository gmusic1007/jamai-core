# 02 · What the factory already made that jamai-core can use as it is

## Status: ✅ the tools exist and were run · Issue: miadisabelle/mightyeagle#35 (Phase 5)

Part of `rispecs/factory-film-production/`. Read `SPEC.md` first. A sentence about `jamai-core`
ends with the file it was read from at `4826b74`.

U stands for a use: one factory tool, the exact command, and what it answers.

## Intent

The composer, and the agent composing with him, check a rendered piece with tools that already
exist and that read the files `jamai-core` writes. Nothing is installed inside the package and
nothing in it changes.

## Desired Outcome

- After a render, one command says what is in the MIDI or the WAV.
- A claim about a piece (its mode, its tempo, its length, that it is the same notes as another
  render) is written once and held against the rendered file, with an exit code a script reads.
- An acted voice clip is held to the record its engine wrote.
- A host that has the factory's music packages has every program `jamai-core` renders with.

## Current Reality

- The package's own order of work is: render before saying anything, then check what was
  written against what sounds, "Measure first, then claim".
  (`claude/jamai/skills/jamai/SKILL.md`)
- Its checks are read by a person: `jamai-midi.py` lists every note and `jamai-chords.py` names
  the chord on each beat. The first takes a file, the second a file and the beats per bar.
  Neither takes a claim to hold the piece to. (`listen/jamai-midi.py`, `listen/jamai-chords.py`,
  `claude/jamai/skills/jamai/SKILL.md`)
- The package is Python and shell with no `package.json` (the tree at `4826b74`). A factory tool
  is therefore a command it can call across a process boundary, and no dependency of the
  package.

## How the measurements below were made

On eury, on 2026-11-24:

```bash
# the package at 4826b74, writing into a scratch folder
render/jamai-render --out <scratch> --name first-light examples/first-light.abc
#   duration 46.6 s · gain 0 dB · first-light.abc .mid .wav .mp3 .svg · exit 0

# the factory's CLI, from the public registry
npm install @miadi/ava8@0.5.0        # ava8 --version → 0.5.0
```

`ava8` needs Node 18.17 or later. `npx @miadi/ava8 <verb>` runs it without installing. In the
blocks below, long output is cut with "…" and the exit code is written at the right of the last
line.

## Specification

### 1. Reading a rendered file back

**U1 · `ava8 measure <file.mid>`** answers what is in a MIDI: format, tracks, note count,
tempo events, meter, length, the range of each track, where tracks overlap, and the share of
each pitch class weighted by sounding duration.

```text
$ ava8 measure first-light.mid
midi        format 0, 1 track(s), division 480
notes       78, 0 unclosed
tempo       88.00 bpm @ tick 0
meter       4/4 @ tick 0
length      43.64 s
tracks
   0  "First Light"        ch 0    78 note(s)  C#4 61 – A5 81  span 20
classes
  D 31.28 %   A 20.32 %   G 14.06 %   E 9.37 %   F# 9.37 %   B 9.37 %   C# 6.25 %
```

**U2 · `ava8 measure <file.wav>`** answers what is in a WAV: sample rate, channels, length, and
the share of spectral magnitude between 2000 and 5000 Hz, which the atelier calls stridence.

```text
$ ava8 measure first-light.wav
wav         44100 Hz, 2 channel(s) mixed to mono, 2053632 sample(s), 46.57 s
stridence   26.56 % of spectral magnitude in 2000-5000 Hz — rejected
            (the thresholds are one musician's calibration on his own material.
             When nothing passes, say the number; do not move the bar.)
```

- It reads the stereo WAV `jamai-render` writes, as it is.
- Measured beside it: `jamai-measure.py` on the same file prints a duration of 93.14 s for the
  46.57 s of sound. Jerry's documentation of 0.4.4 lists `jamai-measure.py` as reading a mono WAV
  only. Until that changes, `ava8 measure` is the reader that takes the package's own render.
- It does not read an MP3. `ava8 measure first-light.mp3` exits 1 and names the three kinds of
  file it reads.
- The "rejected" verdict comes from thresholds calibrated on one musician's material, as the
  tool says itself. It is a number to read, not a refusal to deliver.

### 2. Holding a piece to a claim

**U3 · `ava8 verify <file.mid> [claims]`** holds a rendered MIDI to claims and exits 0 when
every claim held, 1 when one failed, 2 when the command was wrong or nothing was claimed.

| claim | holds |
|---|---|
| `--mode <name>`, `--min-purity <s>` | the share of sounding duration inside a mode, such as `"d major"`, `ddorian` or `"e phrygian"` |
| `--tempo <a,b,…>`, `--tempo-tolerance <bpm>` | the tempo events, in order |
| `--seconds <s>`, `--tolerance <s>` | the total length |
| `--notes <n>` | how many notes there are |
| `--kick <0,2,4,6>` | the eighth-note slots the kick lands on |
| `--source <f.mid>`, `--multiset` | that this render is the same notes as another (U4) |
| `--empty <LO-HI>` | a register band that holds no melodic note |
| `--json` | the whole verdict as JSON on stdout, for the record's `checks` part (01, DW2) |

```text
$ ava8 verify first-light.mid --mode "d major" --tempo 88 --seconds 43.6 --tolerance 3.5
  ok   mode  100.00 % of duration is inside d major
  ok   tempos  1 tempo event(s), matching the claim within 0.5 bpm
  ok   seconds  43.64 s, within 3.5 s of the claim
all 3 claim(s) held                                                  exit 0

$ ava8 verify first-light.mid --mode "d dorian" --tempo 120
 FAIL  mode  d dorian claims 100.00 % purity and the file measures 84.39 %. Outside: F# 9.37 % · C# 6.25 %
 FAIL  tempos  1 tempo event(s) claimed, 1 in the file: 88.00. …
2 of 2 claim(s) failed                                               exit 1

$ ava8 verify first-light.mid
nothing was claimed, so nothing was checked — this is not a pass     exit 2
```

- It is the package's own third step, "check what you wrote against what sounds"
  (`claude/jamai/skills/jamai/SKILL.md`), with a claim written down and an exit code.
- `--empty` has no default. The band left empty is the register a person sings in, and a default
  would publish a measurement of that person's voice. `verify` says on every run that no band
  was checked unless one is given.
- The failing tempo message repeats a trap the package's own skill lists: a bare `Q:` line in
  the body of a tune is ignored. (`claude/jamai/skills/jamai/SKILL.md`)

**U4 · `ava8 verify <file.mid> --source <other.mid>`** answers whether two renders are the same
notes. `ava8 midi <file.abc> -o <out.mid>` writes a MIDI from the same ABC through another
chain, abcjs, where the package uses `abc2midi` (`render/jamai-render`).

```text
$ ava8 midi first-light.abc -o first-light.ava8.mid
$ ava8 verify first-light.mid --source first-light.ava8.mid
  ok   source  78 notes, identical to the source in order and pitch   exit 0
```

- On this example the two chains agree note for note. One example is not every score: the
  package's skill lists a case where `abc2midi` sounds an octave below what is written
  (`claude/jamai/skills/jamai/SKILL.md`), and this command is how such a case shows.
- It gives gmusic1007/jamai-core#5 a measurement where it has an open question about two
  packages rendering ABC.

### 3. The programs on a host

**U5 · `miadi-music check`, `miadi-music env`, `miadi-music python <args>`.** On a host with the
factory's music packages, `check` lists every tool each part needs with the package that brings
it and exits 1 when one is missing, `env` prints the soundfont and the measuring Python as
`KEY=VALUE`, and `python` runs a pinned NumPy, SciPy and Pillow in their own venv.

```text
$ miadi-music check
ok       render   abc2midi      /usr/bin/abc2midi
ok       render   abcm2ps       /usr/bin/abcm2ps
ok       render   fluidsynth    /usr/bin/fluidsynth
ok       render   soundfont     /usr/share/sounds/sf2/FluidR3_GM.sf2
ok       measure  python        /usr/lib/miadi-music/venv/bin/python3 (numpy 1.26.4 scipy 1.13.1 pillow 10.4.0)
…
This host can render, measure and score to picture.                  exit 0

$ jamai doctor
…
Render chain: whole. You can render and publish a melody.            exit 0

$ miadi-music python /usr/bin/jamai-chords-audio.py first-light.wav
   ré majeur    +0.879   …   écart au deuxième : +0.196  — franc       exit 0
```

- `miadi-music-render` depends on `abcmidi`, `abcm2ps`, `librsvg2-bin`, `fluidsynth`,
  `fluid-soundfont-gm`, `ffmpeg` and `lame`. The `jamai` package depends on `abcmidi`,
  `fluidsynth`, `fluid-soundfont-gm`, `lame` and `ffmpeg`, and recommends `abcm2ps` and
  `librsvg2-bin`. (`packaging/deb/build.sh`) Every program `jamai-render` asks for is one
  `miadi-music-render` brings.
- `miadi-music env` reads `MIADI_MUSIC_SOUNDFONT` and falls back to `JAMAI_SOUNDFONT`, the
  package's own setting (`settings`). Both default to the same FluidR3 file.
- `jamai` 0.4.4 and `miadi-music` 0.1.0 are installed on eury side by side, and both checks
  pass there.
- The package's listen tools run under the factory's measuring Python without a change.
- Stands until someone says otherwise: each package keeps its own render chain over the same
  Debian programs, and neither depends on the other. On a Miadi host, `miadi-music-render` is
  what brings them. On any other host, `apt install jamai` brings them itself. The decision
  between the two packages is Jerry's and Guillaume's, in gmusic1007/jamai-core#5, and this is
  what was measured for it.

### 4. A voice clip and its record

**U6 · `ava8 acted <clip.wav> [claims]`** holds an acted voice clip to the JSON record its
engine wrote beside it (`clip.wav` and `clip.json`). Four claims are always checked: every tag of
the script reached the engine, the tagless text carries no bracket, the wav is as long as the
record states, and the consent names the person whose voice it is. `--tags` and `--min-rms-db`
add two more and have no default. Exit 0, 1 or 2 as for `verify`.

```text
$ ava8 acted first-light.wav
ava8: no record at …/first-light.json. The engine writes one beside each wav, and
without it there is nothing to hold the clip to.                     exit 2
```

- It takes a WAV and a record. A sentence spoken by `jamai-say` is an MP3 with no record
  (`broadcast/jamai-say`), so `ava8 acted` has nothing to hold it to. A clip rendered by
  `emotion-render` has both.
- It does not check whether the engine acted a tag out or said it aloud. The tool says so in
  its help.
- Not verified here: an acted clip rendered and then held. No voice is recorded in the account
  these commands ran in.

### 5. The score as pictures

**U7 · `ava8 frames <file.abc> -o <dir>`** writes one SVG per frame with a cursor on the
sounding note, and `ava8 render <file.abc> -o <out.svg>` engraves the score without a display.
Turning frames into a video is ffmpeg's work.

```text
$ ava8 frames first-light.abc -o frames --fps 2 --to 3000
Wrote 6 frames to frames                                             exit 0
```

- The package makes score videos with `jamai-scroll.py`, `jamai-score-video.py` and
  `jamai-musescore --video` (`README.md`). `ava8 frames` is one more way to the frames of a score
  video, from the ABC alone. Only the six frames above were made here. No video was assembled.

### 6. The film's timeline, for the composer

**U8 · The scenes pass of `miadi-film`** (`/scenes-timeline <episode> [video ...]` in the
plugin, `scenes_to_kdenlive.py <video>... --out <folder>` under it) answers where the film
leaves room for music: a Kdenlive project with the track "A2 Music (later)" and a guide at each
black, and `scenes.json` with the place and length of every scene and the seconds of black
between them.

- Read, not run in this pass. Episode 575 (miadi-chronicle://575) holds the first one, made on
  2026-11-13: two projects, 6 s of black between scenes.
- A composer needs no factory tool to use it. `scenes.json` is a file, and the numbers in it are
  the lengths a cue is composed to (01, DW4).

### 7. A composition folder and an episode

**U9 · `musical-composition-to-episode classify <ref>` and `linked --episode <name>`**
(`@miadi/musical-composition-to-episode` 0.3.11 on npm) read a studio composition folder
without writing to it, and say which compositions an episode records.

```text
$ musical-composition-to-episode classify nyro/ep256-jamai-relational-music-synopsis
nyro/ep256-jamai-relational-music-synopsis  compatible-legacy
$ musical-composition-to-episode linked --episode 2026-07-19-episode-256-jamai-relational-music-synopsis
1 composition link(s), 0 unresolvable on this host                   exit 0
```

- It reads a folder with a `composition.json`. `jamai-suno` reads the same kind of folder
  (`suno/README.md`).
- It is migration tooling for folders that predate the chronicle. It weaves a folder's
  provenance into an episode. It does not deliver a rendered piece, which is 01.

## What does not work as it is

| what | state on 2026-11-24 |
|---|---|
| `miadi-platform-events deliver` | On the open pull request jgwill/Miadi#1047. `npm view @miadi/platform-events` answers 404, and it needs `@miadi/hooks-core` 0.6.3 where npm has 0.6.2. Built from the branch in a scratch folder, `deliver --print` ran on the `jamai-render` files (01, DW8) |
| `ava8 measure` on an MP3 | Refused, exit 1. A published melody has an MP3 and no WAV (`publish/jamai-publish-melody`), so the audio of a published melody is measured only after it is rendered again with `jamai-render` |
| `ava8 acted` on a `jamai-say` sentence | No WAV and no record |
| A measuring implementation named canonical | Three exist: the scripts of the atelier plugin (jgwill/miadi-orchestration-kit#44), the venv of `miadi-music-measure`, and `@miadi/ava8-measure`. Naming one is another step of miadisabelle/mightyeagle#35 |

## Creative Advancement Scenarios

**Creative Advancement Scenario**: A claim is held before a piece leaves the workshop
**User Intent**: Jerry wants to know that the cue he is about to deliver is in the mode and at
the tempo he chose.
**Current Reality**: `jamai-render` has written the folder. The ABC says D mixolydian at 69.
**Natural Progression Steps**:
  1. `ava8 verify <slug>.mid --mode "d mixolydian" --tempo 69 --seconds <length> --json` runs
     on the MIDI.
  2. Every claim holds and the command exits 0, or one fails and the line names the notes
     outside the mode.
  3. The JSON verdict goes into the record beside the files.
**Achieved Outcome**: The piece leaves with the claims it was held to and the command that held
them.
**Supporting Features**: U1, U3, the record of 01.

**Creative Advancement Scenario**: An agent composing through `jamai-mcp` checks its own render
**User Intent**: JamAI wants to tell a person what a piece is only after reading what was
rendered.
**Current Reality**: The `jamai` skill tells it to render, then check, then claim
(`claude/jamai/skills/jamai/SKILL.md`). Its tools list notes and chords for a reader.
**Natural Progression Steps**:
  1. `jamai_render` writes the folder.
  2. The agent runs `ava8 measure` on the MIDI and on the WAV, as commands.
  3. It states the key, tempo and length it read, and says which of them it chose and which it
     measured.
**Achieved Outcome**: What the agent says about the piece is what the rendered files hold.
**Supporting Features**: U1, U2, U3.

## Boundaries

- Nothing here adds a dependency to `jamai-core` or changes one of its tools. Every use is a
  command run beside it.
- The thresholds and bands of the atelier are one musician's calibration. This folder moves
  none of them.
- No factory tool renders or publishes a piece in the composer's place (03, W4 and W8).
