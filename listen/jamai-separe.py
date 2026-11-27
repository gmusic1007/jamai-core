#!/usr/bin/env python3
"""jamai-separe.py — la voix à part de l'accompagnement, avec Demucs.

  jamai-separe.py <prise.wav|.m4a|.mp4> [--sortie dossier] [--modele htdemucs_ft]
                  [--device cpu|cuda] [--quatre]

    --sortie <dossier>  où écrire (défaut : <prise>-pistes/ à côté de la prise)
    --modele <nom>      htdemucs_ft (défaut, le plus fin pour la voix), htdemucs (4 fois plus vite)
    --device cpu        défaut. cuda seulement quand le GPU est libre et qu'on te l'a permis
    --quatre            quatre pistes (voix, batterie, basse, autre) au lieu de deux

Écrit voix.wav et accompagnement.wav (ou les quatre pistes) et affiche leur chemin.

Pourquoi séparer d'abord, mesuré le 2026-11-27 :
  - mélodie : sur une ligne chantée seule, basic-pitch retrouve 70 % des attaques à 50 ms
    près ; la même ligne sous une guitare, 12 %. jamai-melodie.py veut la piste voix.wav ;
  - accords : sur « Monde immonde », jamai-chords-audio.py trouve 73 % des fondamentales sur
    accompagnement.wav contre 68 % sur le mix, et sa grille tombe sur 20 des 35 barres de
    référence contre 2 sur le mix ;
  - paroles : Whisper sur la voix seule et sur le mix ne se trompent pas aux mêmes endroits ;
    deux passes valent mieux qu'une.

Demande demucs et torch : `jamai listen-setup` les installe. Le modèle se télécharge une fois.
Mesuré sur CPU (8 cœurs) : 6 min 47 s pour les 140 s de « Monde immonde » avec htdemucs_ft ;
--modele htdemucs va plus vite.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
import jamai_extras  # noqa: E402

jamai_extras.require(["demucs", "torch"], "jamai-separe.py")
import demucs.separate  # noqa: E402

NOMS = {"vocals": "voix", "no_vocals": "accompagnement", "drums": "batterie", "bass": "basse", "other": "autre"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fichier")
    ap.add_argument("--sortie")
    ap.add_argument("--modele", default="htdemucs_ft")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--quatre", action="store_true")
    a = ap.parse_args()
    src = os.path.abspath(a.fichier)
    if not os.path.exists(src):
        sys.exit("  ✗ introuvable : %s" % src)
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.abspath(a.sortie or os.path.join(os.path.dirname(src), base + "-pistes"))
    os.makedirs(out, exist_ok=True)

    with tempfile.TemporaryDirectory() as work:
        # Demucs reads a WAV most reliably: anything else goes through ffmpeg first.
        wav = src
        if not src.lower().endswith(".wav"):
            wav = os.path.join(work, base + ".wav")
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-map", "0:a:0",
                                "-ar", "44100", "-c:a", "pcm_s16le", wav], capture_output=True)
            if r.returncode:
                sys.exit("  ✗ pas de piste audio lisible dans %s" % src)
        args = ["-n", a.modele, "-d", a.device, "-o", work, "--filename", "{stem}.{ext}"]
        if a.device == "cuda":
            args += ["--segment", "7"]      # a 4 GB card runs out of memory on longer segments
        if not a.quatre:
            args += ["--two-stems", "vocals"]
        print(f"# {src} · {a.modele} · {a.device} · {'quatre pistes' if a.quatre else 'voix / accompagnement'}",
              flush=True)
        demucs.separate.main(args + [wav])
        made = os.path.join(work, a.modele)
        written = []
        for f in sorted(os.listdir(made)):
            stem = os.path.splitext(f)[0]
            dest = os.path.join(out, NOMS.get(stem, stem) + ".wav")
            shutil.move(os.path.join(made, f), dest)
            written.append(dest)
    for w in written:
        print(f"  → {w}")


if __name__ == "__main__":
    main()
