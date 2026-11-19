#!/bin/sh
# setup.sh — add the JamAI apt repository to this machine, once. Then: sudo apt install jamai
#
#   curl -fsSL https://apt.gmusicassembly.com/setup.sh | sudo bash
#
# What it does, and nothing else:
#   1. saves the repository's signing key to /etc/apt/keyrings/jamai.gpg
#   2. writes /etc/apt/sources.list.d/jamai.list, trusting that key for this repository only
#   3. runs apt-get update
# To undo: sudo rm /etc/apt/keyrings/jamai.gpg /etc/apt/sources.list.d/jamai.list
set -eu

BASE="__BASE_URL__"
FINGERPRINT="__FINGERPRINT__"

if [ "$(id -u)" != 0 ]; then
  echo "Run it with sudo:  curl -fsSL $BASE/setup.sh | sudo bash" >&2
  exit 1
fi
command -v apt-get > /dev/null || { echo "This machine has no apt: use the one-line install from https://github.com/gmusic1007/jamai-core" >&2; exit 1; }

install -d -m 0755 /etc/apt/keyrings
curl -fsSL "$BASE/jamai.gpg" -o /etc/apt/keyrings/jamai.gpg.new
# Check the key is the one this script names, before trusting it.
if command -v gpg > /dev/null; then
  got="$(gpg --show-keys --with-colons /etc/apt/keyrings/jamai.gpg.new 2>/dev/null | awk -F: '/^fpr/ {print $10; exit}')"
  if [ "$got" != "$FINGERPRINT" ]; then
    rm -f /etc/apt/keyrings/jamai.gpg.new
    echo "The downloaded key is not the JamAI key ($FINGERPRINT). Nothing was changed." >&2
    exit 1
  fi
fi
mv /etc/apt/keyrings/jamai.gpg.new /etc/apt/keyrings/jamai.gpg
chmod 0644 /etc/apt/keyrings/jamai.gpg

echo "deb [signed-by=/etc/apt/keyrings/jamai.gpg] $BASE stable main" > /etc/apt/sources.list.d/jamai.list
apt-get update

echo
echo "The JamAI repository is added (key $FINGERPRINT)."
echo "Now:  sudo apt install jamai"
