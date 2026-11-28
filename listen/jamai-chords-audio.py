#!/usr/bin/env python3
"""jamai-chords-audio.py — accords, grille et tonalité depuis un ENREGISTREMENT, pas un MIDI.

`jamai-chords.py` lit un fichier MIDI, où chaque hauteur est certaine. Ici la source est une
prise réelle : une guitare, une voix par-dessus, une pièce. Il n'y a pas de vérité exacte à en
tirer, seulement une estimation — et le devoir de dire à quel point elle est sûre.

  jamai-chords-audio.py prise.wav [--temps temps.json | --fenetre 1.0] [--temps-par-mesure 4]
                        [--lissage 0.2] [--debut 0] [--fin 68] [--par-temps] [--json]

    --temps <fichier>      les temps de jamai-measure.py --temps (sinon : détectés ici)
    --fenetre <s>          des fenêtres fixes au lieu des temps
    --temps-par-mesure <n> la grille se compte en n temps (défaut 4 ; 3 pour une valse)
    --lissage <p>          prix d'un changement d'accord (défaut 0,2 ; 0 = chaque temps seul)
    --par-temps            une ligne par temps, en plus des accords et de la grille
    --json                 tout en JSON

Méthode (numpy seulement, lib/jamai_audio.py) : pour chaque temps, un spectre fin (1,35 Hz par
case), la basse (E1–E3) à part de l'accord (C3–C7), un gabarit d'accord par fondamentale, la
basse qui vote pour la fondamentale, puis un chemin de Viterbi qui fait payer chaque
changement. La grille place les barres là où les mesures changent le moins d'accord à
l'intérieur, et permet une mesure d'un temps de plus ou de moins quand l'harmonie le demande :
une prise live ne garde pas la même phase pendant deux minutes. La tonalité se tranche deux
fois : Krumhansl sur la basse et l'aigu, et la fonction des accords.

Mesuré le 2026-11-27 sur la prise live de « Monde immonde » (140 s), contre la grille
retenue par JamAI après l'écoute, la vidéo et la recette librosa de la session :
                                          fondamentales justes   tonalité
  l'ancienne version (fenêtres 1 s)          30 % mix · 38 % guitare   ré majeur « franc » — faux
  recette librosa de la session (beatchroma)            58 % guitare
  cette version                              68 % mix · 73 % guitare   mi mineur, deux méthodes
  sa grille tombe sur 20 des 35 barres de référence sur la guitare séparée, 2 sur le mix.
L'ancienne départageait deux gabarits faits des mêmes notes (G6 et Em7, Asus4 et Dsus2) par
l'ordre alphabétique : sans basse, elle ne pouvait pas faire autrement.

Ce que l'outil NE fait pas, et qu'il ne faut pas lui faire dire :
  - une voix forte par-dessus pollue l'aigu : sur un mix, regarde la colonne « force », ou
    sépare d'abord la guitare (jamai-separe.py) ;
  - la force est l'écart à la meilleure autre fondamentale. Négative : sur ce temps seul, une
    autre fondamentale gagnait, et le lissage a gardé l'accord de ses voisins ;
  - une 7e, une 9e ou une sus sont des nuances qu'il entend mal ; la fondamentale et le mode
    (majeur, mineur) sont ce qu'il mesure le mieux ;
  - la barre de mesure est une proposition : les mesures irrégulières sont nommées pour
    qu'on puisse les contredire.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
import numpy as np  # noqa: E402
import jamai_audio as ja  # noqa: E402

HESITE = 0.03


def segments_from_beats(beats, start, end):
    b = [t for t in beats if start <= t < end]
    if not b:
        return []
    return list(zip(b, b[1:] + [min(end, b[-1] + (b[-1] - b[-2] if len(b) > 1 else 0.5))]))


def bar_lines(per, n, irregular=2.0):
    """Where the bar lines fall: a segmentation of the beats into bars of n beats, with an
    occasional bar of n−1 or n+1 when the harmony asks for it.

    A live take does not keep a single phase for two minutes: a held breath, a strum added
    before the chorus, and a global phase puts every chord change of the next section on beat
    3. Dynamic programming over the beats: each bar costs the chord changes inside it, an
    irregular bar costs `irregular` more, the first bar may be a pickup of any length.
    Returns the indices of the beats that start a bar."""
    m = len(per)
    if m == 0:
        return []
    change = [0] * m
    for k in range(1, m):
        change[k] = int(bool(per[k]["chord"]) and per[k]["chord"] != per[k - 1]["chord"])

    def inside(a, b):
        return sum(change[a + 1:b])

    INF = float("inf")
    cost, prev = [INF] * (m + 1), [-1] * (m + 1)
    cost[0] = 0.0
    for i in range(1, m + 1):
        for L in range(1, n + 2):
            j = i - L
            if j < 0:
                break
            if j == 0:
                c = inside(0, i) if L <= n else INF          # a pickup, never longer than a bar
            elif L == n:
                c = cost[j] + inside(j, i)
            elif L in (n - 1, n + 1) and n > 2:
                c = cost[j] + inside(j, i) + irregular
            else:
                c = INF
            if c < cost[i]:
                cost[i], prev[i] = c, j
    starts, i = [], m
    while i > 0:
        j = prev[i]
        starts.append(j)
        i = j
    return sorted(starts)


def bar_cells(per, starts):
    """One cell per bar, each half of the bar named by the chord that holds most of its beats.
    A cell shows one chord, or two when the halves differ: that is how a musician writes a
    grid, and it hides the passing beats the smoothing kept."""
    cells = []
    for a, b in zip(starts, starts[1:] + [len(per)]):
        bar = per[a:b]
        h = max(1, (len(bar) + 1) // 2)
        cell = []
        for half in (bar[:h], bar[h:]):
            names = Counter(p["chord"] for p in half if p["chord"])
            if names:
                top = names.most_common(1)[0][0]
                if not cell or cell[-1] != top:
                    cell.append(top)
        cells.append({"t": bar[0]["t"], "beats": len(bar), "cell": cell})
    return cells


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fichier")
    ap.add_argument("--temps", help="JSON de jamai-measure.py --temps")
    ap.add_argument("--fenetre", type=float, help="fenêtres fixes de tant de secondes")
    ap.add_argument("--temps-par-mesure", type=int, default=4)
    ap.add_argument("--lissage", type=float, default=0.2)
    ap.add_argument("--debut", type=float, default=0.0)
    ap.add_argument("--fin", type=float, default=1e9)
    ap.add_argument("--par-temps", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        x, sr = ja.load(a.fichier)
    except (ValueError, OSError) as exc:
        sys.exit("  ✗ %s" % exc)
    dur = len(x) / sr
    fin = min(a.fin, dur)

    bpm = None
    if a.fenetre:
        segs, unit = [], "fenêtre"
        t = a.debut
        while t < fin:
            segs.append((t, min(t + a.fenetre, fin)))
            t += a.fenetre
    else:
        unit = "temps"
        if a.temps:
            with open(a.temps, encoding="utf-8") as fh:
                d = json.load(fh)
            beats, bpm = d["beats"], d.get("bpm")
        else:
            env, fps = ja.onset_envelope(x, sr)
            bpm, _ = ja.tempo(env, fps)
            beats = ja.beats(env, fps, bpm)
        segs = segments_from_beats(beats, a.debut, fin)
    if not segs:
        sys.exit("  ✗ aucun temps entre %.1f et %.1f s" % (a.debut, fin))

    chroma = [ja.bass_treble(x, sr, s, e) for s, e in segs]
    rows = [ja.chord_scores(tr, bs) for bs, tr in chroma]
    path = ja.smooth(rows, a.lissage) if a.lissage > 0 else [
        (int(np.argmax(r)) if r is not None else None) for r in rows]
    per = []
    for (s, e), (bs, tr), r, j in zip(segs, chroma, rows, path):
        if j is None:
            per.append({"t": round(s, 3), "d": round(e - s, 3), "chord": None})
            continue
        per.append({"t": round(s, 3), "d": round(e - s, 3), "chord": ja.label(j),
                    "force": round(ja.force(r, j), 3),
                    "bass": ja.NAMES[int(np.argmax(bs))] if bs.sum() > 1e-9 else None})

    # accords : les temps consécutifs du même accord, fondus
    chords = []
    for p in per:
        if chords and chords[-1]["chord"] == p["chord"]:
            c = chords[-1]
            c["d"] = round(p["t"] + p["d"] - c["t"], 3)
            c["n"] += 1
            if p.get("force") is not None:
                c["force"] = min(c["force"], p["force"])
                c["basses"][p["bass"]] += 1
        else:
            chords.append({"t": p["t"], "d": p["d"], "n": 1, "chord": p["chord"], "force": p.get("force"),
                           "basses": Counter([p.get("bass")])})
    for c in chords:
        c["bass"] = c.pop("basses").most_common(1)[0][0]

    # grille
    grid, counts = [], []
    if unit == "temps":
        n = max(1, a.temps_par_mesure)
        starts = bar_lines(per, n)
        grid = bar_cells(per, starts)
        counts = [i for i, g in enumerate(grid) if g["beats"] != n and i > 0]

    # tonalité
    B = sum(bs / (bs.sum() or 1) for bs, tr in chroma)
    T = sum(tr / (tr.sum() or 1) for bs, tr in chroma)
    krum = ja.key_profile(B + T)
    timeline = [(ja.CANDIDATES[j][0], ja.CANDIDATES[j][1], e - s) for (s, e), j in zip(segs, path) if j is not None]
    by_chords = ja.key_from_chords(timeline)
    agree = krum[0][1] == by_chords[0][1]

    if a.json:
        print(json.dumps({"file": a.fichier, "duration_s": round(dur, 3), "unit": unit,
                          "tempo_bpm": round(bpm, 2) if bpm else None, "smoothing": a.lissage,
                          "chords": chords, "beats_per_bar": a.temps_par_mesure if grid else None,
                          "pickup_beats": grid[0]["beats"] if grid and grid[0]["beats"] < a.temps_par_mesure else 0,
                          "irregular_bars": [i + 1 for i in counts],
                          "grid": grid, "per_unit": per if a.par_temps else None,
                          "key_krumhansl": [[n, round(r, 3)] for r, n, *_ in krum[:4]],
                          "key_from_chords": [[n, round(s, 3)] for s, n in by_chords[:4]],
                          "key_methods_agree": agree}, ensure_ascii=False, indent=1))
        return

    print(f"# {a.fichier} · {dur:.1f} s · de {a.debut:.1f} à {fin:.1f} s · par {unit}"
          + (f" ({bpm:.1f} BPM)" if bpm else f" ({a.fenetre:.2f} s)" if a.fenetre else "")
          + f" · lissage {a.lissage}")
    if a.par_temps:
        print(f"\n {unit:>8}   accord    force  basse")
        for p in per:
            if p["chord"] is None:
                print(f" {p['t']:7.2f}s     —")
            else:
                print(f" {p['t']:7.2f}s  {p['chord']:>7}   {p['force']:5.3f}  {p['bass'] or '':3}"
                      + ("   ← hésite" if p["force"] < HESITE else ""))
    print(f"\n## accords ({len(chords)} changements)")
    print(f"   début    durée  {unit:>7}   accord   basse  force min")
    for c in chords:
        if c["chord"] is None:
            print(f"  {c['t']:6.1f}s  {c['d']:5.1f}s  {c['n']:6d}        —")
            continue
        print(f"  {c['t']:6.1f}s  {c['d']:5.1f}s  {c['n']:6d}   {c['chord']:>7}  {c['bass'] or '':5}  {c['force']:.3f}"
              + ("   ← hésite" if c["force"] < HESITE else ""))
    if grid:
        n = a.temps_par_mesure
        print(f"\n## grille — {n} temps par mesure, la barre là où les mesures changent le moins d'accord")
        if grid and grid[0]["beats"] < n:
            print(f"   levée de {grid[0]['beats']} temps, puis la première barre à {grid[1]['t']:.2f} s" if len(grid) > 1 else "")
        if counts:
            print("   mesures irrégulières (un temps de plus ou de moins, à vérifier à l'oreille) : "
                  + ", ".join(f"m.{i + 1} ({grid[i]['beats']} temps)" for i in counts))
        for k in range(0, len(grid), 4):
            line = grid[k:k + 4]
            print(f"  {line[0]['t']:6.1f}s  m.{k + 1:<3d} |"
                  + "|".join(f" {' '.join(g['cell']) or '—':<9}" + ("*" if g["beats"] != n else " ") for g in line) + "|")
    print("\n## tonalité")
    print("   Krumhansl (basse + aigu) : " + " · ".join(f"{n} {r:+.3f}" for r, n, *_ in krum[:3]))
    print("   fonction des accords     : " + " · ".join(f"{n} {s:.2f}" for s, n in by_chords[:3]))
    print("   → " + (f"{krum[0][1]} : les deux méthodes s'accordent" if agree else
                     f"les deux méthodes divergent ({krum[0][1]} / {by_chords[0][1]}) : ton oreille tranche"))
    print("\n  Fondamentale et mode d'abord ; les 7e, 9e et sus sont des nuances à vérifier à l'oreille.")


if __name__ == "__main__":
    main()
