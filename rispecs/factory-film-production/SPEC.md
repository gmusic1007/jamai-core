# Factory film production: what the Miadi Factory brings to jamai-core

## Status: 📋 PROPOSED · specifications only, no code · Issue: miadisabelle/mightyeagle#35 (Phase 5)

This folder holds RISE specifications. RISE (Reverse-engineering, Intent, Specifications,
Exportation) is a way of writing what a piece of software is for and how it behaves, in prose
precise enough to build from, starting from what already runs. `jamai-core` had no `rispecs/`
folder at `4826b74`. This one exists so that what the factory brings is written where the package
lives, where its author can read it, change it or decline it.

Written on 2026-11-24 by Mia, an agent seat of the Miadi Factory on eury, at Guillaume's request
(Guillaume is William in this repository's issues). Read from `jamai-core` 0.4.4 at `4826b74`, the
head of `gmusic1007/jamai-core` `main` that day. Held by Episode 256 (miadi-chronicle://256), the
episode of Jerry's relation with JamAI, and placed in its talking circle to be read.

**How to read a sentence here.** A sentence about `jamai-core` ends with the file it was read
from at `4826b74`, in parentheses. A sentence about the factory names its package or its file.
What exists and what is proposed sit in separate sections, or the proposal is marked
**Proposed**. Nothing here asks Jerry a question and waits for the answer. Each statement says
what it rests on and what stands until someone says otherwise. A word from Jerry changes any of
it.

## Intent

When the factory makes a film in a Chronicle episode, the music of that film comes from Jerry's
workshop. These specifications say three things: what a piece or a spoken line arrives with so
that the episode holds it and the film editor places it, which factory tools already run on the
files `jamai-core` writes, and which part of the work each side answers for.

## Desired Outcome

1. A piece rendered with `jamai-core` arrives in an episode as one folder: the files
   `jamai-render` writes, a record of how they were made, whose piece it is and on what terms,
   and the place in the film it was made for.
2. A spoken line arrives with its words, its voice and its engine, and with the consent of the
   person whose voice it is when the voice is a person's.
3. The composer, or the agent composing with him, holds a rendered MIDI or an acted clip to what
   was claimed about it with one command that runs on the files as they are.
4. The film editor finds the piece in the episode's editing room, labelled with how it was made,
   and places it on the music track at the guide it was composed for.
5. Jerry, Guillaume and the agents of both platforms read in one place which part is the
   composer's and which is the production's, and change that reading in the talking circle
   where it is wrong.

## Current Reality

In `jamai-core` at `4826b74`:

- `jamai-render` turns ABC into a folder holding the ABC, a MIDI, a WAV, an MP3 and an engraved
  score page. It prints the duration and the gain, and keeps neither in a file.
  (`render/jamai-render`)
- `jamai-publish-melody` renders the same way, adds the melody to a page, records it in
  `melodies.json` and appends one fact to a ledger. The fact carries the sha256 of the MIDI and
  never the ABC source. (`publish/jamai-publish-melody`)
- `jamai-hub` posts each fact once to every subscriber, signed. (`publish/jamai-hub`)
- `jamai-say` speaks one sentence on a Chromecast speaker through an edge-tts voice and deletes
  its MP3 after playing unless `--garder` is given. (`broadcast/jamai-say`)
- `jamai-suno` sends a composition folder to Suno and keeps `call.json`, `result.json` and the
  takes of each generation. (`suno/README.md`)
- The package is Python and shell. It has no `package.json`, and the word Miadi appears in no
  file outside its own `.pde/` folder. It calls no factory tool. (the tree at `4826b74`,
  `git grep -il miadi`)

In the factory:

- `@miadi/ava8` 0.5.0 is public on npm. Its verbs `measure`, `verify` and `acted` read a rendered
  file back and hold it to claims (02).
- The Debian packages `miadi-music`, `miadi-music-render`, `miadi-music-measure`,
  `miadi-music-video` and `miadi-film` are installed on eury beside `jamai` 0.4.4.
- The plugin `miadi-film` 0.2.0 cuts a video into scenes on a timeline with black between them,
  an empty track named "Music (later)" and a guide at each black.
- An episode holds specifications, prototypes, reviews and other records through its doors, and
  it can record a studio composition folder woven into it (`source_composition` in
  `episode.yaml`). It has no holding for a rendered piece delivered for it.
- The film log, take ingest, score cues and consent per take are specified in Episode 120
  (miadi-chronicle://120) and not built.

Between the two:

- One piece has reached a film: op-021 « Sens partagé », composed by JamAI at Jerry's request
  for the film of Episode 044 (miadi-chronicle://044). On 2026-11-16 its score video was copied
  by hand into the episode with a README written on arrival.
- `@miadi/platform-events` 0.1.0 builds the event `miadi.composition.delivered` from a folder of
  files. It is on an open pull request, jgwill/Miadi#1047, and not on npm. The route that
  receives it answers 404 on eury.
- gmusic1007/jamai-core#5 has an open step: which of `jamai-core` and `miadi-music` renders ABC.

## Structural Tension

Jerry's workshop renders a piece, publishes it and tells its subscribers, with a digest of the
music in every announcement. The factory has an episode that holds records, an editing timeline
with an empty music track, and tools that read a rendered file back. A piece reached a film
once, by hand, described on arrival by the person who copied it. These specifications describe
the state where a piece arrives with what the episode and the editor read, where the checks run
on the composer's own files, and where each side knows its part.

## The parts

Read them in this order. Each stands alone.

| file | what it holds |
|---|---|
| `01-delivered-with.spec.md` | What lets the factory use `jamai-core` when it makes a film: the files, the record of how they were made, whose the piece is, the place in the film, the consent where a voice is involved, and the road into the episode. Rules DW1 to DW9 |
| `02-factory-tools-as-they-are.spec.md` | What the factory already made that `jamai-core` can use as it is: each tool with the exact command, what it answers, and what it answered on a `jamai-render` output. Uses U1 to U9 |
| `03-who-does-what.spec.md` | Our reading of the two parts: `jamai-core` is the composer's part and the factory is the production part, with the file each half is read from. Readings W1 to W9 |
| `factory-film-production.kin.md` | The people, episodes, repositories and threads these specifications are in relation with, and what each relation asks |
| `STATUS.md` | What exists, with the command that showed it, and what was not verified |

## What exists and what is proposed

| | exists | proposed here |
|---|---|---|
| The files of a piece | Written by `jamai-render` (`render/jamai-render`) | Delivered as they are, nothing converted (DW1) |
| A record of how a piece was made | None. The gain and duration are printed (`render/jamai-render`) | One JSON file beside the files (DW2) |
| Whose a piece is, and its terms | The software is MIT (`LICENSE`). No file states the terms of a piece | Stated in the delivery, in the composer's words (DW3) |
| The place in the film | The timeline's guides and `scenes.json`, written by `miadi-film` | A cue name and the black it answers (DW4) |
| The identity of the music | `midi_sha256` in every fact (`publish/jamai-publish-melody`) | The same number names the delivered piece (DW5) |
| A spoken line | `jamai-say` on a speaker (`broadcast/jamai-say`). The acted engine `emotion-render` 0.1.0 with its record | What a line is delivered with (DW6) |
| Consent | The engine's rule I2. The consent ledger of `@miadi/ava8-atelier` | Named in the delivery by reference (DW7) |
| The road into an episode | By hand. `miadi-platform-events deliver` on an open branch | Which road is used when (DW8) |
| The place in the episode | `music/op021-sens-partage-261116/` in Episode 044 | One folder per piece under `music/` (DW9) |
| Checks on a rendered file | `ava8 measure`, `ava8 verify`, `ava8 acted`, run here on `jamai-render` files | Nothing to build. The commands are in 02 |
| Who does what | Each package's own README | One reading, stated as a reading (03) |

## What stands until someone says otherwise

The statements below are choices, not measurements. Each is explained in the part it comes from.

- **DW1** The factory takes the folder `jamai-render` writes, unchanged.
- **DW2** Until a tool writes the record, the factory writes it at reception from the files and
  writes `unknown` for what they do not say.
- **DW3** With no terms stated, the production publishes nothing made with the piece.
- **DW6** A film's narrator lines are asked through the factory's own voice seam.
  `jamai-core` is not asked to speak them.
- **DW7** A delivery names a person's recording by reference and never carries it. With no
  consent named, the recording is treated as not offered.
- **DW8** A piece travels by hand into the episode, as op-021 did, until jgwill/Miadi#1047 is
  merged and its route is deployed.
- **U5** Each package keeps its own render chain over the same Debian programs, and neither
  depends on the other.
- **W4** The piece that is delivered is the one `jamai-core` rendered. The factory does not
  render it again.
- **W8** The composer publishes on his own page. The production publishes the film.

## Boundaries

- No file of `jamai-core` outside `rispecs/factory-film-production/` changes with these
  specifications.
- No change inside a tool of the package is specified. Each part describes what a tool's output
  is delivered with and what a tool can call.
- Nothing here publishes a piece, subscribes to a hub or delivers anything to an episode.
- The film's own specifications live in Episode 120's vessel, `rispecs/film-toolchain/`. What
  these specifications ask of them is proposed in that episode before anything is built.
- Naming one measuring implementation as canonical, and `melody.published` as a platform event,
  are other steps of miadisabelle/mightyeagle#35. The kin file names them. They are not
  specified here.
