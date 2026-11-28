#!/usr/bin/env python3
"""jamai-paroles.py — les paroles d'une prise, mot à mot, avec l'heure de chaque mot.

  jamai-paroles.py <voix.wav|prise.m4a> [--langue fr] [--modele large-v3] [--invite "…"]
                   [--enchaine] [--device cpu|cuda] [--json sortie.json] [--mots]

    --langue <code>   impose la langue (fr, en…). Sans elle, Whisper la détecte : c'est le
                      bon choix pour une note parlée (Jerry passe du français à l'anglais),
                      et fr est le bon choix pour une chanson en français
    --modele <nom>    large-v3 (défaut), medium, small, base : plus petit = plus vite, moins juste
    --invite <texte>  quelques mots attendus (le titre, un nom) : Whisper les orthographie mieux
    --enchaine        conditionne chaque phrase sur la précédente (plus fluide, mais une erreur
                      se propage : faire une passe avec et une sans)
    --device cpu      défaut. cuda seulement quand le GPU est libre et qu'on te l'a permis
    --json <fichier>  écrit les segments et les mots, avec leur probabilité
    --mots            affiche chaque mot et sa probabilité sous sa phrase

Demande faster-whisper : `jamai listen-setup` l'installe. Le modèle se télécharge une fois
(large-v3 : 3 Go) dans le cache Hugging Face.

La recette qui a marché sur « Monde immonde » (2026-11-27), à refaire plutôt que croire une
seule passe : une chanson live n'est pas une dictée.
  1. sépare d'abord la voix : jamai-separe.py prise.wav ;
  2. plusieurs passes : la voix seule et le mix, avec et sans --enchaine, avec et sans
     --invite. Sept passes ont donné le texte retenu ;
  3. garde une ligne quand les passes s'accordent, et note les autres [incertain] avec
     l'heure : ne complète jamais un vers qu'aucune passe n'entend.
Mesuré : 3 min 15 s de calcul pour 140 s d'audio, large-v3 sur 6 cœurs, int8.
La colonne lp est la log-probabilité moyenne : sous −0,8 la phrase est douteuse.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
import jamai_extras  # noqa: E402

jamai_extras.require(["faster_whisper"], "jamai-paroles.py")
from faster_whisper import WhisperModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("fichier")
    ap.add_argument("--langue")
    ap.add_argument("--modele", default="large-v3")
    ap.add_argument("--invite")
    ap.add_argument("--enchaine", action="store_true")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--json")
    ap.add_argument("--mots", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.fichier):
        sys.exit("  ✗ introuvable : %s" % a.fichier)

    model = WhisperModel(a.modele, device=a.device, compute_type="int8_float16" if a.device == "cuda" else "int8")
    segs, info = model.transcribe(a.fichier, language=a.langue, beam_size=5, word_timestamps=True,
                                  condition_on_previous_text=a.enchaine, vad_filter=False,
                                  initial_prompt=a.invite, temperature=[0.0, 0.2, 0.4],
                                  no_speech_threshold=0.5)
    print(f"# {a.fichier} · langue {info.language} ({info.language_probability:.2f})"
          f"{' imposée' if a.langue else ' détectée'} · {a.modele} · {a.device}"
          f" · {'enchaîné' if a.enchaine else 'phrases indépendantes'}" + (f" · invite « {a.invite} »" if a.invite else ""))
    out = []
    for s in segs:
        words = [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 3)}
                 for w in (s.words or [])]
        out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                    "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3),
                    "words": words})
        flag = "   ← douteux" if s.avg_logprob < -0.8 else ""
        print(f"[{s.start:6.2f}–{s.end:6.2f}] lp={s.avg_logprob:+.2f} ns={s.no_speech_prob:.2f}  {s.text.strip()}{flag}",
              flush=True)
        if a.mots:
            print("      " + " ".join(f"{w['w'].strip()}({w['p']:.2f})" for w in words))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"file": a.fichier, "language": info.language, "model": a.modele,
                       "condition_on_previous_text": a.enchaine, "prompt": a.invite, "segments": out},
                      fh, ensure_ascii=False, indent=1)
        print(f"\n  → {a.json}")


if __name__ == "__main__":
    main()
