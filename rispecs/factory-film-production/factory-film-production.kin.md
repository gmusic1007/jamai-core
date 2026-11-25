# Factory film production: relational context

Who and what these specifications stand in relation with, and what each relation asks of them.

## People

- **Jerry** (GitHub `Gerico1007`, and `gmusic1007` for this repository) is the musician and the
  author of `jamai-core`. Its first tools were written during composition sessions with him
  (`README.md`). Everything here about his package is a reading he can correct. No step waits
  for him, and a word from him changes any of it.
- **Guillaume** (William, GitHub `jgwill`) makes the films and the episodes. On 2026-11-24 he
  asked for these specifications: what would let the package be used inside the factory when a
  film is made, what the factory already made that the package can use and contribute to, and a
  clearer statement of what the package answers for, so that a talking circle has something to
  speak about.
- **JamAI** is the composing agent of the G.Music Assembly. It uses these tools and composed
  op-021 for the film of Episode 044.
- **Mia** is an agent seat of the Miadi Factory. She wrote these files on 2026-11-24 with nobody
  steering, from the package at `4826b74` and from the factory's tools run on its files.

## The circle

A talking circle was opened on 2026-11-24 in the Root Circle of Episode 256. It receives these
specifications. It does not gate them. What is said there is read on its own page by the people
the circle admits and is not copied into this repository. `03-who-does-what.spec.md` lists the
statements the circle receives.

## Episodes

| episode | relation |
|---|---|
| miadi-chronicle://256 | Holds these specifications. It is the episode of Jerry's relation with JamAI. Its own specification, `rispecs/musical-composition-experience`, says a piece belongs to an episode with its provenance. 01 describes what that provenance arrives as |
| miadi-chronicle://581 | The episode of Guillaume's relation with JamAI. It holds the voice specifications of miadisabelle/mightyeagle#36 and the three `@miadi/ava8*` packages of 02 |
| miadi-chronicle://044 | The first film to ask the workshop for its music. op-021 sits in its `music/` folder |
| miadi-chronicle://120 | The film toolchain: the film log, take ingest, score cues, consent per take. What 01 proposes for the editing room and for a ScoreCue is proposed there |
| miadi-chronicle://575 | The first timeline with an empty music track and a guide at each black |
| miadi-chronicle://548 | The event spine the delivery event belongs to |

## Repositories and threads

| thread | relation |
|---|---|
| gmusic1007/jamai-core#4 | Every tool the composition loop runs is in the package. It names the tools that set a score over footage as still outside the package. Placing music on picture is the production's part in 03, and these specifications ask nothing of that issue |
| gmusic1007/jamai-core#5 | The community can install the package "and it agrees with miadi-music". Its open step is which of the two renders ABC. 02's U4 and U5 are measurements for it. The decision stays with Jerry and William, there |
| gmusic1007/jamai-core#6 | Jerry's own melodies are published and announced through the package. 03's W8 keeps publication and the hub with the composer. A factory subscription to the hub is named in 01 and not asked for |
| gmusic1007/jamai-core#3 | Sign-in, and a visibility per melody. When it is built, a melody's visibility is one place the terms of a piece (01, DW3) could be read. Not specified here |
| miadisabelle/mightyeagle#35 | The issue these specifications are Phase 5 of |
| miadisabelle/mightyeagle#36 | The voice specifications. Its film door, `rispecs/voice-emotion-render/04-film-door.spec.md`, names `jamai-core` as a pointer. This folder is what that pointer leads to |
| jgwill/Miadi#1094 | `@miadi/ava8` 0.5.0, `@miadi/ava8-measure` 0.2.0 and `@miadi/ava8-atelier` 0.2.0, open as a pull request and public on npm |
| jgwill/Miadi#1047 | A composition delivered to an episode: `@miadi/platform-events` and its receiving route. Open. It names `melody.published` as a fact of the same family, not built |
| jgwill/Miadi#962 | The release a person on the record agrees to at the start of a production |
| jgwill/miadi-orchestration-kit#44 | The atelier-jerry plugin, Jerry's, where the measured register, the consent guard, the verification of the rendered file and the provenance block were first proven |
| jgwill/miadi-orchestration-kit#73, jgwill/miadi-orchestration-kit#130, jgwill/miadi-orchestration-kit#153 | The `miadi-music` packages, the `miadi-film` package and the `miadi-film` plugin |
| `Gerico1007/assembly-emotion-render` | Jerry's acted voice engine. Its record beside each clip is the precedent for the record of 01 |

One difference from the film door, stated so that neither file is read against the other: the
film door says Phase 5 proposes that `jamai-say` reach the acted engine. These specifications do
not specify a change inside `jamai-say`. They say the engine is a command the package can call,
and what a line is delivered with whichever tool spoke it (01, DW6).

## Jerry's documentation

The documentation of 0.4.4 was verified against `4826b74` on 2026-11-24 by Jerry's own
documentation pipeline. These specifications add one folder and change no documentation. Where
they state a limit of a tool (`jamai-measure.py` and a stereo WAV, in 02), it is one that
reference already lists. It was read here from copies of what the pipeline wrote that day. The
published site was not opened.

## What this context asks of the specifications

- They are statements with what each rests on, never a list of questions for Jerry.
- Every proposal stays outside his tools: what an output is delivered with, and what a tool can
  call.
- Where the two platforms have a tool for the same concern, the specifications bring a
  measurement and leave the decision with the people named for it.
- What a person did not offer is never published. Consent is named and kept, not inferred.
- They stay provisional until the people they describe have read them. The circle is where that
  happens.

## Not specified here, and where it belongs

| what | where |
|---|---|
| One measuring implementation named canonical | Phase 5 of miadisabelle/mightyeagle#35 |
| `melody.published` as a platform event | jgwill/Miadi#1047, under "Next" |
| The music composition companion plugin | Phase 4 of miadisabelle/mightyeagle#35, in `jgwill/miadi-orchestration-kit` |
| A pull request to `gmusic1007/jamai-core` with this folder | Opened by the factory's coordinating session, after it has read these files |
| A holding that shows a piece on an episode's page | Episode 256's own specification, not built |
