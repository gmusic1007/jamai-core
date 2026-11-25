# 01 · What a piece or a spoken line is delivered with

## Status: 📋 PROPOSED, nothing built here · Issue: miadisabelle/mightyeagle#35 (Phase 5)

Part of `rispecs/factory-film-production/`. Read `SPEC.md` first. A sentence about `jamai-core`
ends with the file it was read from at `4826b74`.

DW stands for a rule about what something is delivered with.

## Intent

A piece composed in Jerry's workshop for a film arrives in the episode of that film with
everything the episode and the film editor read. Nobody describes it again on arrival, and
nothing about how it was made is lost between the workshop and the edit.

## Desired Outcome

- The episode holds the piece as one folder whose files, record and terms can be read by a
  person and by a tool.
- The film editor sees, in the editing room, what the piece is, how it was made and which place
  in the film it was composed for.
- The same music is recognised as the same music on Jerry's melody page, in the delivery and in
  the edit, by one number.
- A spoken line is never in the edit without its words, its voice and, when the voice is a
  person's, that person's consent.

## Current Reality

### What `jamai-core` writes today

- `jamai-render` writes `NAME.abc`, `NAME.mid`, `NAME.wav`, `NAME.mp3` and, when `abcm2ps` is
  present, `NAME.svg` into one folder, `$JAMAI_STATE_DIR/renders/NAME` unless `--out` names
  another. (`render/jamai-render`)
- The WAV is rendered by FluidSynth at 44.1 kHz through `$JAMAI_SOUNDFONT`, and the MP3 by LAME
  V2. (`render/jamai-render`)
- Its last printed lines are a `duration` line, a `gain` line and each file as
  `kind<TAB>path`. The folder keeps `abc2midi.log` and `abcm2ps.log`. No file in it says which
  soundfont, which gain or which versions of the programs made the sound.
  (`render/jamai-render`)
- `jamai-publish-melody` copies the ABC, the MIDI, the MP3, the score pages and an optional
  video into the melody folder. The WAV is made in a temporary folder and is not kept.
  (`publish/jamai-publish-melody`)
- Each entry of `melodies.json` holds the slug, title, date, key, meter, tempo, duration, note,
  video, ABC source, `midi_sha256`, `gain_db` and the time of publication.
  (`publish/jamai-publish-melody`)
- The fact it appends has the id `melody:<slug>:<first 16 hex of the MIDI sha256>` and carries
  the type, the time, slug, title, the addresses of the MP3, the page and the MIDI, key, meter,
  tempo, duration and `midi_sha256`. It never carries the ABC source. A change of gain alone
  leaves the MIDI identical and is not announced. (`publish/jamai-publish-melody`)
- `jamai-say` synthesises one sentence with edge-tts into an MP3, plays it on a Chromecast
  speaker and deletes the MP3 afterwards unless `--garder` is given. It refuses to run without
  a speaker name. Its voice is an edge-tts voice name, `fr-CA-SylvieNeural` unless another is
  set. It writes no record. (`broadcast/jamai-say`)
- `jamai-suno` reads a composition folder holding `composition.json` and its ABC, and keeps for
  each generation `call.json`, `result.json` and the audio as `take-N.<ext>`, with a log of every
  exchange. (`suno/README.md`)
- `jamai-musescore --video` writes an MP4 of the score scrolling with its audio, and `--meta`
  prints the score's title, key, measures and parts as JSON. (`README.md`,
  `render/jamai-musescore`)
- The word consent appears once in the package, about pressing keys in a person's MuseScore
  window. (`musescore/VISION.md`, `git grep -ic consent`)

### What the factory reads today

- **The editing room.** The `miadi-film` plugin puts every medium of an episode into one
  Kdenlive project's bins. A video or audio file that is not a capture is listed as "Other
  media". Each clip's description starts with how it was made, then the first words said in it,
  then its address.
  (`claude/miadi-film/skills/editing-room/SKILL.md` in `jgwill/miadi-orchestration-kit`)
- **The timeline.** Its scenes pass writes a track "A2 Music (later)", left empty for the
  composer, a guide at the start of each black, and `scenes.json`, where each scene has its
  place on the timeline in seconds (`timeline_at_s`, `seconds`) and each project its
  `pause_seconds`. (`claude/miadi-film/skills/scenes-to-timeline/SKILL.md`, and `scenes.json` of
  Episode 575, miadi-chronicle://575)
- **The film's data drawing.** A ScoreCue has a `cue_id` named as in film scoring (`1M3`), the
  slug of a composition folder, and its episode. A Take is stored as MediaFiles with a role.
  A Consent is bound to a take. All of it is specified and none of it is built.
  (`rispecs/film-toolchain/` in Episode 120's vessel, miadi-chronicle://120)
- **The episodes repository.** A `.wav` is ignored by git outside a `keep/` folder. An `.mp3`, a
  `.mid`, an `.svg`, an `.abc` and a `.json` are not. (`git check-ignore -v` in the episodes
  repository, 2026-11-24)
- **The delivery event.** `miadi.composition.delivered` carries the episode, a `purpose` in the
  composer's words, optional `words`, the composition's `slug`, `title`, `label`, `composer` and
  `person`, and at most 12 files, each with its name, bytes, sha256, media type and a role among
  `readme`, `audio`, `video`, `score`, `midi`, `chords`, `image` and `other`.
  (`rispecs/events/03-platform-deliveries.spec.md` on jgwill/Miadi#1047, open)

### The one delivery so far

op-021 « Sens partagé » reached Episode 044 on 2026-11-16. Its folder
`music/op021-sens-partage-261116/` holds a score video of 58 s and a README written by the agent
who copied it. The README says the piece is in D mixolydian at 69 BPM, that it was composed from
the film's spotting notes, and that the whole composition folder stays in Jerry's workshop on
eury. That folder holds no MIDI, no audio file apart from the video, and no statement of how the
video was rendered. (`README.md` of that folder in Episode 044's vessel)

## Structural Tension

The workshop knows everything about a piece at the moment it renders it, and prints some of it
on a terminal. The edit receives a video and a paragraph. The rules below describe a piece that
arrives with what the workshop already knows, written once, in a folder the episode keeps.

## Specification

### 1. A piece

**DW1 · The files, as they are.** A piece delivered for a film is the folder `jamai-render`
writes. Each file has one reader:

| file | its reader |
|---|---|
| `NAME.wav` | the film editor, on the music track |
| `NAME.mp3` | a person listening on the episode's page |
| `NAME.mid` | the checks of 02, and the identity of the music (DW5) |
| `NAME.svg` and further pages | a person reading the score |
| `NAME.abc` | whoever the composer gives the source to. It is in the delivery only when he includes it |
| a score video, when one was made | the film editor, as picture |

- Rests on: the list of files in `render/jamai-render`. The fact of a publication never carries
  the ABC source (`publish/jamai-publish-melody`), and the delivery keeps that choice with the
  composer.
- Stands until someone says otherwise: the factory takes this folder unchanged and converts
  nothing on the way. A piece published with `jamai-publish-melody` has no WAV, so a piece meant
  for a film is rendered with `jamai-render`, which keeps it.

**DW2 · The record. Proposed.** One JSON file sits beside the files and says how they were
made. Its proposed name is `NAME.record.json`. The content matters and the field names are a
proposal.

| part of the record | holds | where it is known today |
|---|---|---|
| `piece` | slug, title, opus when there is one | the ABC `T:` header and the name derived from it (`render/jamai-render`) |
| `made_by` | the tool and its version, the command with its options, the time | `VERSION` and the command line. Kept by no file |
| `source` | sha256 of the ABC, and its key, meter and tempo headers | the ABC written beside the MIDI (`render/jamai-render`) |
| `render` | the soundfont, the gain in dB, the sample rate, the programs and their versions | `$JAMAI_SOUNDFONT`, `--gain-db` or `JAMAI_GAIN_DB`, 44100 (`render/jamai-render`). The gain is printed and not kept |
| `files` | each file with its role, bytes and sha256, and its seconds when it is audio or video | the files themselves |
| `music` | sha256 of the MIDI | the number announced as `midi_sha256` (`publish/jamai-publish-melody`) |
| `whose` | composer, person, label, and the terms (DW3) | no file of the package |
| `cue` | the episode, the cue name, the black it answers, the intended seconds (DW4) | the factory's request |
| `from` | the recordings of a person the piece was composed from, by reference, each with the consent it was offered under (DW7) | no file of the package |
| `checks` | the claims that were held and the command that held them | `ava8 verify --json` (02, U3) |

- Rests on: Jerry's acted voice engine, `emotion-render`, already writes a JSON record beside
  each clip it renders, and `jamai-suno` already keeps `call.json` and `result.json` beside each
  take (`suno/README.md`). A record beside a rendered piece follows both.
- Who writes it is not specified here. A tool of the package, a wrapper beside it, or the
  factory at reception can each write it from what is listed in the third column.
- Stands until someone says otherwise: until a tool writes the record, the factory writes it at
  reception from the files and from the lines it was given, and writes `unknown` for what they
  do not say. Today that is the soundfont, the gain and the versions of the programs.

**DW3 · Whose it is, and on what terms.** The delivery says who composed the piece, for whom,
and under which name it is published (`composer`, `person` and `label` of the delivery event). It
states in the composer's words what the film may do with the piece: use it in the cut, show it
before the film is released, publish it apart from the film.

- Rests on: the `LICENSE` file covers the software and says nothing of a piece (`LICENSE`). On
  2026-11-16 the question whether a teaser of op-021 may be public before the film was put to
  Jerry and Guillaume (Episode 044's vessel).
- Stands until someone says otherwise: with no terms stated, the episode holds the piece, the
  editor may place it in a working cut, and the production publishes nothing made with it.

**DW4 · The place in the film.** A piece composed for a film names its cue: the episode, a cue
name as in film scoring (`1M3` is reel 1, music cue 3), the black it answers by project and scene
number, and the seconds it was composed to fill.

- Rests on: the guides and `scenes.json` that the scenes pass writes, and the ScoreCue of the
  film's data drawing.
- What the composer is given first: the factory's request names the episode, the cue, the place
  and length of each black from `scenes.json`, and the purpose in the director's words. op-021
  was composed from spotting notes written on 2026-11-08.
- Stands until someone says otherwise: a piece delivered without a cue is held by the episode as
  a piece, and the editor decides where it goes.

**DW5 · One number for the same music.** The sha256 of the MIDI names the music. A melody
published on Jerry's page, the piece delivered to an episode and the file in the edit are the
same music when that number is the same. Two renders of one MIDI at different gains are the same
music with a different sound, and the record's `render` part tells them apart.

- Rests on: `jamai-publish-melody` builds the id of a fact from the first 16 hex of that sha256,
  announces a revision only when it changes, and treats a change of gain as the same music
  (`publish/jamai-publish-melody`). The delivery event declares a sha256 for every file.
- Measured on 2026-11-24: the sha256 that `miadi-platform-events deliver --print` declared for
  `first-light.mid` is the one `sha256sum` prints for the file `jamai-render` wrote.

### 2. A spoken line

**DW6 · A line is delivered with its words, its voice and its engine.** A line spoken by the
workshop for a film is a file of the piece's folder with the role `audio`. The record names the
words as written, the voice, the engine and its version, and the person whose voice it is, or
that it is nobody's.

- With `jamai-say`, the engine is edge-tts and the voice is one of its named voices, so no
  person's recorded voice is involved and the record says so. `jamai-say` was written to speak
  in a house, on a speaker. A line reaches a folder only when `--garder` kept its MP3.
  (`broadcast/jamai-say`)
- A line in a person's recorded voice comes from the acted engine,
  `Gerico1007/assembly-emotion-render` 0.1.0. It is a command any tool can call:
  `emotion-render --voice <id> --text "<script>" --out <file.wav>`, exit 0 rendered or checked,
  2 refused, 1 failed. It writes the wav and a JSON record beside it, and it refuses a voice
  whose person has not consented. Such a line is delivered with that record, unchanged, and
  `ava8 acted` holds the clip to it (02, U6).
- Measured on eury on 2026-11-24: `emotion-render --version` answers `0.1.0`, and `--check` for
  a voice nobody recorded answers `REFUSED` with exit 2.
- Whether a tool of the package calls the engine is Jerry's. The delivery is the same either
  way.
- Stands until someone says otherwise: a film's narrator lines are asked through the factory's
  own voice seam (the film door, miadisabelle/mightyeagle#36). `jamai-core` is not asked to
  speak them.

### 3. Consent where a voice is involved

**DW7 · A person's voice is named with the consent it stands on.** A voice enters this work in
three ways, and each has its own keeper.

| a voice enters as | example | what the delivery carries | who keeps the consent |
|---|---|---|---|
| a recording the piece was composed from | a sung take read by `jamai-measure.py`, `jamai-chords-audio.py` or `jamai-grille.py` (`README.md`) | a reference to the take and the consent it was offered under. Never the recording | the factory, in the consent ledger that `@miadi/ava8-atelier` reads |
| a line in a person's recorded voice | a clip rendered by `emotion-render` | the engine's record, which names the person and the consent | the engine's voice entry, read again by `ava8 acted` |
| a person on the record in the film | someone filmed, or whose own voice is heard in the cut | nothing. The release is the film's | the production, as jgwill/Miadi#962 describes |

- Rests on: Episode 256's own specification says that what a person did not offer is never
  published. `ava8 verify` ships no default register band because such a band is a measurement
  of a living person's voice (02, U3).
- Stands until someone says otherwise: a delivery names a person's recording by reference and
  never carries it. With no consent named, the factory treats the recording as not offered: the
  piece is held, and nothing that lets the recording be heard or measured is published.

### 4. The road and the place

**DW8 · The road into an episode.** Three roads exist or are built. They carry different
things.

| road | state on 2026-11-24 | carries |
|---|---|---|
| By hand into the episode's folder | used once, for op-021 | whatever the person copies |
| `miadi-platform-events deliver` to `POST /api/deliveries/compositions` | built on the open pull request jgwill/Miadi#1047. The package is not on npm, and the route answers 404 on eury | the files with their sizes and sha256, the purpose, the composer's words. The receiver keeps the files only when each matches, and never writes into an episode: placing the delivery stays a person's or a seat's act |
| A subscription to Jerry's hub | in the package (`publish/jamai-hub`). No factory subscription was found in what was read | the fact that a melody was published or revised, with its addresses. It does not say the melody is for an episode |

- Measured on 2026-11-24: `miadi-platform-events deliver --episode 256 --composition first-light
  --purpose "…" --file first-light.mp3 --file first-light.mid --file first-light.svg --file
  first-light.abc --print`, on the files `jamai-render` wrote, printed one
  `miadi.composition.delivered` event and sent nothing. It gave the MP3 the role `audio`, the
  MIDI `midi`, the SVG `image` and the ABC `score`. `--file path:role` sets a role, so the record
  travels as `--file NAME.record.json:other`.
- `deliver` reads a relative `--file` in `$MIADI_COMPOSITION_DIR/<slug>`, and `jamai-render --out
  DIR --name NAME` writes into the folder it is given (`render/jamai-render`). One folder serves
  both.
- Stands until someone says otherwise: a piece travels by hand, as op-021 did, with the record
  and the terms in its folder, until jgwill/Miadi#1047 is merged and its route is deployed.
  Then `deliver` is the road, and the hub stays what tells subscribers.

**DW9 · The place in the episode.** A delivered piece sits in the episode under
`music/<slug>-<yymmdd>/`, as op-021 sits in `music/op021-sens-partage-261116/`. The record, the
MP3, the MIDI and the score are tracked in git. The WAV is not: it is kept by custody and
proven by the sha256 in the record.

- The editing room lists the piece under "Other media". **Proposed**, in Episode 120's
  specifications and not here: the room reads the record for the clip's description, so the
  editor sees "rendered by jamai-render 0.4.4, FluidR3, 0 dB, cue 1M3" in place of a file name.
- **Proposed**, in the same place: a ScoreCue names the piece by its slug and the sha256 of its
  MIDI.
- Not built on either side: a holding that shows a piece on the episode's page, as a
  specification or a review is shown. Episode 256's own specification asks for it.

## Creative Advancement Scenarios

**Creative Advancement Scenario**: A piece arrives with its record
**User Intent**: Jerry wants the cue he composed for a film to be in the episode as he made it.
**Current Reality**: The cue is rendered in his workshop. The episode has a `music/` folder
holding one earlier piece and a README.
**Natural Progression Steps**:
  1. `jamai-render --out <folder> --name <slug>` writes the files.
  2. The record is written beside them: the render, the sha256 of each file, the cue, the terms
     in Jerry's words.
  3. The folder reaches the episode by the road of the day (DW8).
  4. The episode keeps the folder under `music/`, and the WAV is proven by its sha256.
**Achieved Outcome**: The episode holds the piece with how it was made and what the film may do
with it, in Jerry's words and the workshop's numbers.
**Supporting Features**: DW1, DW2, DW3, DW8, DW9.

**Creative Advancement Scenario**: The editor places the cue at its black
**User Intent**: The person editing wants the music where the director left room for it.
**Current Reality**: The timeline has an empty "Music (later)" track and a guide at each black.
The piece is in the episode with a cue name and a length.
**Natural Progression Steps**:
  1. The editing room shows the piece with its description from the record.
  2. The cue names the project and the scene whose black it answers.
  3. The editor places the WAV on the music track at that guide, and trims or moves it.
**Achieved Outcome**: The cue sits in the cut at the place it was composed for, and the cut can
be followed back to the render that made the sound.
**Supporting Features**: DW4, DW9, the scenes pass of `miadi-film`.

**Creative Advancement Scenario**: The same music, heard in two places
**User Intent**: Guillaume wants to know that the melody on Jerry's page is the cue in his film.
**Current Reality**: The page shows a melody with a fact id. The episode holds a record.
**Natural Progression Steps**:
  1. The fact's id ends with the first 16 hex of the MIDI's sha256.
  2. The record's `music` part holds the whole sha256.
  3. The two agree, or they differ and the record's `render` part says what changed.
**Achieved Outcome**: One number answers whether two files are the same music.
**Supporting Features**: DW5.

## Data

Reads the files of a render, the fact ledger's fields and the delivery event. Proposes one
record file per piece. Proposes, in Episode 120, that a ScoreCue and the editing room read it.

## Boundaries

- No tool of `jamai-core` is changed or specified. The record can be written outside every
  tool.
- The delivery event and its route belong to jgwill/Miadi#1047. Nothing here changes them.
- Whose recorded voice a line is spoken in, and what a consent means for the film, are decided
  by the people concerned, not by a specification.
