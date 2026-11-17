# jamai-core 🎸

JamAI's composition workshop: tools that **listen** to what was played, **render** it so it can
be heard and read, **publish** it on a page of your own, and **tell the people who subscribed**.

Everything here was written during real composition sessions, each tool at the moment something
was missing. Version 0.2.0 makes the set installable by someone who is not in the house where it
was born: one command, and it asks for every setting it needs.

## Install

```bash
git clone https://github.com/gmusic1007/jamai-core.git
./jamai-core/install.sh
```

The installer does four things, in this order:

1. **Asks the settings** declared in [`settings`](settings): where the commands go, which
   soundfont, where older ABC sessions live, where melodies are published and under which
   public address, the hub's port, the screen and speaker names. Enter keeps the value shown in brackets.
2. **Writes them** to `~/.config/jamai/jamai.env` (plain `KEY=VALUE`). The one secret, the hub's
   admin token, is generated and kept apart in `secrets.env`, mode 600.
3. **Links the 21 commands** into the folder you chose (default `~/.local/bin`). A file already
   there is renamed `name.bak-<stamp>`, never deleted.
4. **Runs `jamai doctor`**, which names each missing program, the package that brings it, and
   what stops working without it.

| | |
|---|---|
| `./install.sh --yes` | no questions: defaults, or values already in the environment |
| `./install.sh --check` | changes nothing, exits 1 if a command is not linked to this checkout |
| `./install.sh --dry-run` | says what an install would do |
| `./install.sh --uninstall` | removes the links, keeps your config |

Piped (`curl -fsSL …/install.sh | bash`), the same script clones the repository into
`~/.local/share/jamai-core` first and asks its questions on your terminal. That form needs the
repository to be readable without signing in, which is not the case today.

**System programs** (Debian and Ubuntu names): `abcmidi abcm2ps fluidsynth fluid-soundfont-gm
lame ffmpeg jq librsvg2-bin imagemagick python3-numpy python3-scipy python3-pil`. Optional, for
a screen and a speaker: `pipx install catt edge-tts`. Tested on Ubuntu. Other systems are untested.

## A first melody

```bash
jamai-render examples/first-light.abc            # hear it and read it; nothing is published
jamai-publish-melody examples/first-light.abc    # add it to your melody page
```

`jamai-publish-melody` renders ABC to MIDI, WAV and MP3, engraves the score, updates
`melodies.json` and the index page in `JAMAI_MELODY_DIR`, and prints the listen address. With
`JAMAI_PUBLIC_BASE` empty, that address is a file on your machine: no web host is needed to start.

A soft arrangement renders quiet. `--gain-db 10` (or `JAMAI_GAIN_DB`) lifts both the WAV and the MP3.
The gain is linear with no limiter, so measure the peak before going far: a loud piece can clip.

## Settings

Three sources, first match wins: the environment, then `~/.config/jamai/jamai.env`, then the
default in `settings`.

```bash
jamai config show                 # every setting, its value, and where the value comes from
jamai config set JAMAI_PUBLIC_BASE https://example.org/melody
jamai setup                       # ask them all again
```

Nothing about where you publish is built into a tool. The self-test fails if a house address
appears in the packaged code.

## Older sessions, and MuseScore

```bash
jamai-legacy list ~/old-sessions            # every ABC session under a folder: date, key, meter, tempo, title
jamai-musescore ~/old-sessions/theme.abc    # open one in MuseScore as a score you can edit
jamai-publish-melody ~/old-sessions/theme.abc
```

A legacy session is plain ABC, so every command takes it as it is. `jamai-musescore` goes through
MIDI: `abc2midi` writes the MIDI file and MuseScore's own converter turns it into MusicXML. Notes,
rhythm, tempo, key and instruments come through. Chord symbols, lyrics and voice names do not.
`--no-open` converts without opening a window. Set `JAMAI_LEGACY_DIRS` to list without naming a
folder each time.

## People who want your music: the hub

After each publication, `jamai-publish-melody` appends one fact to a ledger and delivers nothing
itself:

| fact | when |
|---|---|
| `melody.published` | the slug is new |
| `melody.revised` | the slug existed and the music changed (the MIDI differs) |
| none | the MIDI is byte-identical, so an engraving fix notifies nobody twice |

A fact carries the title, the links to the MP3, MIDI and score, key, meter, tempo, duration and
a digest of the MIDI. It never carries the ABC source. The session note stays on the page unless
you set `JAMAI_PUBLISH_NOTE_PUBLIC=1`.

`jamai-hub serve` runs the service: your melody page, a subscribe page, and a worker that POSTs
each fact once to every subscriber.

```bash
jamai-hub serve                           # http://127.0.0.1:8642/
jamai-hub invite "a friend's studio"      # a one-use code to hand to that person
jamai-hub subscriptions                   # who is subscribed (never the secrets)
jamai-hub unit > ~/.config/systemd/user/jamai-hub.service   # keep it running
```

A subscriber gives a webhook address and receives an id and a secret, shown once. Every delivery
is signed with that secret. On the receiving side:

```python
import hashlib, hmac
expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
trusted = hmac.compare_digest(expected, request.headers["X-JamAI-Signature"])
```

What the hub refuses by default: a subscription without an invite code, a webhook that is not
https, a webhook that resolves to a private or local address (checked again at each delivery),
and redirects. A subscription receives what is announced after it, counted by position in the
ledger. A failed delivery is tried again five times over about nine hours.

The hub has no accounts and no sign-in. A person manages a subscription with its id and secret.

## For an agent: MCP server and Claude plugin

```bash
claude mcp add jamai -- jamai-mcp                         # the tools, in Claude Code
claude plugin marketplace add gmusic1007/jamai-core       # or the plugin: tools plus a skill
claude plugin install jamai@jamai-core
```

`jamai-mcp` offers eleven tools over stdio: `jamai_doctor`, `jamai_config`, `jamai_render`,
`jamai_midi_notes`, `jamai_chords`, `jamai_tab`, `jamai_legacy_list`, `jamai_musescore`,
`jamai_publish_melody`, `jamai_list_melodies`, `jamai_events`. Only `jamai_publish_melody`
changes a published page, and only `jamai_musescore` with `open: true` opens a window. The plugin adds the
[`jamai` skill](claude/jamai/skills/jamai/SKILL.md): the order of work, and the traps that each
cost a session to find. The plugin needs jamai-core installed first, since it calls `jamai-mcp`
by name.

## The commands

`jamai tools` prints this list.

| folder | command | what it does |
|---|---|---|
| `listen/` | `jamai-midi.py` | MIDI to a note-by-note listing and ABC |
| | `jamai-chords.py` | the chord sounding on each beat of a MIDI file |
| | `jamai-chords-audio.py` | chords and key from a recording |
| | `jamai-measure.py` | tempo, structure, pitch and timbre of a recording |
| | `jamai-grille.py` | measure the bar grid before writing the score |
| `render/` | `jamai-render` | ABC to MIDI, WAV, MP3 and an engraved score |
| | `jamai-musescore` | open a melody in MuseScore as an editable score |
| | `jamai-tab.py` | six-line guitar tablature from ABC |
| | `jamai-score-video.py` | score video, one system at a time |
| | `jamai-scroll.py` | score video scrolling left to right under a red playhead |
| `publish/` | `jamai-publish-melody` | render a melody and add it to the melody page |
| | `jamai-hub` | the melody page, subscriptions and webhook delivery |
| `workshop/` | `jamai-unread.py` | recorder drops nobody has worked on yet |
| | `jamai-related.py` | units that already speak of the same thing |
| | `jamai-follow-fork` | follow a Claude session read-only |
| | `jamai-legacy` | ABC sessions written before the package, ready to open or publish |
| `broadcast/` | `jamai-cast` | an HTML page on a Chromecast screen |
| | `jamai-say` | a spoken sentence on a Chromecast speaker |
| `moments/` | `routine` | a named moment of a house: its screen, speaker and posture |
| `mcp/` | `jamai-mcp` | the tools as an MCP server |
| `bin/` | `jamai` | setup, config, doctor |

## Proof

```bash
tests/selftest.sh
```

It installs into a throwaway folder and checks 94 things: the settings and the links, a render,
the three publication cases, the hub's invite, signature, single delivery and refusals, byte
ranges, a legacy session listed, converted for MuseScore and published, the defects fixed under
gmusic1007/jamai-core#4, the MCP server, and that no house address is in the packaged code. Where MuseScore is absent, its three checks are
skipped and one other check confirms the command says so. It touches none of
your files and reaches no outside address.

## Where this comes from

The first nine tools were written between 3 and 14 August 2026, during composition sessions with
Jerry ⚡ of the G.Music Assembly, and gathered here from the places they had grown. An earlier
`Gerico1007/Jamai-core` (May 2025) held nine empty module folders: an architecture drawn before a
note was played. This repository took the name and left the plan. It packages only what runs.

Not in the package yet: the drop watcher and transcription (`jamai-on-drop`, `jamai-watch`), the
footage clip tools and the speaker bridge.

*♠️🌿🎸🧵 G.Music Assembly*
