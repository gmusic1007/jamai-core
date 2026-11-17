#!/usr/bin/env bash
# selftest.sh — prove an install end to end, in a throwaway folder. It touches nothing of yours:
# no real config, no real melody page, no real ~/.local/bin, and it never leaves this machine.
#
#   tests/selftest.sh            run everything
#   tests/selftest.sh --keep     keep the throwaway folder afterwards and print where it is
#
# What it proves: the installer links every command and writes the settings; a melody renders
# and publishes with no house address in the result; the right fact is announced (published,
# unchanged, revised); the hub accepts a subscription by invite only, delivers one signed
# POST per fact, refuses private targets, serves the page and byte ranges; a legacy ABC
# session is listed, converted for MuseScore and published; the live-control plugin is installed and a
# stand-in MuseScore receives commands; the MCP server lists and runs its tools.
set -uo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
T="$(mktemp -d "${TMPDIR:-/tmp}/jamai-selftest.XXXXXX")"
PIDS=()
cleanup() {
  for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done
  if [ "$KEEP" -eq 1 ]; then echo "kept: $T"; else rm -rf "$T"; fi
}
trap cleanup EXIT

# Nothing of the caller's settings may leak into the test.
for v in $(env | sed -n 's/^\(JAMAI_[A-Z0-9_]*\|GMUSIC_[A-Z0-9_]*\)=.*/\1/p'); do unset "$v"; done
export JAMAI_CONFIG_DIR="$T/config"
export JAMAI_MUSESCORE_PLUGINS_DIR="$T/msplugins"
export JAMAI_MUSESCORE_LIVE_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
export JAMAI_BIN="$T/bin"
export PATH="$T/bin:$PATH"

pass=0; fail=0
ok()   { pass=$((pass + 1)); printf 'ok    %s\n' "$1"; }
bad()  { fail=$((fail + 1)); printf 'FAIL  %s\n' "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; }
skipped=0
skip() { skipped=$((skipped + 1)); printf 'skip  %s\n' "$1"; }
check(){ local what="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$what"; else bad "$what" "command: $*"; fi; }
free_port() { python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'; }
wait_for() { local i; for i in $(seq 1 "${2:-50}"); do eval "$1" >/dev/null 2>&1 && return 0; sleep 0.2; done; return 1; }

echo "── install"
JAMAI_STATE_DIR="$T/state" JAMAI_MELODY_DIR="$T/site/melody" JAMAI_PUBLIC_BASE="https://music.example.org/melody" \
JAMAI_SITE_TITLE="Selftest Atelier" JAMAI_SITE_BYLINE="A test person" JAMAI_HUB_PUBLIC_URL="https://music.example.org/hub" \
  "$ROOT/install.sh" --yes > "$T/install.log" 2>&1
check "installer exits 0" test "$?" -eq 0
n_tools="$(sed -n '/^TOOLS=(/,/)$/p' "$ROOT/install.sh" | grep -o -E '[a-z]+/[A-Za-z0-9._-]+' | wc -l)"
check "every command is linked ($n_tools)" test "$(find "$T/bin" -maxdepth 1 -type l | wc -l)" -eq "$n_tools"
check "install.sh --check finds no drift" "$ROOT/install.sh" --check
check "jamai.env holds the melody folder" grep -q "^JAMAI_MELODY_DIR=$T/site/melody$" "$T/config/jamai.env"
check "jamai.env holds this checkout" grep -q "^JAMAI_CORE_ROOT=$ROOT$" "$T/config/jamai.env"
check "an admin token was generated" grep -q '^JAMAI_HUB_ADMIN_TOKEN=.\{20,\}' "$T/config/secrets.env"
check "secrets.env is mode 600" test "$(stat -c %a "$T/config/secrets.env")" = 600
check "the token is not in jamai.env" bash -c "! grep -q TOKEN '$T/config/jamai.env'"
# From here on the settings come from the files, as they would for a person.
jamai config set JAMAI_STATE_DIR "$T/state" >/dev/null
check "config get reads the file" test "$(jamai config get JAMAI_PUBLIC_BASE)" = "https://music.example.org/melody"
check "config show hides the secret" bash -c "jamai config show | grep JAMAI_HUB_ADMIN_TOKEN | grep -q hidden"
check "the environment wins over the file" test "$(JAMAI_HUB_PORT=1234 jamai config get JAMAI_HUB_PORT)" = 1234
check "an undeclared name is refused" bash -c "! jamai config set NOT_DECLARED x"
jamai doctor > "$T/doctor.log" 2>&1; doctor_rc=$?
check "doctor reports the render chain" grep -q '^Render chain:' "$T/doctor.log"
if [ "$doctor_rc" -ne 0 ]; then
  echo; cat "$T/doctor.log"; echo
  echo "The render chain is incomplete on this machine, so the rest cannot run. $pass passed, $fail failed so far."
  exit 1
fi

echo "── render"
jamai-render "$ROOT/examples/first-light.abc" > "$T/render.log" 2>&1
check "jamai-render exits 0" test "$?" -eq 0
check "it wrote an MP3" test -s "$T/state/renders/first-light/first-light.mp3"
check "it wrote a MIDI file" test -s "$T/state/renders/first-light/first-light.mid"
check "it published nothing" test ! -e "$T/site/melody/melodies.json"

echo "── publish"
jamai-publish-melody --note "a private session note" "$ROOT/examples/first-light.abc" > "$T/publish1.log" 2>&1
check "first publication exits 0" test "$?" -eq 0
check "it prints the public address" grep -q 'https://music.example.org/melody/first-light.mp3' "$T/publish1.log"
check "the manifest has one melody" test "$(jq length "$T/site/melody/melodies.json")" -eq 1
check "the page carries the title" grep -q 'Selftest Atelier' "$T/site/melody/index.html"
check "the page links to the hub" grep -q 'https://music.example.org/hub/' "$T/site/melody/index.html"
check "one fact: melody.published" test "$(jq -r .type "$T/state/events/ledger.jsonl")" = melody.published
check "the fact leaves the note out" bash -c "! grep -q 'private session note' '$T/state/events/ledger.jsonl'"
check "the fact leaves the ABC out" bash -c "! grep -q 'K:D' '$T/state/events/ledger.jsonl'"
jamai-publish-melody "$ROOT/examples/first-light.abc" > "$T/publish2.log" 2>&1
check "same music again: no new fact" test "$(wc -l < "$T/state/events/ledger.jsonl")" -eq 1
check "and it says so" grep -q 'Not announced' "$T/publish2.log"
sed 's/D8 :|/D4 F4 :|/' "$ROOT/examples/first-light.abc" > "$T/revised.abc"
jamai-publish-melody --slug first-light "$T/revised.abc" > "$T/publish3.log" 2>&1
check "changed music: melody.revised" test "$(tail -n1 "$T/state/events/ledger.jsonl" | jq -r .type)" = melody.revised
check "the revision names what it revises" test -n "$(tail -n1 "$T/state/events/ledger.jsonl" | jq -r '.revises // empty')"
check "the manifest still has one melody" test "$(jq length "$T/site/melody/melodies.json")" -eq 1
check "no house address anywhere in the site" bash -c "! grep -rIl -E 'gmusicassembly|/home/gmusic|ferret-harmonic' '$T/site'"

echo "── hub"
HUB_PORT="$(free_port)"; RCV_PORT="$(free_port)"
JAMAI_HUB_ALLOW_PRIVATE_TARGETS=1 jamai-hub serve --port "$HUB_PORT" > "$T/hub.log" 2>&1 & PIDS+=($!)
python3 - "$RCV_PORT" "$T/received" > "$T/receiver.log" 2>&1 <<'EOF' &
import http.server, json, os, sys
port, out = int(sys.argv[1]), sys.argv[2]
os.makedirs(out, exist_ok=True)
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        n = len(os.listdir(out))
        with open(os.path.join(out, "%03d.json" % n), "wb") as fh:
            fh.write(json.dumps({"headers": dict(self.headers), "body": body.decode()}).encode())
        self.send_response(204); self.end_headers()
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
EOF
PIDS+=($!)
H="http://127.0.0.1:$HUB_PORT"
check "the hub answers" wait_for "curl -fsS $H/healthz"
check "the receiver answers" wait_for "curl -s -o /dev/null -X POST -d '{}' http://127.0.0.1:$RCV_PORT/warmup"
rm -f "$T/received"/*.json
check "the subscribe page is served" bash -c "curl -fsS $H/ | grep -q 'Receive each new melody'"
check "the melody page is served" bash -c "curl -fsS $H/melody/ | grep -q 'Selftest Atelier'"
check "a byte range answers 206" test "$(curl -s -o /dev/null -w '%{http_code}' -H 'Range: bytes=0-99' $H/melody/first-light.mp3)" = 206
check "a path outside the folder answers 404" test "$(curl -s -o /dev/null -w '%{http_code}' --path-as-is "$H/melody/../../config/secrets.env")" = 404
check "api/melodies leaves the ABC out" bash -c "curl -fsS $H/api/melodies | jq -e '.melodies[0] | has(\"abc\") | not'"
sub() { curl -s -X POST -H 'Content-Type: application/json' -d "$1" "$H/api/subscriptions"; }
check "no invite: refused" bash -c "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"url\":\"http://127.0.0.1:$RCV_PORT/hook\"}' $H/api/subscriptions | grep -q 403"
INVITE="$(jamai-hub invite "selftest")"
check "an invite code is issued" test -n "$INVITE"
check "the invite file holds no usable code" bash -c "! grep -q '$INVITE' '$T/state/hub/invites.json'"
RESP="$(sub "{\"url\":\"http://127.0.0.1:$RCV_PORT/hook\",\"label\":\"selftest\",\"invite\":\"$INVITE\"}")"
SUB_ID="$(printf '%s' "$RESP" | jq -r '.id // empty')"; SUB_SECRET="$(printf '%s' "$RESP" | jq -r '.secret // empty')"
check "with the invite: subscribed" test -n "$SUB_ID" -a -n "$SUB_SECRET"
check "the subscription is anchored on the last fact, not on the clock" bash -c "curl -fsS -H 'Authorization: Bearer $SUB_SECRET' $H/api/subscriptions/$SUB_ID | jq -e --arg id \"\$(tail -n1 '$T/state/events/ledger.jsonl' | jq -r .id)\" '.subscription.after_fact == \$id'"
check "the same invite twice: refused" bash -c "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"url\":\"http://127.0.0.1:$RCV_PORT/hook\",\"invite\":\"$INVITE\"}' $H/api/subscriptions | grep -q 403"
check "the wrong secret sees nothing" test "$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer nope' "$H/api/subscriptions/$SUB_ID")" = 404
check "the admin token lists subscriptions" bash -c "curl -fsS -H \"Authorization: Bearer \$(sed -n 's/^JAMAI_HUB_ADMIN_TOKEN=//p' '$T/config/secrets.env')\" $H/api/admin/subscriptions | jq -e '.subscriptions | length == 1'"
check "the admin list never shows a secret" bash -c "! curl -fsS -H \"Authorization: Bearer \$(sed -n 's/^JAMAI_HUB_ADMIN_TOKEN=//p' '$T/config/secrets.env')\" $H/api/admin/subscriptions | grep -q '$SUB_SECRET'"
sleep 4
check "facts older than the subscription are not sent" test "$(ls "$T/received" | wc -l)" -eq 0
printf 'X:1\nT:Second Light\nM:3/4\nL:1/8\nQ:1/4=96\nK:G\n|: G2 B2 d2 | c2 A2 F2 | G2 B2 d2 | g6 | e2 c2 A2 | d2 B2 G2 | A2 F2 D2 | G6 :|\n' > "$T/second.abc"
jamai-publish-melody "$T/second.abc" > "$T/publish4.log" 2>&1
check "a new melody is delivered" wait_for "test \$(ls '$T/received' | wc -l) -ge 1" 60
check "the signature verifies under the secret" python3 - "$T/received/000.json" "$SUB_SECRET" <<'EOF'
import hashlib, hmac, json, sys
got = json.load(open(sys.argv[1]))
headers = {k.lower(): v for k, v in got["headers"].items()}
want = "sha256=" + hmac.new(sys.argv[2].encode(), got["body"].encode(), hashlib.sha256).hexdigest()
fact = json.loads(got["body"])
assert headers["x-jamai-signature"] == want, "signature"
assert headers["x-jamai-event"] == "melody.published" and fact["slug"] == "second-light", "fact"
assert fact["url"] == "https://music.example.org/melody/second-light.mp3", "url"
EOF
sleep 4
check "the fact is delivered once" test "$(ls "$T/received" | wc -l)" -eq 1
check "the delivery is recorded" bash -c "jamai-hub deliveries 5 | grep -q '\"status\": \"delivered\"'"
check "a test delivery reaches the receiver" bash -c "curl -fsS -X POST -H 'Authorization: Bearer $SUB_SECRET' $H/api/subscriptions/$SUB_ID/ping | jq -e .delivered"
check "ending the subscription works" bash -c "curl -fsS -X DELETE -H 'Authorization: Bearer $SUB_SECRET' $H/api/subscriptions/$SUB_ID | jq -e .ended"

echo "── hub, as a public one (private targets refused)"
PUB_PORT="$(free_port)"
JAMAI_HUB_OPEN_SUBSCRIPTIONS=1 jamai-hub serve --port "$PUB_PORT" > "$T/hub-public.log" 2>&1 & PIDS+=($!)
P="http://127.0.0.1:$PUB_PORT"
check "the public hub answers" wait_for "curl -fsS $P/healthz"
code() { curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "$1" "$P/api/subscriptions"; }
check "a loopback target is refused" test "$(code '{"url":"https://127.0.0.1/hook"}')" = 400
check "a private LAN target is refused" test "$(code '{"url":"https://192.168.1.10/hook"}')" = 400
check "a plain http target is refused" test "$(code '{"url":"http://93.184.216.34/hook"}')" = 400
check "an unknown event type is refused" test "$(code '{"url":"https://93.184.216.34/hook","events":["everything"]}')" = 400

echo "── legacy sessions and MuseScore"
mkdir -p "$T/legacy/2025/notes" "$T/legacy/node_modules/x"
printf 'An older session. Free text sits above the tune, as in the real files.\n\n%% a comment\nX:1\nT:Old Session Theme\nC:an earlier agent\nM:6/8\nL:1/8\nQ:3/8=80\nK:Am\n|: A2 c e2 c | d2 B G2 B | A2 c e2 a | g3 e3 | f2 d B2 d | e2 c A2 c | B2 G E2 G | A6 :|\n' > "$T/legacy/2025/251017_old_session.abc"
printf 'not a tune\n' > "$T/legacy/2025/notes/empty.abc"
printf 'X:1\nT:Vendored\nK:C\nCDEF|\n' > "$T/legacy/node_modules/x/vendored.abc"
jamai-legacy list "$T/legacy" > "$T/legacy.out" 2>&1
check "jamai-legacy finds the session" grep -q 'Old Session Theme' "$T/legacy.out"
check "it reads the date from the file name" grep -q '^2025-10-17 ' "$T/legacy.out"
check "it leaves out vendored folders and files with no tune" grep -q '^1 session(s)$' "$T/legacy.out"
check "its JSON is valid" bash -c "jamai-legacy list --json '$T/legacy' | jq -e '.[0].key == \"Am\" and .[0].meter == \"6/8\"'"
jamai config set JAMAI_LEGACY_DIRS "$T/legacy" >/dev/null
check "JAMAI_LEGACY_DIRS is used when no folder is named" bash -c "jamai-legacy list | grep -q 'Old Session Theme'"
ms_bin=""; for c in musescore4 mscore4 mscore musescore musescore3 mscore3; do command -v "$c" >/dev/null 2>&1 && { ms_bin="$c"; break; }; done
if [ -n "$ms_bin" ]; then
  jamai-musescore --no-open --out "$T/ms" "$T/legacy/2025/251017_old_session.abc" > "$T/musescore.out" 2>&1
  check "jamai-musescore converts the session (with $ms_bin)" test "$?" -eq 0
  check "the MusicXML holds notes" grep -q '<note' "$T/ms/251017_old_session.musicxml"
  check "nothing was opened" grep -q 'opened.*no (--no-open)' "$T/musescore.out"
else
  skip "jamai-musescore: MuseScore is not installed on this machine (3 checks)"
  check "without MuseScore it says so and exits 3" bash -c "jamai-musescore --no-open '$T/legacy/2025/251017_old_session.abc' 2>&1 | grep -q 'MuseScore is not installed'; test \${PIPESTATUS[0]} -eq 3"
fi
jamai-publish-melody "$T/legacy/2025/251017_old_session.abc" > "$T/publish-legacy.log" 2>&1
check "the legacy session publishes" grep -q 'https://music.example.org/melody/old-session-theme.mp3' "$T/publish-legacy.log"
check "and is announced as a new melody" test "$(tail -n1 "$T/state/events/ledger.jsonl" | jq -r '.type + " " + .slug')" = "melody.published old-session-theme"

echo "── fixed defects (gmusic1007/jamai-core#4)"
# A fake catt and a fake voice: these checks reach no speaker and no network.
export JAMAI_CAST_STATE="$T/cast-state"
mkdir -p "$T/fake"
ffmpeg -nostats -loglevel error -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -q:a 9 "$T/fake/one-second.mp3"
printf '%s\n' '#!/usr/bin/env bash' \
  "echo \"\$*\" >> '$T/fake/catt.log'" \
  'case "$*" in' \
  "  scan) printf 'Scanning Chromecasts...\n10.0.0.2 - Bathroom speaker - Google Home Mini\n10.0.0.3 - Kitchen Tv - Google Cast Group\n10.0.0.4 - kitchen speaker - Google Home\n10.0.0.5 - bed - Google Cast Group\n10.0.0.6 - Bedroom speaker - Google Nest Mini\n10.0.0.7 - Television - Chromecast\n' ;;" \
  "  *status*) printf 'Time: 00:00:01 / 00:00:01 (100%%)\nState: PLAYING\n' ;;" \
  'esac' > "$T/fake/catt"
printf '%s\n' '#!/usr/bin/env bash' \
  "while [ \$# -gt 0 ]; do case \"\$1\" in --write-media) cp '$T/fake/one-second.mp3' \"\$2\"; shift 2 ;; *) shift ;; esac; done" > "$T/fake/edge-tts"
chmod +x "$T/fake/catt" "$T/fake/edge-tts"
say() { JAMAI_SAY_DEVICE= CATT="$T/fake/catt" EDGE_TTS="$T/fake/edge-tts" jamai-say "$@"; }
say -d Bathroom "hello" > "$T/say.out" 2>&1; say_rc=$?
check "jamai-say -d Bathroom finds \"Bathroom speaker\" and plays" bash -c "test $say_rc -eq 0 && grep -q 'Bathroom » → Bathroom speaker' '$T/say.out' && grep -q 'PREUVE' '$T/say.out'"
check "catt received the exact name" grep -q -- '^-d Bathroom speaker cast ' "$T/fake/catt.log"
check "the device names were cached in JAMAI_CAST_STATE" test -s "$T/cast-state/appareils.txt"
check "an exact name wins over a longer one (bed, not Bedroom speaker)" bash -c "export JAMAI_CAST_STATE='$T/cast-state' CATT='$T/fake/catt'; . '$ROOT/lib/jamai-devices.sh'; test \"\$(jamai_device_resolve bed)\" = bed"
say -d kitchen "hello" > "$T/say-kitchen.out" 2>&1; say_rc=$?
check "a name that fits two devices is refused, naming both (exit 2)" bash -c "test $say_rc -eq 2 && grep -q 'plusieurs appareils.*Kitchen Tv' '$T/say-kitchen.out' && grep -q 'kitchen speaker' '$T/say-kitchen.out'"
say -d garage "hello" > "$T/say-garage.out" 2>&1; say_rc=$?
check "an unknown name is refused with the names seen (exit 2)" bash -c "test $say_rc -eq 2 && grep -q 'Vus : .*Television' '$T/say-garage.out'"
JAMAI_SAY_DEVICE= jamai-say "hello" > /dev/null 2>&1; say_rc=$?
check "jamai-say without a device still refuses (exit 2)" test "$say_rc" -eq 2
JAMAI_CAST_DEVICE= CATT="$T/fake/catt" jamai-cast -d telev > "$T/cast.out" 2>&1; cast_rc=$?
check "jamai-cast -d telev finds Television, then asks for a page (exit 1)" bash -c "test $cast_rc -eq 1 && grep -q 'telev » → Television' '$T/cast.out'"
JAMAI_CAST_DEVICE= jamai-cast > /dev/null 2>&1; cast_rc=$?
check "jamai-cast without a device still refuses (exit 2)" test "$cast_rc" -eq 2
printf 'X:1\nT:Two Instruments\nM:4/4\nL:1/4\nQ:1/4=100\nK:C\nV:1\n%%%%MIDI program 24\nCDEF|G4|]\nV:2\n%%%%MIDI program 42\nC,4|C,4|]\n' > "$T/instruments.abc"
abc2midi "$T/instruments.abc" -o "$T/instruments.mid" > /dev/null 2>&1
jamai-midi.py "$T/instruments.mid" > "$T/instruments.txt" 2>&1
check "jamai-midi.py shows the nylon guitar (program 24)" grep -q 'programme 24 (Acoustic Guitar (nylon))' "$T/instruments.txt"
check "jamai-midi.py shows the cello (program 42)" grep -q 'programme 42 (Cello)' "$T/instruments.txt"
loudness() { ffmpeg -nostats -i "$1" -af volumedetect -f null - 2>&1 | sed -n 's/.*mean_volume: \(-\{0,1\}[0-9.]*\) dB.*/\1/p'; }
jamai-render --out "$T/gain0" --name g "$ROOT/examples/first-light.abc" > /dev/null 2>&1
jamai-render --out "$T/gain6" --name g --gain-db 6 "$ROOT/examples/first-light.abc" > /dev/null 2>&1
diff_db="$(awk -v a="$(loudness "$T/gain0/g.wav")" -v b="$(loudness "$T/gain6/g.wav")" 'BEGIN { printf "%.2f", b - a }')"
check "--gain-db 6 makes the render 6 dB louder (measured: $diff_db dB)" awk -v d="$diff_db" 'BEGIN { exit !(d > 5.5 && d < 6.5) }'
check "--gain-db refuses a word" bash -c "! jamai-render --gain-db loud '$ROOT/examples/first-light.abc' > /dev/null 2>&1"
jamai-publish-melody --gain-db 3 --no-announce "$ROOT/examples/first-light.abc" > /dev/null 2>&1
check "the manifest records the gain" test "$(jq -r '.[] | select(.slug == "first-light") | .gain_db' "$T/site/melody/melodies.json")" = 3

echo "── live MuseScore (a stand-in on its own port, never the real one)"
python3 "$ROOT/tests/fake_musescore.py" "$JAMAI_MUSESCORE_LIVE_PORT" "$T/live.log" > "$T/fake-ms.log" 2>&1 & PIDS+=($!)
jamai-musescore --install-plugin > "$T/plugin.out" 2>&1
check "--install-plugin puts the plugin in MuseScore's plugins folder" cmp -s "$ROOT/musescore/musescore-mcp-websocket.qml" "$T/msplugins/musescore-mcp-websocket.qml"
check "a second run leaves it and says so" bash -c "jamai-musescore --install-plugin | grep -q 'already installed'"
check "the stand-in answers" wait_for "jamai-musescore --live ping"
check "--live ping gets pong" bash -c "jamai-musescore --live ping | jq -e '.result == \"pong\"'"
check "--live sends an action with its params" bash -c "jamai-musescore --live addNote '{\"pitch\":60,\"duration\":{\"numerator\":1,\"denominator\":4}}' >/dev/null && tail -n1 '$T/live.log' | jq -e '.action == \"addNote\" and .params.pitch == 60 and .params.duration.denominator == 4'"
quiet_port="$(free_port)"
check "with nothing listening, it says how to start the plugin (exit 3)" bash -c "JAMAI_MUSESCORE_LIVE_PORT=$quiet_port jamai-musescore --live ping 2>&1 | grep -q 'enable \"musescore-mcp-websocket\"'; test \${PIPESTATUS[0]} -eq 3"

echo "── mcp"
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"selftest","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"jamai_list_melodies","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"jamai_chords","arguments":{"midi_path":"'"$T/site/melody/second-light.mid"'","beats_per_bar":3}}}' \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"jamai_legacy_list","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"musescore_live_status","arguments":{}}}' \
  '{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"musescore_live","arguments":{"action":"setTempo","params":{"bpm":72}}}}' \
  '{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"musescore_live","arguments":{"action":"rm"}}}' \
  | jamai-mcp > "$T/mcp.out" 2> "$T/mcp.err"
check "mcp answers initialize" bash -c "sed -n 1p '$T/mcp.out' | jq -e '.result.serverInfo.name == \"jamai-core\"'"
check "mcp lists 14 tools" bash -c "sed -n 2p '$T/mcp.out' | jq -e '.result.tools | length == 14'"
check "mcp lists the melodies" bash -c "sed -n 3p '$T/mcp.out' | jq -e '.result.isError == false and (.result.content[0].text | test(\"second-light\"))'"
check "mcp names chords from a MIDI file" bash -c "sed -n 4p '$T/mcp.out' | jq -e '.result.isError == false'"
check "mcp refuses an unknown tool" bash -c "sed -n 5p '$T/mcp.out' | jq -e '.error.code == -32601'"
check "mcp lists the legacy sessions" bash -c "sed -n 6p '$T/mcp.out' | jq -e '.result.isError == false and (.result.content[0].text | test(\"Old Session Theme\"))'"
check "mcp finds MuseScore listening" bash -c "sed -n 7p '$T/mcp.out' | jq -e '.result.isError == false and (.result.content[0].text | test(\"MuseScore is listening\"))'"
check "mcp changes the tempo in the open score" bash -c "sed -n 8p '$T/mcp.out' | jq -e '.result.isError == false' >/dev/null && tail -n1 '$T/live.log' | jq -e '.action == \"setTempo\" and .params.bpm == 72'"
check "mcp refuses an action MuseScore does not know" bash -c "sed -n 9p '$T/mcp.out' | jq -e '.result.isError == true'"
check "a notification gets no answer" test "$(wc -l < "$T/mcp.out")" -eq 9

echo "── package"
check "no house value in the packaged code" bash -c "! grep -rIn -E '/home/gmusic|gmusicassembly\.com|ferret-harmonic|tail3b11eb|192\.168\.[0-9]+\.[0-9]+' '$ROOT/bin' '$ROOT/lib' '$ROOT/publish' '$ROOT/render' '$ROOT/mcp' '$ROOT/listen' '$ROOT/workshop' '$ROOT/broadcast' '$ROOT/moments' '$ROOT/install.sh' '$ROOT/settings' '$ROOT/claude'"
check "plugin manifests are valid JSON" bash -c "jq -e . '$ROOT/.claude-plugin/marketplace.json' '$ROOT/claude/jamai/.claude-plugin/plugin.json' '$ROOT/claude/jamai/.mcp.json'"
"$ROOT/install.sh" --uninstall > "$T/uninstall.log" 2>&1
check "uninstall removes every link" test "$(find "$T/bin" -maxdepth 1 -type l | wc -l)" -eq 0
check "uninstall keeps the config" test -s "$T/config/jamai.env"

echo
echo "$pass passed, $fail failed, $skipped skipped"
[ "$fail" -eq 0 ] && echo "Whole. Install with: ./install.sh"
[ "$fail" -eq 0 ]
