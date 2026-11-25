# Status · 2026-11-24

Every command below was run on eury on 2026-11-24, between 22:13 and 22:30 EST, in the account
`mia`. "The render" is the folder that `render/jamai-render` at `4826b74` wrote from
`examples/first-light.abc`. Each exit code is the command's own, read without a pipe.

## What exists, with the command that showed it

### `jamai-core`

| what | command | answer |
|---|---|---|
| This branch starts from the package's head | `git rev-parse --short origin/main`, then the same for `upstream/main` | `4826b74` twice. `VERSION` is 0.4.4 |
| A render | `render/jamai-render --out <scratch> --name first-light examples/first-light.abc` | `duration 46.6 s`, `gain 0 dB (FluidSynth 0.9000)`, the files `.abc .mid .wav .mp3 .svg` and two logs, exit 0 |
| The package installed | `dpkg -l jamai`, `jamai doctor` | 0.4.4. "Render chain: whole", exit 0. `catt` and the MuseScore live plugin are missing for this account |
| It names no factory tool | `git grep -il miadi` | three files, all under `.pde/` |
| It holds no consent record | `git grep -ic consent` | one match, in `musescore/VISION.md` |
| Its package dependencies | `packaging/deb/build.sh`, `dpkg -s jamai` | Depends: bash, python3, abcmidi, fluidsynth, fluid-soundfont-gm, lame, ffmpeg, jq, curl. Recommends: abcm2ps, librsvg2-bin, imagemagick, python3-numpy, python3-scipy, python3-pil |

### The factory's tools, on the render

| what | command | answer |
|---|---|---|
| The CLI is public | `npm view @miadi/ava8 version`, and the same for `-measure` and `-atelier` | 0.5.0, 0.2.0, 0.2.0. `npm install @miadi/ava8@0.5.0` then `ava8 --version` answers 0.5.0 |
| A MIDI read back | `ava8 measure first-light.mid` | 78 notes, 88.00 bpm, 4/4, 43.64 s, D 31.28 %, exit 0 |
| A WAV read back | `ava8 measure first-light.wav` | 44100 Hz, 2 channels mixed to mono, 46.57 s, stridence 26.56 %, exit 0 |
| An MP3 is refused | `ava8 measure first-light.mp3` | "is not a readable artefact", exit 1 |
| Claims that hold | `ava8 verify first-light.mid --mode "d major" --tempo 88 --seconds 43.6 --tolerance 3.5` | "all 3 claim(s) held", exit 0 |
| Claims that fail | `ava8 verify first-light.mid --mode "d dorian" --tempo 120` | "2 of 2 claim(s) failed", 84.39 % inside the mode, exit 1 |
| No claim | `ava8 verify first-light.mid` | "nothing was claimed, so nothing was checked", exit 2 |
| Two chains, the same notes | `ava8 midi first-light.abc -o first-light.ava8.mid`, then `ava8 verify first-light.mid --source first-light.ava8.mid` | "78 notes, identical to the source in order and pitch", exit 0 |
| A clip with no record | `ava8 acted first-light.wav` | "no record at …/first-light.json", exit 2 |
| Score frames | `ava8 frames first-light.abc -o frames --fps 2 --to 3000` | "Wrote 6 frames", six SVG files, exit 0 |
| The package's own measurer on the same WAV | `miadi-music python /usr/bin/jamai-measure.py first-light.wav` | `durée : 93.14 s` for 46.57 s of sound, exit 0 |

### The factory's packages on the host

| what | command | answer |
|---|---|---|
| Installed | `dpkg -l` | `miadi-music`, `miadi-music-render`, `miadi-music-measure`, `miadi-music-video` 0.1.0, `miadi-film` 0.1.0 |
| The host can render and measure | `miadi-music check` | every line `ok`, "This host can render, measure and score to picture.", exit 0 |
| Its settings | `miadi-music env` | `MIADI_MUSIC_PYTHON=/usr/lib/miadi-music/venv/bin/python3`, `MIADI_MUSIC_SOUNDFONT=/usr/share/sounds/sf2/FluidR3_GM.sf2`, exit 0 |
| A listen tool under the measuring Python | `miadi-music python /usr/bin/jamai-chords-audio.py first-light.wav` | `ré majeur +0.879`, exit 0 |
| The film plugin | `claude/miadi-film/.claude-plugin/plugin.json` in `jgwill/miadi-orchestration-kit` at `48a391e` | 0.2.0 |
| The acted engine | `emotion-render --version`, then `--check --voice nobody --text "Hello [sigh] there." --out <file.wav>` | `0.1.0`, exit 0. `REFUSED … Known voices: none`, exit 2, no file written |
| A composition folder and its episode | `musical-composition-to-episode classify nyro/ep256-jamai-relational-music-synopsis`, then `linked --episode 2026-07-19-episode-256-jamai-relational-music-synopsis` | `compatible-legacy`, exit 0. "1 composition link(s), 0 unresolvable on this host", exit 0. `npm view @miadi/musical-composition-to-episode version` answers 0.3.11 |

### The delivery

| what | command | answer |
|---|---|---|
| The package is not released | `npm view @miadi/platform-events` | E404. `npm view @miadi/hooks-core version` answers 0.6.2, and the branch needs 0.6.3 |
| It is on an open pull request | `gh pr view 1047 -R jgwill/Miadi` | open, branch `mentorship-webhook` at `84fb49c` |
| It builds | `tsc -p packages/hooks-core/tsconfig.build.json`, then the same for `packages/platform-events`, in a scratch clone | exit 0 twice |
| It describes the render | `miadi-platform-events deliver --episode 256 --composition first-light --purpose "…" --composer JamAI --file first-light.mp3 --file first-light.mid --file first-light.svg --file first-light.abc --print` | one `miadi.composition.delivered` event with four files, roles `audio`, `midi`, `image`, `score`, each sha256 equal to `sha256sum`. Nothing sent. Exit 0 |
| The route is not deployed here | `POST $MIADI_API_URL/api/deliveries/compositions` with no token | 404 |
| What git keeps of a piece | `git check-ignore -v` on names under `music/` in the episodes repository | `.wav` ignored outside `keep/`. `.mp3 .mid .svg .abc .json` not ignored |

## State of each part

| part | state |
|---|---|
| `01-delivered-with.spec.md` | Proposed. Nothing of it is built. Its current reality is read and measured |
| `02-factory-tools-as-they-are.spec.md` | The tools exist. U1 to U7 and U9 were run. U8 was read, not run |
| `03-who-does-what.spec.md` | A reading. Nobody it describes has read it yet |
| The talking circle | Opened on 2026-11-24 in Episode 256's Root Circle. These specifications are placed there |
| A pull request to `gmusic1007/jamai-core` | Not opened. The factory's coordinating session opens it after reading these files |

## Not verified

- No acted clip was rendered or held. No voice is recorded in the account these commands ran in.
- `jamai-say` was read and not run. It needs a Chromecast speaker and `catt`.
- `jamai-publish-melody`, `jamai-hub`, `jamai-musescore` and `jamai-suno` were read and not run.
- The scenes pass of `miadi-film` was not run here. Its `scenes.json` was read in Episode 575.
- `miadi-platform-events deliver` was run with `--print` only. No delivery was sent, and the
  receiving route was not exercised.
- The two MIDI chains were compared on one example, the eight written bars of
  `examples/first-light.abc`.
- No frame sequence was turned into a video.
- Jerry's documentation was read from copies of what his pipeline wrote on 2026-11-24. The
  published site was not opened.
- Nobody the specifications describe has read them.

## Next

1. The circle reads the statements of `03-who-does-what.spec.md`, and the files change from what
   is said there.
2. The factory's coordinating session reads the folder and opens the pull request to
   `gmusic1007/jamai-core`.
3. The proposals for the editing room and the ScoreCue (01, DW9) are written in Episode 120
   before anything is built.
