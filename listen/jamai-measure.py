#!/usr/bin/env python3
"""jamai-measure.py — mesure d'un enregistrement : structure, tempo, temps, hauteurs, timbre.

  jamai-measure.py <prise.wav|.m4a|.mp3|.mp4> [--temps temps.json] [--json]

    --temps <fichier>   écrit les temps détectés (secondes) en JSON, pour jamai-chords-audio.py
    --json              tout en JSON au lieu du rapport

Numpy seulement. Tout passe par lib/jamai_audio.py, que jamai-chords-audio.py partage.

Ce qui a changé le 2026-11-27, mesuré sur la prise live de « Monde immonde » (140 s, stéréo) :
  - l'ancienne version lisait un WAV stéréo comme du mono : 279,98 s, 64,6 BPM et des hauteurs
    fausses. La lecture passe maintenant par ffmpeg, qui mélange les canaux ;
  - son chroma venait d'une FFT de 2048 points à 44,1 kHz (21,5 Hz par case) : sous 500 Hz,
    une note tombait sur la classe de la case voisine. Le profil se calcule maintenant à
    1,35 Hz par case ;
  - elle donne les TEMPS, pas seulement un tempo : 301 temps sur cette prise, le même compte
    que librosa.beat.beat_track, et un tempo de 129,4 BPM contre 129,2 pour librosa.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
import numpy as np  # noqa: E402
import jamai_audio as ja  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fichier")
    ap.add_argument("--temps", help="écrit les temps (secondes) dans ce fichier JSON")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        x, sr = ja.load(a.fichier)
    except (ValueError, OSError) as exc:
        sys.exit("  ✗ %s" % exc)
    dur = len(x) / sr

    # ── enveloppe RMS par 100 ms : où ça joue, où c'est silencieux
    hop = sr // 10
    env_rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, max(len(x) - hop, 1), hop)])
    db = 20 * np.log10(env_rms + 1e-9)
    floor = float(np.percentile(db, 10)) if len(db) else -90.0
    active = db > floor + 12
    segs, on = [], None
    for i, act in enumerate(active):
        if act and on is None:
            on = i
        elif not act and on is not None:
            if i - on >= 3:
                segs.append((on / 10, i / 10))
            on = None
    if on is not None:
        segs.append((on / 10, len(active) / 10))

    # ── timbre, sur la prise entière
    p_sum = None
    for _, mag in ja.frames(x, 2048, 512):     # hop of a quarter, as the first version (scipy stft)
        p_sum = mag ** 2 if p_sum is None else p_sum + mag ** 2
    f = np.arange(len(p_sum)) * sr / 2048
    tot = float(p_sum.sum()) + 1e-12
    centroid = float((f * p_sum).sum() / tot)
    bands = [(0, 250), (250, 1000), (1000, 4000), (4000, 8000), (8000, sr / 2)]
    band_share = [(lo, hi, 100 * float(p_sum[(f >= lo) & (f < hi)].sum()) / tot) for lo, hi in bands]

    # ── classes de hauteur, basse et aigu à part
    bass, treble = ja.bass_treble(x, sr)
    pc = (bass / (bass.sum() or 1)) + (treble / (treble.sum() or 1))
    pc = pc / (pc.sum() or 1)

    # ── tempo et temps
    env, fps = ja.onset_envelope(x, sr)
    bpm, cands = ja.tempo(env, fps)
    beat_times = ja.beats(env, fps, bpm)
    local = ja.local_tempi(beat_times)
    keys = ja.key_profile(pc)

    if a.temps:
        with open(a.temps, "w", encoding="utf-8") as fh:
            json.dump({"source": a.fichier, "bpm": round(bpm, 2), "beats": [round(t, 4) for t in beat_times]}, fh)

    if a.json:
        print(json.dumps({
            "file": a.fichier, "duration_s": round(dur, 3), "sample_rate": sr,
            "peak": round(float(np.max(np.abs(x))) if len(x) else 0.0, 4),
            "rms": round(float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0, 5),
            "active_segments": [[s, e] for s, e in segs],
            "centroid_hz": round(centroid), "bands_percent": [[lo, hi, round(s, 2)] for lo, hi, s in band_share],
            "pitch_classes_percent": {ja.FR[k]: round(100 * float(pc[k]), 2) for k in range(12)},
            "key_profile": [[n, round(r, 3)] for r, n, *_ in keys[:4]],
            "tempo_bpm": round(bpm, 2), "tempo_candidates": [[round(b, 2), round(s, 3)] for b, s in cands],
            "beats": [round(t, 4) for t in beat_times],
            "local_tempo": [[s, e, round(b, 1)] for s, e, b in local],
        }, ensure_ascii=False, indent=1))
        return

    print(f"# {a.fichier}")
    print(f"durée      : {dur:.2f} s   lu à {sr} Hz, mono")
    print(f"pic        : {np.max(np.abs(x)):.4f}   RMS global : {np.sqrt(np.mean(x ** 2)):.5f}")
    print(f"\n# enveloppe (100 ms/case), plancher={floor:.1f} dB")
    print(f"segments actifs (>0,3 s) : {len(segs)}")
    for s, e in segs[:40]:
        print(f"   {s:6.1f} → {e:6.1f} s   ({e - s:.1f} s)")
    sym = ''.join('#' if act else '.' for act in active)
    print("\n# carte temporelle, 1 caractère = 100 ms")
    for i in range(0, len(sym), 100):
        print(f"  {i / 10:6.1f}s |{sym[i:i + 100]}|")
    print(f"\n# timbre\ncentroïde spectral : {centroid:.0f} Hz")
    for lo, hi, s in band_share:
        print(f"   {lo:5.0f}–{hi:5.0f} Hz : {s:5.2f} %")
    print("\n# profil de classes de hauteur (basse E1–E3 et aigu C3–C7, à parts égales)")
    for k in np.argsort(-pc):
        print(f"   {ja.FR[k]:4s} {100 * pc[k]:5.2f} %  {'█' * int(pc[k] * 200)}")
    print("   tonalité qu'il suggère (Krumhansl) : "
          + " · ".join(f"{n} {r:+.3f}" for r, n, *_ in keys[:3])
          + "   — jamai-chords-audio.py la tranche avec les accords")
    print("\n# tempo (autocorrélation du flux spectral, a priori autour de 120 BPM)")
    print(f"   retenu : {bpm:.1f} BPM")
    for b, s in cands:
        print(f"     {b:6.1f} BPM   force {s:.3f}")
    print("   Un pic à la moitié ou au double est la même musique comptée autrement : c'est")
    print("   la carrure qui décide, pas l'outil.")
    print(f"\n# temps détectés : {len(beat_times)}"
          + (f"   (premier {beat_times[0]:.2f} s, dernier {beat_times[-1]:.2f} s)" if beat_times else ""))
    if local:
        print("   tempo local par 10 s : " + " · ".join(f"{s:.0f}s {b:.0f}" for s, e, b in local))
    print("   " + ' '.join(f"{t:.2f}" for t in beat_times[:48]) + (" …" if len(beat_times) > 48 else ""))
    if a.temps:
        print(f"\n  → {a.temps}")


if __name__ == "__main__":
    main()
