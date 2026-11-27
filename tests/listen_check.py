#!/usr/bin/env python3
"""listen_check.py — the selftest's judge for the listen/ tools on tests/listen-grid.abc.

  listen_check.py measure <measure.json> <real-duration-s>     length right, tempo 120 ± 2
  listen_check.py beats   <beats.json>                          about two beats a second
  listen_check.py roots   <chords-audio.json> <min-share>       chord roots, beat by beat
  listen_check.py key     <chords-audio.json>                   E minor, by both methods
  listen_check.py grid    <chords-audio.json> <min-bars>        bar cells of the grid

Exit 0 when the check holds, 1 when it does not, and say what was found either way.
The fixture: 16 bars of 4/4 at 120 BPM (2 s a bar), E minor,
| Em Em B7 B7 | Em Em B7 B7 | G G A A | G G B7 B7 |, a voice singing over the guitar.
"""
import json
import sys

GRID = "Em Em B7 B7 Em Em B7 B7 G G A A G G B7 B7".split()
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
BAR_S = 2.0


def root(chord):
    return NAMES.index(chord[:2] if len(chord) > 1 and chord[1] == '#' else chord[0])


def main():
    what, path = sys.argv[1], sys.argv[2]
    d = json.load(open(path, encoding="utf-8"))
    if what == "measure":
        real = float(sys.argv[3])
        print("duration %.2f s (real %.2f), tempo %.2f BPM" % (d["duration_s"], real, d["tempo_bpm"]))
        return abs(d["duration_s"] - real) <= 0.02 * real and abs(d["tempo_bpm"] - 120) <= 2
    if what == "beats":
        print("%d beats" % len(d["beats"]))
        return 60 <= len(d["beats"]) <= 80
    if what == "roots":
        ok = tot = 0
        for p in d["per_unit"]:
            bar = int((p["t"] + p["d"] / 2) // BAR_S)
            if not p["chord"] or bar >= len(GRID):
                continue
            tot += 1
            ok += root(p["chord"]) == root(GRID[bar])
        print("%d of %d beats on the right root" % (ok, tot))
        return tot > 0 and ok / tot >= float(sys.argv[3])
    if what == "key":
        k, c = d["key_krumhansl"][0][0], d["key_from_chords"][0][0]
        print("Krumhansl %s, chords %s" % (k, c))
        return k == "E minor" and c == "E minor"
    if what == "grid":
        right = 0
        for g in d["grid"]:
            bar = int(round(g["t"] / BAR_S))
            if bar < len(GRID) and len(g["cell"]) == 1 and root(g["cell"][0]) == root(GRID[bar]):
                right += 1
        print("%d bars of %d hold one chord with the right root" % (right, len(GRID)))
        return right >= int(sys.argv[3])
    raise SystemExit("unknown check: %s" % what)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
