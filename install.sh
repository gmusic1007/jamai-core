#!/usr/bin/env bash
# install.sh — install jamai-core with one command.
#
#   ./install.sh               ask the settings, link the commands, check the tools
#   ./install.sh --yes         the same with no questions: defaults, or values already in the environment
#   ./install.sh --check       change nothing; exit 1 if a command is not linked to this checkout
#   ./install.sh --dry-run     change nothing; say what an install would do
#   ./install.sh --uninstall   remove the links this installer made (your config stays)
#
# From nothing, once you can read the repository:
#   git clone https://github.com/gmusic1007/jamai-core.git && ./jamai-core/install.sh
# Piped (curl -fsSL …/install.sh | bash) it clones into ${JAMAI_CORE_ROOT:-~/.local/share/jamai-core} first.
#
# WHY LINKS AND NOT COPIES: a skill or an agent calls `jamai-midi.py` by name and never
# learns where this checkout lives. Move the checkout, run this again, nothing else changes.
#
# Exit codes: 0 done or clean · 1 drift found (--check) · 2 cannot proceed
set -euo pipefail

REPO_URL="${JAMAI_REPO_URL:-https://github.com/gmusic1007/jamai-core.git}"
SELF="${BASH_SOURCE[0]:-}"
ROOT=""
[ -n "$SELF" ] && [ -f "$SELF" ] && ROOT="$(cd "$(dirname "$(readlink -f "$SELF")")" && pwd)"

# Piped install: there is no checkout beside this script yet. Fetch one and hand over.
if [ -z "$ROOT" ] || [ ! -f "$ROOT/settings" ]; then
  command -v git >/dev/null || { echo "install.sh: git is needed to fetch jamai-core" >&2; exit 2; }
  ROOT="${JAMAI_CORE_ROOT:-$HOME/.local/share/jamai-core}"
  if [ -d "$ROOT/.git" ]; then git -C "$ROOT" pull --ff-only
  else git clone "$REPO_URL" "$ROOT"; fi
  exec bash "$ROOT/install.sh" "$@"
fi

TOOLS=(bin/jamai
       listen/jamai-midi.py listen/jamai-chords.py listen/jamai-chords-audio.py
       listen/jamai-measure.py listen/jamai-grille.py
       render/jamai-render render/jamai-musescore render/jamai-tab.py render/jamai-score-video.py render/jamai-scroll.py
       publish/jamai-publish-melody publish/jamai-hub
       workshop/jamai-legacy
       broadcast/jamai-cast broadcast/jamai-say
       moments/routine
       mcp/jamai-mcp
       suno/jamai-suno)

mode=install; yes=0
for arg in "$@"; do
  case "$arg" in
    --check) mode=check ;; --dry-run) mode=dry ;; --uninstall) mode=uninstall ;;
    --yes|-y) yes=1 ;;
    -h|--help) sed -n '2,/^set -euo/p' "$SELF" | sed -e 's/^# \{0,1\}//' -e '/^set -euo/d'; exit 0 ;;
    *) echo "install.sh: unknown option $arg" >&2; exit 2 ;;
  esac
done

# The settings come first: where the commands are linked is one of them.
if [ "$mode" = install ]; then
  if [ "$yes" -eq 1 ]; then "$ROOT/bin/jamai" setup --yes; else "$ROOT/bin/jamai" setup; fi
fi
TARGET="$("$ROOT/bin/jamai" config get JAMAI_BIN)"
STAMP="$(date +%y%m%d%H%M%S)"

linked=0; drift=0
for rel in "${TOOLS[@]}"; do
  src="$ROOT/$rel"; name="$(basename "$rel")"; dst="$TARGET/$name"
  [ -f "$src" ] || { echo "✗ $name — $rel is missing from this checkout"; drift=$((drift + 1)); continue; }
  current=""; [ -e "$dst" ] || [ -L "$dst" ] && current="$(readlink -f "$dst" 2>/dev/null || true)"
  same=0; [ -n "$current" ] && [ "$current" = "$(readlink -f "$src")" ] && same=1
  case "$mode" in
    check)
      if [ "$same" -eq 1 ]; then echo "✓ $name"; linked=$((linked + 1))
      elif [ -n "$current" ]; then echo "✗ $name — points at $current"; drift=$((drift + 1))
      else echo "✗ $name — not linked"; drift=$((drift + 1)); fi ;;
    dry)
      if [ "$same" -eq 1 ]; then echo "= $name — already linked"
      elif [ -n "$current" ]; then echo "~ $name — would move $dst to $dst.bak-$STAMP, then link"
      else echo "+ $name — would link"; fi ;;
    uninstall)
      if [ -L "$dst" ] && [ "$same" -eq 1 ]; then rm "$dst"; echo "removed: $name"; linked=$((linked + 1)); fi ;;
    install)
      mkdir -p "$TARGET"
      [ -x "$src" ] || chmod +x "$src"
      if [ "$same" -eq 1 ]; then echo "= $name"
      else
        # Whatever is already there is kept, never deleted.
        if [ -e "$dst" ] || [ -L "$dst" ]; then mv "$dst" "$dst.bak-$STAMP"; echo "  kept the previous $name as $name.bak-$STAMP"; fi
        ln -sfn "$src" "$dst"; echo "→ $name"
      fi
      linked=$((linked + 1)) ;;
  esac
done

case "$mode" in
  check)
    echo "$linked / ${#TOOLS[@]} linked in $TARGET"
    [ "$drift" -eq 0 ] || { echo "Drift found. Nothing was written. Run ./install.sh to repair."; exit 1; } ;;
  dry)       echo "Dry run. Nothing was written." ;;
  uninstall) echo "$linked link(s) removed from $TARGET. Your config in $("$ROOT/bin/jamai" config path) is untouched." ;;
  install)
    echo "$linked / ${#TOOLS[@]} commands linked in $TARGET"
    # Live control of an open score: the MuseScore plugin goes in place when MuseScore is here.
    for ms in "${JAMAI_MUSESCORE_BIN:-}" musescore4 mscore4 mscore musescore; do
      if [ -n "$ms" ] && command -v "$ms" >/dev/null 2>&1; then
        echo; "$ROOT/render/jamai-musescore" --install-plugin; break
      fi
    done
    echo
    "$ROOT/bin/jamai" doctor || true
    cat <<EOF

Next:
  jamai-publish-melody examples/first-light.abc     render and publish a first melody
  jamai hub serve                                   the melody page and its subscriptions, on your machine
  jamai-legacy list <folder>                        older ABC sessions, ready to open or publish
  jamai config show                                 every setting and where its value comes from
EOF
    ;;
esac
