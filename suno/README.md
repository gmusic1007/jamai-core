# jamai-suno

Turns a JamAI composition (a `<slug>/` folder holding `composition.json` and its ABC) into a Suno
generation through Suno's MCP server, `https://api.suno.com/mcp`, with the person's own Suno account.
Python 3 standard library only. The seed render uses this package's own `render/jamai-musescore`.

The authorization stays on the person's machine, in `~/.config/jamai-suno/` (mode 600). No token
or credential belongs in this repository.

```
jamai-suno prepare  <composition-folder> [--abc FILE] [--key "E Phrygian"] [--seed melody|full|none]
jamai-suno generate <composition-folder> [--variant instrumental|lyrics] [--tool NAME] [--plan]
jamai-suno tools [--json]
jamai-suno login [--port 41799] [--no-browser] [--redirect-uri URL]
jamai-suno status
```

## prepare

Reads `composition.json` and one ABC file. Writes into `<composition>/suno/`:

- `request.json`: title, style prompt, instrumental flag, a `lyrics` variant when the melody voice
  has `w:` lines, the musical facts each choice came from, and warnings.
- `BRIEF.md`: the same, for a person, with `texts[]` shown as context.
- `seed/<abc-name>-melody.mp3`: the melody voice alone, rendered by `jamai-musescore --export mp3`.
  Under `xvfb-run` when there is no display (MuseScore 4.7's converter needs an X connection).

Rules:

- **D1 (which ABC):** `--abc`, else `<folder>/<slug>.abc`, else `<root>/<slug>.abc`. If none of
  these exists, it stops and lists the candidates. It never chooses between versions.
- **D2 (lyrics):** lyrics come only from the ABC `w:` lines of the melody voice. `texts[]` never
  goes to Suno.
- **Melody voice:** the voice with `w:` lines, else a voice named Mélodie, Voix, lead or chant,
  else the first pitched voice.
- **Key:** `--key`, else the ABC `K:`, else `composition.json` `key`. The notes are always read with
  the written `K:` signature. It warns when `K:` disagrees with the first and last chord, or with
  `composition.json`.
- **Style prompt:** the instruments (from `%%MIDI program`), the tempo, the meter, the key, and the
  melody's shape, range and motion. A house clause follows them (see `HOUSE_STYLE` in `jamai_suno.py`).

## generate

1. Token: `SUNO_MCP_TOKEN`, else `~/.config/jamai-suno/oauth.json`, refreshed when it expires.
2. `initialize`. On 401 or 403 it stops with **authorization required** (exit 3).
3. `tools/list`, saved to `suno/tools.json`.
4. The tool is `--tool`, else `"generate"` in `~/.config/jamai-suno/suno-tools.map.json`. With neither, it stops (exit 4)
   and lists the live tools.
5. The arguments are matched to the tool's schema by name. Every required parameter must be
   filled. A public/private parameter is set to private.
6. `--plan` prints the call and stops there. Without it the tool is called. The output goes to
   `suno/<UTC>-<variant>/`: `call.json`, `result.json`, and the audio it can find, as
   `take-N.<ext>`.

Every exchange is logged in `suno/log/<UTC>-generate.jsonl`, with the token redacted.

Exit codes: 0 ok, 1 the tool reported an error, 2 bad input, 3 authorization required, 4 tool
choice or arguments, 5 server or render failure.

## login

OAuth 2.1 with PKCE, from the server's protected-resource and authorization-server metadata. It
registers a public client through dynamic registration, prints the approval URL, and waits on
`127.0.0.1:<port>`. The browser has to run on this machine, or reach the port through
`ssh -L <port>:127.0.0.1:<port> <this machine>`. With `--redirect-uri`, a public address that a
reverse proxy forwards to `127.0.0.1:<port>/callback` is registered instead, for a browser on
another device; a request whose `state` does not match is refused and the wait goes on. The token
is saved in `~/.config/jamai-suno/oauth.json`, mode 600.

## Tests

`python3 tests/test_suno.py` runs against a local mock of an OAuth-protected MCP server: the 401
gate, the tool list, `--plan`, a call answered by SSE with an audio download, login and refresh.
The mock's tool names are invented.
