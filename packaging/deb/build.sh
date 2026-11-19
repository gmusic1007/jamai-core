#!/usr/bin/env bash
# build.sh — build jamai-core as a Debian package, so `apt install ./jamai-core_<v>_all.deb`
# brings the program and the system tools it needs in one step.
#
#   packaging/deb/build.sh            writes dist/jamai_<VERSION>_all.deb
#
# The package is named `jamai` (apt install jamai). Until 0.4.1 it was `jamai-core`: this one
# replaces it, so an install of jamai-core upgrades cleanly.
#
# Layout of the package:
#   /usr/lib/jamai-core/      the repository's files, as they are in git (no .git, no .pde)
#   /usr/bin/<command>        one link per command, the same list install.sh links
#
# The package writes nothing in anyone's home folder. Each person runs `jamai setup` once,
# which asks the settings and writes ~/.config/jamai/jamai.env.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
OUT="$ROOT/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# The files git tracks, minus the decomposition records: what the repository publishes.
mkdir -p "$STAGE/usr/lib/jamai-core" "$STAGE/usr/bin" "$STAGE/DEBIAN" "$OUT" "$STAGE/usr/share/doc/jamai"
git -C "$ROOT" ls-files -z | grep -z -v -E '^(\.pde/|packaging/|\.claude/)' \
  | (cd "$ROOT" && xargs -0 cp --parents -t "$STAGE/usr/lib/jamai-core")

# The commands: read from install.sh, so the two lists cannot drift apart.
mapfile -t TOOLS < <(sed -n '/^TOOLS=(/,/)$/p' "$ROOT/install.sh" | grep -o -E '[a-z]+/[A-Za-z0-9._-]+')
for rel in "${TOOLS[@]}"; do
  [ -f "$STAGE/usr/lib/jamai-core/$rel" ] || { echo "build.sh: $rel is not tracked by git" >&2; exit 2; }
  chmod 755 "$STAGE/usr/lib/jamai-core/$rel"
  ln -s "/usr/lib/jamai-core/$rel" "$STAGE/usr/bin/$(basename "$rel")"
done

# What Debian expects of every package: its licence and its history, under /usr/share/doc.
{ echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
  echo "Upstream-Name: jamai-core"; echo "Source: https://github.com/gmusic1007/jamai-core"; echo
  echo "Files: *"; echo "Copyright: 2026 Jerry / G.Music Assembly"; echo "License: MIT"; echo
  echo "Files: musescore/musescore-mcp-websocket.qml"; echo "Copyright: 2025 George Chen"; echo "License: MIT"; echo
  echo "License: MIT"; sed 's/^$/./; s/^/ /' "$ROOT/LICENSE"; } > "$STAGE/usr/share/doc/jamai/copyright"
{ echo "jamai ($VERSION) stable; urgency=medium"; echo
  git -C "$ROOT" log -20 --format="  * %s" | sed 's/^  \* \[#[0-9]*\] /  * /'; echo
  echo " -- gmusic1007 <204083825+gmusic1007@users.noreply.github.com>  $(date -R)"; } | gzip -9n > "$STAGE/usr/share/doc/jamai/changelog.Debian.gz"

size_kb="$(du -sk "$STAGE/usr" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: jamai
Version: $VERSION
Architecture: all
Maintainer: gmusic1007 <204083825+gmusic1007@users.noreply.github.com>
Installed-Size: $size_kb
Depends: bash, python3, abcmidi, fluidsynth, fluid-soundfont-gm, lame, ffmpeg, jq, curl
Recommends: abcm2ps, librsvg2-bin, imagemagick, python3-numpy, python3-scipy, python3-pil
Provides: jamai-core
Replaces: jamai-core (<< 0.4.2)
Breaks: jamai-core (<< 0.4.2)
Section: sound
Priority: optional
Homepage: https://github.com/gmusic1007/jamai-core
Description: write, hear, publish and share music from ABC notation
 JamAI's composition workshop. Render ABC to MIDI, WAV, MP3 and an engraved
 score, name the chords of a MIDI file or a recording, make score videos and
 guitar tablature, publish melodies to a page of your own, and let people
 subscribe to receive each new melody by signed webhook. Offers its tools to
 AI agents as an MCP server and a Claude plugin.
 .
 After installing, each person runs jamai setup once.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
  echo "jamai-core is installed. Each person runs, once:  jamai setup   then:  jamai doctor"
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

deb="$OUT/jamai_${VERSION}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$deb" >/dev/null
echo "$deb"
echo "commands: ${#TOOLS[@]} · files: $(find "$STAGE/usr/lib/jamai-core" -type f | wc -l) · $(du -h "$deb" | cut -f1)"
