#!/usr/bin/env bash
# build-repo.sh — add packages to the JamAI apt repository and sign it.
#
#   packaging/apt/build-repo.sh <site folder> <package.deb>...
#
# <site folder> is the published repository: the gh-pages branch, served at APT_BASE_URL
# (default https://apt.gmusicassembly.com). Packages already in its pool stay: apt can still
# install an older version. The signing key comes from the gpg keyring in GNUPGHOME, or from
# APT_SIGNING_KEY (an armored private key, as the release workflow passes it).
#
# Layout written:
#   pool/main/j/jamai/<package>.deb
#   dists/stable/main/binary-{all,amd64,arm64}/Packages(.gz)
#   dists/stable/Release, InRelease, Release.gpg
#   jamai.gpg, jamai.asc        the public key
#   setup.sh                    adds the repository to a machine
#   index.html, CNAME, .nojekyll
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SITE="${1:?usage: build-repo.sh <site folder> <package.deb>...}"; shift
BASE="${APT_BASE_URL:-https://apt.gmusicassembly.com}"
ARCHS="all amd64 arm64"

if [[ -n "${APT_SIGNING_KEY:-}" ]]; then
  export GNUPGHOME="$(mktemp -d)"; chmod 700 "$GNUPGHOME"
  trap 'rm -rf "$GNUPGHOME"' EXIT
  printf '%s\n' "$APT_SIGNING_KEY" | gpg --batch --quiet --import
fi
FPR="$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')"
[[ -n "$FPR" ]] || { echo "build-repo.sh: no signing key (GNUPGHOME or APT_SIGNING_KEY)" >&2; exit 2; }

mkdir -p "$SITE/pool/main/j/jamai"
for deb in "$@"; do
  name="$(dpkg-deb -f "$deb" Package)"
  [[ "$name" == jamai ]] || { echo "build-repo.sh: $deb is package $name, not jamai" >&2; exit 2; }
  cp "$deb" "$SITE/pool/main/j/jamai/"
done

cd "$SITE"
for arch in $ARCHS; do
  d="dists/stable/main/binary-$arch"; mkdir -p "$d"
  # An "all" package is listed for every architecture, so any machine finds it.
  apt-ftparchive packages pool > "$d/Packages"
  gzip -9nkf "$d/Packages"
done
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin="G.Music Assembly" \
  -o APT::FTPArchive::Release::Label="JamAI" \
  -o APT::FTPArchive::Release::Suite="stable" \
  -o APT::FTPArchive::Release::Codename="stable" \
  -o APT::FTPArchive::Release::Architectures="$ARCHS" \
  -o APT::FTPArchive::Release::Components="main" \
  -o APT::FTPArchive::Release::Description="JamAI: write, hear, publish and share music" \
  release dists/stable > dists/stable/Release.tmp
mv dists/stable/Release.tmp dists/stable/Release
rm -f dists/stable/InRelease dists/stable/Release.gpg
gpg --batch --yes --digest-algo SHA512 --local-user "$FPR" --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --batch --yes --digest-algo SHA512 --local-user "$FPR" --armor --detach-sign -o dists/stable/Release.gpg dists/stable/Release

gpg --export "$FPR" > jamai.gpg
gpg --armor --export "$FPR" > jamai.asc
sed -e "s|__BASE_URL__|$BASE|g" -e "s|__FINGERPRINT__|$FPR|g" "$HERE/setup.sh" > setup.sh
host="${BASE#https://}"; host="${host%%/*}"
[[ "$host" == *.github.io ]] || printf '%s\n' "$host" > CNAME
touch .nojekyll

versions="$(for f in pool/main/j/jamai/*.deb; do dpkg-deb -f "$f" Version; done | sort -V -r | sed 's/.*/<li><code>&<\/code><\/li>/' | tr -d '\n')"
sed -e "s|__BASE_URL__|$BASE|g" -e "s|__FINGERPRINT__|$FPR|g" -e "s|__VERSIONS__|$versions|g" "$HERE/index.html" > index.html

echo "signed with $FPR"
echo "packages: $(ls pool/main/j/jamai | tr '\n' ' ')"
