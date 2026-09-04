#!/usr/bin/env python3
"""scroll.py — vidéo de partition qui DÉFILE DE GAUCHE À DROITE.

Jerry lit mieux à l'horizontale. Une seule portée, seize mesures, et la fenêtre
glisse en suivant la musique.

Le défilement n'est PAS linéaire : abcm2ps espace les mesures selon leur
contenu, et ici elles vont de 298 à 608 pixels. Un panoramique linéaire
dériverait d'une mesure entière au milieu. On détecte donc les barres de mesure
dans l'image, et on construit un panoramique par MORCEAUX — une mesure de
musique = un segment de pixels, exactement.

  scroll.py <partition.png> <audio.mp3> <sortie.mp4> <sec_par_mesure> <nb_mesures> [partition.svg]

Le nombre de mesures est OBLIGATOIRE et sert de contrôle : si la détection ne
le retrouve pas, l'outil s'arrête au lieu de fabriquer une vidéo désynchronisée.
Payé le 2026-08-14 sur l'introduction de l'opus 013 : un premier détecteur
comptait les HAMPES des accords comme des barres et trouvait 16 mesures là où
il y en avait 8. La vidéo se fabriquait quand même, décalée du double.
"""
import subprocess, sys
import numpy as np
from PIL import Image

png, audio, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
# Le 4e argument accepte soit un nombre (toutes les mesures durent pareil),
# soit une liste « 8x3.636,37x2.4 » — une fusion change de tempo en son
# milieu, et une seule valeur mentirait sur une moitié de la partition.
def lire_durees(spec):
    if 'x' not in spec and ',' not in spec:
        return None, float(spec)
    out = []
    for bloc in spec.split(','):
        n, d = bloc.split('x'); out += [float(d)] * int(n)
    return out, out[0]
DUREES, SEC_PAR_MES = lire_durees(sys.argv[4] if len(sys.argv) > 4 else '2.4')
NB_ATTENDU  = int(sys.argv[5]) if len(sys.argv) > 5 else 0
FEN_L, CANVAS_H = 1280, 720

im = np.array(Image.open(png).convert('L'))
h, w = im.shape

# ── D'OÙ VIENNENT LES POSITIONS DE MESURE ──────────────────────────────────
# Deux chemins. Le SVG quand on l'a, les pixels sinon.
#
# Ajouté le 2026-09-03. La détection au pixel plus bas cherche le plus long
# trait vertical CONTIGU de chaque colonne. Sur une partition d'accords
# frappés, la hampe d'un accord de six notes est aussi haute qu'une barre :
# mesuré sur la guitare des couplets de l'opus 014, 31 mesures détectées
# pour 4. Le garde-fou a refusé de fabriquer la vidéo — le bon réflexe — mais
# il n'existait aucun recours ici, alors que jamai-clip.py en avait un depuis
# le 2026-08-14. Deux outils voisins, une seule corrigé. C'est réparé.
#
# abcm2ps écrit déjà les numéros de mesure dans le SVG avec leur abscisse
# exacte, à condition de mettre `%%measurenb 1` dans la source. On les lit :
# plus de seuil, plus de devinette, et ça marche quel que soit le nombre de
# portées ou la densité des accords.
SVG = sys.argv[6] if len(sys.argv) > 6 else None
if SVG:
    import re
    t = open(SVG).read()
    m = re.search(r'width="([\d.]+)px"\s+height="([\d.]+)', t)
    if not m: sys.exit(f"  ✗ pas de largeur lisible dans {SVG}")
    ech = w / float(m[1])                # le PNG est rendu à une autre échelle
    nums = sorted({int(n): float(x) for x, n in
                   re.findall(r'<text x="([\d.]+)" y="[\d.]+">(\d+)</text>', t)
                   if 1 < int(n) <= NB_ATTENDU}.items())
    if len(nums) != NB_ATTENDU - 1:
        sys.exit(f"  ✗ {len(nums)} numéros de mesure dans le SVG, {NB_ATTENDU-1} attendus. "
                 f"`%%measurenb 1` est-il dans la source ABC ?")
    xs = [v * ech for _, v in nums]      # début des mesures 2..N
    pas = xs[1] - xs[0]
    X = [xs[0] - pas] + xs + [xs[-1] + (xs[-1] - xs[-2])]
    NB = len(X) - 1
    print(f"  {w}x{h} px · {NB} mesures lues DANS LE SVG")
    if NB != NB_ATTENDU:
        sys.exit(f"  ✗ ARRÊT : {NB} mesures, {NB_ATTENDU} attendues.")
else:
    # ── détection des barres de mesure ─────────────────────────────────────────
    # On ne compte PAS les colonnes sombres : une hampe d'accord en fait autant
    # qu'une barre. On mesure le plus long segment vertical CONTIGU de chaque
    # colonne — une barre traverse la portée entière, une hampe non.
    dark = im < 128
    longest = np.zeros(w, dtype=int)
    for x in range(w):
        c = dark[:, x]
        if not c.any(): continue
        best = cur = 0
        for v in c:
            cur = cur + 1 if v else 0
            if cur > best: best = cur
        longest[x] = best
    cand = np.where(longest >= int(0.25*h))[0]
    groups, cur = [], [cand[0]]
    for x in cand[1:]:
        if x - cur[-1] <= 4: cur.append(x)
        else: groups.append(int(np.mean(cur))); cur = [x]
    groups.append(int(np.mean(cur)))

    # La BARRE FINALE est double : deux traits que le détecteur sépare (mesuré :
    # 14815 et 14829 sur l'intégrale). Deux colonnes à moins de 30 px l'une de
    # l'autre sont le même repère — on garde la dernière.
    # (J'ai d'abord cru que la colonne en trop était l'accolade à gauche, et je
    #  l'ai retirée : le compte devenait juste et la vidéo décalée d'une mesure.
    #  Le compte qui tombe juste n'est pas une preuve — seule l'image l'est.)
    fusion = [groups[0]]
    for x in groups[1:]:
        if x - fusion[-1] < 30: fusion[-1] = x
        else: fusion.append(x)
    groups = fusion
    X = groups
    NB = len(X) - 1
    print(f"  {w}x{h} px · {NB} mesures détectées · barres {X[0]} → {X[-1]}")
    if NB_ATTENDU and NB != NB_ATTENDU:
        sys.exit(f"  ✗ ARRÊT : {NB} mesures détectées, {NB_ATTENDU} attendues. "
                 f"Une vidéo fabriquée là-dessus serait désynchronisée.")

# ── panoramique par morceaux ───────────────────────────────────────────────
# x_tete(t) = position de la mesure en train de sonner.
# Puis la fenêtre est centrée dessus, bornée aux extrémités de l'image.
xmax = max(0, w - FEN_L)
durees = DUREES if DUREES else [SEC_PAR_MES]*NB
if len(durees) != NB:
    sys.exit(f"  ✗ {len(durees)} durées pour {NB} mesures")
bornes = [0.0]
for d in durees: bornes.append(bornes[-1] + d)

expr = f"{X[-1]}"                      # après la fin : on reste sur la dernière
for b in range(NB-1, -1, -1):
    t0, t1 = bornes[b], bornes[b+1]
    x0, x1 = X[b], X[b+1]
    seg = f"({x0}+({x1-x0})*(t-{t0:.3f})/{durees[b]:.3f})"
    expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"

# ── 2. LA TÊTE DE LECTURE SUIT LA MUSIQUE, MÊME QUAND L'IMAGE NE BOUGE PLUS
# Défaut signalé par Jerry le 2026-08-14 : « rendu à la dernière mesure, elle
# arrête ». Vrai — et aux DEUX bouts. La fenêtre est bornée à [0, w-1280],
# donc au début et à la fin elle ne bouge plus ; la tête, dessinée au centre
# fixe, restait plantée pendant que la musique continuait sous elle.
# Elle est maintenant dessinée à (position jouée − décalage de la fenêtre) :
# centrée tant que l'image défile, et libre de courir jusqu'au bout ensuite.
crop_x  = f"clip({expr}-{FEN_L//2},0,{xmax})"
tete_x  = f"({expr})-({crop_x})"

pad_y = max(0, (CANVAS_H - h)//2)

# LA TÊTE EST UN OVERLAY, PAS UN DRAWBOX. Mesuré le 2026-08-14 sur ce build :
# drawbox n'évalue PAS « t » dans son expression x — son paramètre d'épaisseur
# s'appelle aussi « t » et masque la variable de temps. Avec x='t*100' il ne
# dessine rien du tout ; avec x=100 il dessine. La tête restait donc plantée à
# une position constante, ce que Jerry a vu avant moi. overlay, lui, honore
# « t » exactement : vérifié à 51 / 201 / 401 px pour t = 0,5 / 2 / 4 s.
vf = (f"[0:v]crop={FEN_L}:{h}:x='{crop_x}':y=0,"
      f"pad={FEN_L}:{CANVAS_H}:0:{pad_y}:color=white[bg];"
      f"[bg][2:v]overlay=x='{tete_x}-1':y={pad_y}[v]")

cmd = ['ffmpeg','-v','error','-y',
       '-loop','1','-i',png,          # -loop 1 : sans lui, une image fixe sort en 0,04 s
       '-i',audio,
       '-f','lavfi','-i',f'color=red@0.75:s=3x{h},format=rgba',
       '-filter_complex',vf,'-map','[v]','-map','1:a',
       '-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-r','30',
       '-c:a','aac','-b:a','160k','-shortest',sortie]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    print(r.stderr[-1500:]); sys.exit(1)
d = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                    '-of','csv=p=0',sortie],capture_output=True,text=True).stdout.strip()
print(f"  → {sortie} · {d} s")
