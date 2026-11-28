#!/usr/bin/env python3
"""jamai-melodie.py — les notes d'une ligne chantée ou jouée, en MIDI, prêtes pour jamai-grille.py.

  jamai-melodie.py <voix.wav> [--methode basic-pitch|pyin] [--mid ligne.mid] [--json notes.json]
                   [--fmin 80] [--fmax 1000] [--une-voix]

    --methode basic-pitch  défaut : des NOTES (attaque, fin, hauteur), par le réseau de Spotify
              pyin         une courbe de hauteur (librosa), découpée en notes ici : pour vérifier
    --mid <fichier>        écrit la ligne en MIDI. Ensuite : jamai-grille.py ligne.mid --abc …
    --json <fichier>       écrit les notes
    --une-voix             une note à la fois : à chaque chevauchement, la plus forte reste.
                           C'est ce que jamai-grille.py attend, au prix d'attaques perdues
                           (0,55 au lieu de 0,70 sur la ligne seule)
    --fmin, --fmax         la tessiture cherchée, en Hz (défaut 80–1000 : voix et guitare)

Donne-lui une piste SÉPARÉE (jamai-separe.py). Mesuré le 2026-11-27 sur une ligne de « Monde
immonde » rendue en voix « oohs », dont chaque note est connue (144 notes) :

  méthode            attaques justes (F1, 50 ms)   hauteur juste   calcul (CPU, 133 s d'audio)
  basic-pitch              0,70                        0,99             2 s
  pyin (librosa)           0,64                        0,90            39 s
  CREPE tiny / full        0,38 / 0,43                 0,96 / 0,95     16 s / 459 s
  la même ligne sous une guitare : 0,12 basic-pitch, 0,18 pyin, 0,04 CREPE — d'où la séparation ;
  la même, séparée par jamai-separe.py puis basic-pitch : 0,44. Demucs apprend sur des voix
  réelles : sur une voix « oohs » de synthèse, ce chiffre est plutôt un plancher.

La hauteur est presque toujours juste ; c'est l'ATTAQUE qui fait le rythme d'une partition, et
c'est là que pyin, qu'on avait utilisé pour « Monde immonde », perdait le plus. CREPE n'est pas
retenu : il ne donne qu'une courbe, comme pyin, et il est le plus lent.

Demande basic-pitch (et librosa pour pyin) : `jamai listen-setup` les installe.
"""
import argparse
import json
import os
import sys
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
import jamai_extras  # noqa: E402

NOMS = ['do', 'do#', 'ré', 'ré#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si']


def nom(m):
    m = int(round(m))
    return f"{NOMS[m % 12]}{m // 12 - 1}"


def par_basic_pitch(path, fmin, fmax):
    jamai_extras.require(["basic_pitch", "onnxruntime"], "jamai-melodie.py --methode basic-pitch")
    import logging
    logging.disable(logging.WARNING)          # basic-pitch warns about every backend it lacks
    import pathlib
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict
    model = pathlib.Path(ICASSP_2022_MODEL_PATH).parent / "nmp.onnx"
    _, _, events = predict(path, str(model), onset_threshold=0.5, frame_threshold=0.3,
                           minimum_note_length=80, minimum_frequency=fmin, maximum_frequency=fmax,
                           melodia_trick=True)
    return [{"s": float(e[0]), "e": float(e[1]), "midi": int(e[2]), "force": round(float(e[3]), 3)}
            for e in sorted(events, key=lambda e: e[0])]


def par_pyin(path, fmin, fmax):
    jamai_extras.require(["librosa"], "jamai-melodie.py --methode pyin")
    import numpy as np
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = 256
    f0, voiced, prob = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr, frame_length=2048, hop_length=hop)
    t = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop)
    midi = librosa.hz_to_midi(f0)
    notes, cur = [], None
    for ti, m, v, p in zip(t, midi, voiced, prob):
        # a note goes on while the voice is voiced and stays within 0.6 semitone of its last frames
        if v and np.isfinite(m) and cur and abs(m - float(np.median(cur["m"][-5:]))) < 0.6:
            cur["m"].append(m); cur["p"].append(p); cur["e"] = ti
        else:
            if cur and cur["e"] - cur["s"] >= 0.08:
                notes.append(cur)
            cur = {"s": ti, "e": ti, "m": [m], "p": [p]} if (v and np.isfinite(m)) else None
    if cur and cur["e"] - cur["s"] >= 0.08:
        notes.append(cur)
    return [{"s": float(n["s"]), "e": float(n["e"]) + hop / sr, "midi": int(round(float(np.median(n["m"])))),
             "force": round(float(np.mean(n["p"])), 3)} for n in notes]


def une_voix(notes):
    keep = []
    for n in sorted(notes, key=lambda n: -n["force"]):
        if not any(k["s"] < n["e"] and n["s"] < k["e"] for k in keep):
            keep.append(n)
    return sorted(keep, key=lambda n: n["s"])


def polyphonie(notes):
    """Share of the sounding time where two notes or more sound at once."""
    ev = sorted([(n["s"], 1) for n in notes] + [(n["e"], -1) for n in notes])
    on, last, poly, total = 0, None, 0.0, 0.0
    for t, d in ev:
        if last is not None and on > 0:
            total += t - last
            if on > 1:
                poly += t - last
        on += d
        last = t
    return poly / total if total else 0.0


def ecrire_mid(notes, path):
    jamai_extras.require(["pretty_midi"], "jamai-melodie.py --mid")
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(initial_tempo=120)
    inst = pretty_midi.Instrument(program=53, name="ligne")
    for n in notes:
        inst.notes.append(pretty_midi.Note(velocity=int(40 + 80 * min(1.0, n["force"])), pitch=n["midi"],
                                           start=n["s"], end=max(n["e"], n["s"] + 0.05)))
    pm.instruments.append(inst)
    pm.write(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fichier")
    ap.add_argument("--methode", default="basic-pitch", choices=["basic-pitch", "pyin"])
    ap.add_argument("--mid")
    ap.add_argument("--json")
    ap.add_argument("--fmin", type=float, default=80.0)
    ap.add_argument("--fmax", type=float, default=1000.0)
    ap.add_argument("--une-voix", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.fichier):
        sys.exit("  ✗ introuvable : %s" % a.fichier)
    warnings.filterwarnings("ignore")
    notes = (par_basic_pitch if a.methode == "basic-pitch" else par_pyin)(a.fichier, a.fmin, a.fmax)
    if a.une_voix:
        notes = une_voix(notes)
    poly = polyphonie(notes)

    print(f"# {a.fichier} · {a.methode}{' · une voix' if a.une_voix else ''} · {len(notes)} notes")
    if notes:
        lo, hi = min(n["midi"] for n in notes), max(n["midi"] for n in notes)
        print(f"   tessiture {nom(lo)} – {nom(hi)} · {100 * poly:.0f} % du temps à plusieurs notes")
    if poly > 0.25:
        print("   ⚠ plusieurs notes à la fois plus d'un quart du temps : un accompagnement ou une")
        print("     deuxième voix est dans la piste. Sépare d'abord (jamai-separe.py), ou --une-voix.")
    print("\n    début     durée   note    midi   force")
    for n in notes[:400]:
        print(f"  {n['s']:7.2f}s  {n['e'] - n['s']:6.2f}s   {nom(n['midi']):6s} {n['midi']:4d}   {n['force']:.2f}")
    if len(notes) > 400:
        print(f"  … {len(notes) - 400} notes de plus dans --json")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"file": a.fichier, "method": a.methode, "one_voice": a.une_voix,
                       "polyphony": round(poly, 3), "notes": notes}, fh, ensure_ascii=False, indent=1)
        print(f"\n  → {a.json}")
    if a.mid:
        ecrire_mid(notes, a.mid)
        print(f"  → {a.mid}   (la grille, avant d'écrire : jamai-grille.py {a.mid} --abc ligne.abc)")


if __name__ == "__main__":
    main()
