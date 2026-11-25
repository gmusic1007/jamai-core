# 03 · Who does what: the composer's part and the production part

## Status: 📋 A READING, stated to be corrected · Issue: miadisabelle/mightyeagle#35 (Phase 5)

Part of `rispecs/factory-film-production/`. Read `SPEC.md` first. A sentence about `jamai-core`
ends with the file it was read from at `4826b74`.

W stands for a reading of who does what. Every W below is our reading of files, not a decision
taken for anyone. It stands until someone in the talking circle says otherwise.

## Intent

Two platforms work on one film. Each knows which part of the work it answers for, which part the
other answers for, and where the two meet. Nothing is built twice because nobody had said whose
it was.

## Desired Outcome

- A person or an agent on either side reads one page and knows where a piece of work belongs.
- Where both sides have a tool for the same concern, the page says what each one is for.
- The reading is discussed in the talking circle of Episode 256 (miadi-chronicle://256) and
  changed there. The file is changed after the circle, not before.

## Current Reality

- `jamai-core` describes itself as JamAI's composition workshop: tools that listen to what was
  played, render it, publish it on a page of the person's own, and tell the people who
  subscribed. It packages only what runs. (`README.md`)
- The factory describes its film work in Episode 120 (miadi-chronicle://120): an editor and a
  director make every choice, and an assistant editor prepares the room.
  (`claude/miadi-film/README.md` in `jgwill/miadi-orchestration-kit`)
- miadisabelle/mightyeagle#35 lists four concerns that have more than one implementation:
  measuring a rendered piece, consent on a recorded voice, speech, and score to sound.
- gmusic1007/jamai-core#5 asks which of `jamai-core` and `miadi-music` renders ABC, and names
  Jerry and William as the ones who decide.
- Neither side has written which part is whose.

## Structural Tension

Both platforms grew from the same collaboration and each built what it needed when it needed
it. Four concerns now exist on both sides. The reading below names, for each, what the
composer's tool is for and what the production's tool is for, so that the next piece of work
has a place before it is started.

## Specification

### 1. The two parts

**W1 · `jamai-core` is the composer's part.**

| it | with | read from |
|---|---|---|
| listens to what was played | `jamai-midi.py`, `jamai-chords.py`, `jamai-chords-audio.py`, `jamai-measure.py`, `jamai-grille.py` | `README.md`, `listen/` |
| writes and renders a score | `jamai-render`, `jamai-musescore`, `jamai-tab.py`, `jamai-score-video.py`, `jamai-scroll.py` | `render/` |
| speaks a line | `jamai-say`, on a speaker, in an edge-tts voice | `broadcast/jamai-say` |
| publishes a melody and tells subscribers | `jamai-publish-melody`, `jamai-hub` | `publish/` |
| sends a composition to Suno | `jamai-suno`, with the person's own account | `suno/README.md` |
| offers all of it to an agent | `jamai-mcp`, sixteen tools, and the `jamai` skill | `README.md`, `mcp/jamai-mcp`, `claude/jamai/` |

It answers for the ABC source, the render, the melody page, the subscribers and their secrets,
and the settings of the house it runs in. No address of a house is in the packaged code, and
its self-test fails if one appears. (`README.md`)

**W2 · The factory is the production part.**

| it | with | read from |
|---|---|---|
| holds the episode | the Chronicle: an episode's folder, its `episode.yaml` and the doors that hold records on it | the `chronicle-episode` skill in `jgwill/miadi-orchestration-kit` |
| cuts the picture | the `miadi-film` package (Kdenlive, Ardour, ffmpeg) and the `miadi-film` plugin. The editor makes the cuts | `claude/miadi-film/README.md` in the same repository |
| checks what was rendered | `ava8 measure`, `ava8 verify`, `ava8 acted` | `packages/ava8/README.md` on jgwill/Miadi#1094 |
| keeps the consent | the consent ledger read by `@miadi/ava8-atelier`, and consent per take in the film's specifications | `packages/ava8-atelier/README.md` on jgwill/Miadi#1094, `rispecs/film-toolchain/consent-per-take.spec.md` in Episode 120's vessel |
| receives a delivery | `POST /api/deliveries/compositions` | jgwill/Miadi#1047, open. The route answers 404 on eury |

It answers for the episode, the cut, the checks at reception, the consent of every person on
the record, and the publication of the film.

**W3 · They meet in three places.** The folder a piece is delivered in (01). The commands that
read a rendered file back (02). The cue: the black on the timeline that a piece was composed to
fill (01, DW4). Outside those three, neither side needs to know how the other works.

### 2. The four concerns that exist on both sides

**W4 · Score to sound.** The piece that is delivered is the one `jamai-core` rendered, with the
soundfont and the gain the composer chose (`render/jamai-render`). The factory does not render
it again. `miadi-music-render` brings programs to a host and renders nothing by itself.
`ava8 midi` writes a second MIDI from the same ABC only as a witness for `ava8 verify --source`
(02, U4).

- Rests on: a change of gain is the composer's choice, recorded in his manifest and not
  announced as a revision (`publish/jamai-publish-melody`). A second render on the factory's
  side would be a different sound under the same name.
- Stands until someone says otherwise: the factory never replaces a delivered file with its own
  render. The decision between the two packages is in gmusic1007/jamai-core#5.

**W5 · Measuring.** The composer measures to compose: what was played, which chords, which key,
where the bars are. His tools print for a reader, in his language. (`listen/`) The production
measures to hold a delivered file to what was claimed about it, with an exit code (02, U1 to
U3). Both stay.

- Three measuring implementations exist on the factory's side (02, last table). Naming one of
  them canonical is another step of miadisabelle/mightyeagle#35 and is not done here.

**W6 · Speech.** `jamai-say` speaks in a house, on a speaker, for the person who is there
(`broadcast/jamai-say`). A film's lines are asked through the factory's voice seam, which is
specified in miadisabelle/mightyeagle#36. A line in a person's recorded voice is rendered by the
acted engine, which is Jerry's, under its two rules.

- Stands until someone says otherwise: `jamai-core` is not asked to speak a film's lines, and
  the factory does not ask `jamai-say` to become a film tool.

**W7 · Consent.** The factory keeps it. The package holds no consent record (the word appears
once, in `musescore/VISION.md`, about pressing keys in a person's window). A recording of a
person is read by the package's listen tools on the composer's machine. What that person
offered, and for what, is recorded on the factory's side and named in the delivery by reference
(01, DW7).

- Rests on: the film's release (jgwill/Miadi#962) and the consent ledger are the production's.
  The rule that no voice is cloned without its person's consent is the engine's own.
- Stands until someone says otherwise: `jamai-core` is delivered a yes or a no it can read. It
  is not asked to keep a ledger.

### 3. Publishing, and the agents

**W8 · Each publishes its own.** The composer publishes a melody on his page, and his hub tells
his subscribers (`publish/jamai-publish-melody`, `publish/jamai-hub`). The production publishes
the film. Whether a piece made for a film is public on the composer's page before the film is
released is said in the terms of the delivery (01, DW3).

- Stands until someone says otherwise: the factory writes nothing into the composer's melody
  folder, ledger or hub. It subscribes to the hub the way anyone does, with an invite code from
  the composer (`README.md`). The production publishes nothing made with a piece whose terms are
  not stated.

**W9 · An agent proposes and a person keeps.** JamAI composes through `jamai-mcp`, where only
`jamai_publish_melody` changes a published page and it is called when the person asked
(`mcp/jamai-mcp`). The factory's assistant editor prepares a room and a timeline and marks them
as a proposal until a person keeps it (`claude/miadi-film/skills/scenes-to-timeline/SKILL.md`).
On both sides the agent does the preparing and the person makes the choice: the composer for
the music, the editor and the director for the cut.

### 4. What neither side is asked to do

| `jamai-core` is not asked to | the factory does not |
|---|---|
| hold an episode or know more of the Chronicle than an episode number in a delivery | render, engrave or re-encode a delivered piece |
| keep a consent ledger | publish a piece, or write into the melody page or the hub |
| cut picture or place a cue | change a tool of the package |
| depend on a `@miadi/*` package | decide whose recorded voice speaks, or what a piece's terms are |

## For the talking circle

These are the statements the circle receives. None is a question. Each stands until someone
there says otherwise, and the file changes after the circle has spoken.

1. **W1, W2** `jamai-core` is the composer's part and the factory is the production part.
2. **W3** They meet in the delivery folder, in the checks and at the cue.
3. **W4** The factory never renders a delivered piece again.
4. **W5** Both sides keep their measuring tools, for two different uses.
5. **W6** `jamai-core` is not asked to speak a film's lines.
6. **W7** The factory keeps the consent, and `jamai-core` is delivered a yes or a no.
7. **W8** Each publishes its own, and a piece without terms is not published by the
   production.
8. **W9** An agent proposes and a person keeps.

## Creative Advancement Scenarios

**Creative Advancement Scenario**: A new piece of work finds its side
**User Intent**: An agent on either platform wants to know where a tool it is about to write
belongs.
**Current Reality**: The tool would place a cue on a film's timeline from a delivered piece.
**Natural Progression Steps**:
  1. It reads W1 and W2: placing a cue is cutting the picture, which is the production's.
  2. It reads W3: the cue is one of the three meeting places, described in 01.
  3. It writes the tool on the factory's side, reading the record the piece arrived with.
**Achieved Outcome**: The tool is written once, on the side that answers for it.
**Supporting Features**: W1, W2, W3.

**Creative Advancement Scenario**: The reading is corrected in the circle
**User Intent**: The composer wants `jamai-core` to speak a film's lines after all, in a
voice that was recorded for it.
**Current Reality**: W6 says it is not asked to.
**Natural Progression Steps**:
  1. It is said in the talking circle of Episode 256.
  2. W6 is rewritten from those words, and 01's DW6 already says what such a line is delivered
     with.
  3. The specifications are held again by the episode at their new commit.
**Achieved Outcome**: The page says what the people it describes agreed to.
**Supporting Features**: every W, and the circle.

## Boundaries

- This file decides nothing in gmusic1007/jamai-core#5, names no canonical measuring
  implementation, and chooses nobody's voice.
- It describes two parts. It does not rank them.
