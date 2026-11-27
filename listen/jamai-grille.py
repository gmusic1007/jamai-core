#!/usr/bin/env python3
"""jamai-grille.py — CHOISIR LA GRILLE AVANT D'ÉCRIRE LA PARTITION.

Sa règle, le 2026-09-07, après avoir refusé trois écritures de suite :
« la comparaison avec les bonnes grilles doit se faire AVANT d'écrire la
partition ».

Ce que ça donnait sans outil : sa prise du 7 septembre écrite en 4/4 sur une
grille de doubles-croches. Ses 43 notes s'étalaient sur SIX valeurs différentes
avec des liaisons partout. Ses mots : « si un musicien recevait cette
partition-là, est-ce qu'il se mettrait à rire de moi ? […] c'est comme s'il y a
beaucoup de silence […] dur à lire ». La même ligne en 6/8, croche = 0,379 s,
tient en TROIS valeurs et 40 notes sur 43 valent une simple croche — pour une
erreur de quantification IDENTIQUE (79 ms contre 81).

La grille ne se devine pas. Elle se mesure, et il y a rarement une seule
réponse : l'outil affiche le tableau et dit laquelle il retient, et pourquoi.

  jamai-grille.py <prise.m4a|.wav|.mid> [options]

    --tonalite <nom>   impose la tonalité au lieu de la proposer (« si♭ mineur »)
    --grille <nom>     impose la grille au lieu de la retenir (« 6/8 croche »)
    --levee <n>        impose la levée en unités de grille
    --bpm <n>          impose le pouls, mesuré par jamai-measure.py sur la prise entière
    --abc <fichier>    écrit la partition (sinon : analyse seulement)
    --titre <texte>    titre de la partition
    --json             sort tout en JSON

L'outil REFUSE d'écrire un ABC portant une valeur non notable. C'est voulu :
5/8 et 7/8 n'existent pas, abcm2ps les grave à trois points, et personne ne
lève d'erreur. Le compte qui tombe juste n'est pas une preuve — regarde l'image.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile, wave
from collections import Counter

NOMS = ['do', 'do#', 'ré', 'ré#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si']
FR2ABC = {'do': 'C', 'ré': 'D', 'mi': 'E', 'fa': 'F', 'sol': 'G', 'la': 'A', 'si': 'B'}

# ─────────────────────────────────────────────────────────── lecture de la prise

def charger(chemin):
    """Rend (échantillons mono, fréquence). Passe par ffmpeg : le .m4a de son
    téléphone n'est pas lisible autrement, et wave ne connaît que le PCM."""
    if chemin.lower().endswith(('.mid', '.midi')):
        return None, None
    tmp = tempfile.mktemp(suffix='.wav')
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', chemin,
                        '-map', '0:a:0', '-ac', '1', '-ar', '22050', tmp],
                       capture_output=True)
    if r.returncode or not os.path.exists(tmp):
        sys.exit(f"  ✗ pas de piste audio exploitable dans {chemin}")
    w = wave.open(tmp)
    import numpy as np
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768.0
    sr = w.getframerate()
    w.close(); os.unlink(tmp)
    return a, sr


def relever(a, sr, mini=0.12):
    """Les notes tenues, par FFT fine et produit harmonique.

    PIÈGE 11, payé sur l'opus 013 : sur une prise très grave le chromagramme
    ordinaire ne dit RIEN — douze classes entre 4,8 et 13,3 %. Une FFT de
    16 384 points (2,7 Hz de résolution) sur les fondamentales 70–700 Hz résout
    les hauteurs au cent près.

    Le produit harmonique existe parce qu'un pic sur l'harmonique 2 ou 3 est
    souvent plus fort que la fondamentale : sans lui, le relevé monte d'une
    octave sans prévenir. C'est le même défaut que l'avertissement fa#4/fa#3 de
    la cartouche id-0003.
    """
    import numpy as np
    N, HOP = 16384, 1024
    trace = []
    for st in range(0, max(1, len(a) - N), HOP):
        seg = a[st:st + N] * np.hanning(N)
        S = np.abs(np.fft.rfft(seg))
        f = np.fft.rfftfreq(N, 1 / sr)
        if S.max() < 1e-4:
            trace.append((st / sr, None, 0.0)); continue
        idx = np.where((f >= 70) & (f <= 700))[0]
        hps = S[idx].copy()
        for h in (2, 3):
            ih = idx * h
            ih = ih[ih < len(S)]
            hps[:len(ih)] *= S[ih]
        k = idx[int(np.argmax(hps))]
        trace.append((st / sr, 69 + 12 * math.log2(f[k] / 440), float(S[k])))

    amps = [x[2] for x in trace if x[1] is not None]
    seuil = float(np.percentile(amps, 45)) if amps else 0.0
    notes, cur = [], None
    for t, mi, amp in trace:
        ok = mi is not None and amp >= seuil
        if ok and cur and abs(mi - cur['m']) < 0.7:
            cur['m'] = (cur['m'] * cur['n'] + mi) / (cur['n'] + 1)
            cur['n'] += 1; cur['fin'] = t
        else:
            if cur and cur['fin'] - cur['deb'] >= mini:
                notes.append(cur)
            cur = {'deb': t, 'fin': t, 'm': mi, 'n': 1} if ok else None
    if cur and cur['fin'] - cur['deb'] >= mini:
        notes.append(cur)
    return [{'deb': x['deb'], 'duree': x['fin'] - x['deb'], 'midi': x['m']} for x in notes]


def relever_midi(chemin):
    """Un MIDI se lit note pour note — aucune raison de le deviner à l'oreille."""
    d = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run(['python3', os.path.join(d, 'jamai-midi.py'), chemin],
                         capture_output=True, text=True).stdout
    notes, tempo = [], 120.0
    for l in out.split('\n'):
        m = re.match(r'^\s*\[t=\d+\] tempo ([\d.]+) BPM', l)
        if m:
            tempo = float(m.group(1))
        p = l.split()
        if len(p) >= 7 and re.match(r'^\d+$', p[0]) and re.match(r'^[\d.]+$', p[1]):
            # colonnes : début(ticks) temps durée canal midi nom abc vel
            # PIÈGE 7 : la colonne « temps » est en NOIRES, pas en secondes.
            notes.append({'deb': float(p[1]) * 60.0 / tempo,
                          'duree': float(p[2]) * 60.0 / tempo,
                          'midi': float(p[4])})
    return notes


# ───────────────────────────────────────────────────────────── justesse et pouls

def justesse(notes):
    """L'écart au tempérament égal. Un demi-ton fait 100 cents ; une médiane
    au-dessus de 25 veut dire que le relevé se promène sur la grille des
    demi-tons, et que les noms de notes sont des approximations. Le dire est la
    moitié du travail : une dictée présentée comme sûre coûte plus cher qu'une
    dictée annoncée douteuse."""
    ec = sorted(abs((n['midi'] - round(n['midi'])) * 100) for n in notes)
    if not ec:
        return 0.0, 0
    med = ec[len(ec) // 2]
    return med, sum(1 for x in ec if x > 35)


def pouls(notes):
    """Les pouls CANDIDATS, pas un seul.

    L'intervalle d'attaque médian d'une prise chantée est presque toujours une
    SUBDIVISION du pouls, pas le pouls. Mesuré le 2026-09-07 sur comp-0001 :
    l'intervalle médian donne 0,557 s alors que l'autocorrélation du flux
    spectral donne 1,138 s — exactement le double. Un outil qui se fixe sur le
    premier ne testera jamais la grille qui gagne, et il le fera en silence.

    On rend donc l'intervalle médian ET ses multiples 2 et 3. Toutes les
    grilles sont ensuite comparées sur chacun ; c'est le tableau qui tranche,
    pas une hypothèse choisie d'avance.
    """
    ioi = [notes[i + 1]['deb'] - notes[i]['deb'] for i in range(len(notes) - 1)]
    dedans = sorted(x for x in ioi if 0.05 < x < 2.5)
    if not dedans:
        return None
    base = dedans[len(dedans) // 2]
    return [base, base * 2, base * 3]


def phrases(notes, souffle=1.6):
    """Découpe aux respirations. Une phrase, c'est ce qui tient entre deux
    souffles ; c'est l'unité que l'oreille entend et celle sur laquelle une
    levée se calcule."""
    out, cur = [], [notes[0]]
    for a, b in zip(notes, notes[1:]):
        if b['deb'] - (a['deb'] + a['duree']) > souffle:
            out.append(cur); cur = []
        cur.append(b)
    out.append(cur)
    return [p for p in out if p]


# ──────────────────────────────────────────────────────────────────── tonalité

MAJ = [0, 2, 4, 5, 7, 9, 11]
MIN_NAT = [0, 2, 3, 5, 7, 8, 10]
MIN_HARM = [0, 2, 3, 5, 7, 8, 11]


def tonalites(notes):
    """Les 36 gammes classées par couverture des notes TENUES.

    Compter les notes tenues, pas les images du chromagramme : une note longue
    et une note brève pèsent pareil dans l'oreille qui suit une mélodie.

    Deux gammes de même armure sortent à égalité — majeur et son relatif
    mineur. Ce qui les départage est la FRÉQUENCE DE LA TONIQUE, et c'est
    écrit dans le rapport pour que le choix soit relisible.
    """
    cnt = Counter(NOMS[int(round(n['midi'])) % 12] for n in notes)
    tot = sum(cnt.values()) or 1
    res = []
    for i, t in enumerate(NOMS):
        for lab, iv in (('majeur', MAJ), ('mineur', MIN_NAT), ('mineur harm.', MIN_HARM)):
            g = [NOMS[(i + x) % 12] for x in iv]
            res.append({'nom': f"{t} {lab}", 'tonique': t, 'degres': g,
                        'couverture': sum(cnt.get(n, 0) for n in g) / tot * 100,
                        'poids_tonique': cnt.get(t, 0)})
    res.sort(key=lambda r: (-r['couverture'], -r['poids_tonique']))
    return res, cnt


# ────────────────────────────────────────────────────────────────── les grilles

GRILLES = [
    # nom,              mesure, unités/mesure, unité = pouls / n, L: de l'ABC
    ("4/4 · double-croche", "4/4", 16, 4, "1/16"),
    ("4/4 · croche",        "4/4",  8, 2, "1/8"),
    ("6/8 · croche",        "6/8",  6, 3, "1/8"),
    ("12/8 · croche",      "12/8", 12, 3, "1/8"),
    ("3/4 · croche",        "3/4",  6, 2, "1/8"),
    ("2/4 · double-croche", "2/4",  8, 4, "1/16"),
]


def comparer(phr, pouls_candidats):
    """Le tableau que Jerry a demandé : chaque grille jugée sur trois axes.

    - erreur médiane : de combien chaque attaque doit bouger pour tomber sur la
      grille. Au-delà de ~100 ms la dérive s'entend.
    - silence interne : la part de la phrase qui n'est pas jouée. Les
      respirations ENTRE phrases n'y sont pas comptées — elles sont réelles et
      elles resteront ; c'est le vide À L'INTÉRIEUR qui rend illisible.
    - valeurs distinctes : combien de durées différentes le lecteur doit
      décoder. C'est le chiffre que son œil a vu avant moi. Six valeurs = une
      partition dont il a dit qu'un musicien rirait.
    """
    lignes = []
    for p in pouls_candidats:
      for nom, mes, par_mes, div, L in GRILLES:
        U = p / div
        if not (0.10 <= U <= 0.90):      # hors de ça, ni lisible ni jouable
            continue
        errs, sil, span, vals = [], 0, 0, []
        for ph in phr:
            t0 = ph[0]['deb']
            g = [(round((n['deb'] - t0) / U), max(1, round(n['duree'] / U))) for n in ph]
            errs += [abs((n['deb'] - t0) / U - round((n['deb'] - t0) / U)) * U * 1000 for n in ph]
            vals += [v for _, v in g]
            s = g[-1][0] + g[-1][1]
            occ = sum(min(g[k][1], (g[k + 1][0] - g[k][0]) if k + 1 < len(g) else g[k][1])
                      for k in range(len(g)))
            span += s; sil += s - occ
        errs.sort()
        lignes.append({'nom': f"{nom} · pouls {p:.2f}s", 'mesure': mes, 'par_mesure': par_mes, 'unite': U, 'L': L,
                       'err_ms': errs[len(errs) // 2] if errs else 0,
                       'silence': 100 * sil / span if span else 0,
                       'valeurs': len(set(vals)),
                       'part_unite': 100 * sum(1 for v in vals if v == 1) / len(vals)})
    # Le retenu : le moins de valeurs distinctes, à erreur acceptable. La
    # lisibilité est le critère que Jerry a nommé ; la précision est le
    # garde-fou qui l'empêche de tout écraser.
    ok = [l for l in lignes if l['err_ms'] <= 100] or lignes
    ok.sort(key=lambda l: (l['valeurs'], l['err_ms']))
    return lignes, ok[0]


def levee(phr, U, par_mes, forts):
    # forts = l'écart entre deux TEMPS, pas entre deux unités. En 4/4 écrit en
    # croches il y a 4 temps de 2 croches ; en 6/8 deux temps de 3. Le premier
    # essai comptait un temps toutes les 2 unités en 4/4, donc la moitié de la
    # grille était « forte » et le tableau des levées alternait sans rien dire.
    """« Il n'y aurait pas une manière de commencer sur le troisième ou
    quatrième temps ? » — sa question du 7 septembre. Elle se répond en
    comptant : pour chaque décalage possible, combien d'attaques tombent sur un
    temps fort. On rend le meilleur, et le compte de chacun pour qu'il puisse
    contredire."""
    scores = []
    for off in range(par_mes):
        n = 0
        for ph in phr:
            t0 = ph[0]['deb']
            for x in ph:
                pos = round((x['deb'] - t0) / U) + off
                if pos % forts == 0:
                    n += 1
        scores.append((n, off))
    total = sum(len(p) for p in phr)
    scores.sort(key=lambda s: (-s[0], s[1]))
    return scores[0][1], [{'levee': o, 'sur_temps': n, 'sur': total} for n, o in
                          sorted(scores, key=lambda s: s[1])]


# ────────────────────────────────────────────────────────────────── écrire l'ABC

# 5/8 et 7/8 N'EXISTENT PAS. abcm2ps les grave à trois points, sans une seule
# erreur affichée. Payé le 2026-09-04 sur l'opus 019, refusé à l'écoute.
VAL_NOTE_BINAIRE = (16, 12, 8, 6, 4, 3, 2, 1)
VAL_NOTE_TERNAIRE = (6, 3, 2, 1)
# Un silence ne se pointe pas et se pose sur un multiple de lui-même. C'est la
# règle qu'il a refusée en premier : « des pauses triple pointées, ça fait dur ».
VAL_SIL_BINAIRE = (16, 8, 4, 2, 1)
VAL_SIL_TERNAIRE = (6, 3, 2, 1)


def morceaux(p, L, note, ternaire):
    out = []
    while L > 0:
        if note:
            src = VAL_NOTE_TERNAIRE if ternaire else VAL_NOTE_BINAIRE
            k = next((c for c in src if c <= L and (not ternaire or c < 3 or p % 3 == 0)), None)
        else:
            src = VAL_SIL_TERNAIRE if ternaire else VAL_SIL_BINAIRE
            k = next((c for c in src if c <= L and (
                (ternaire and ((c == 6 and p % 6 == 0) or (c == 3 and p % 3 == 0)
                               or (c == 2 and p % 2 == 0) or c == 1))
                or (not ternaire and p % c == 0))), None)
        if k is None:
            raise ValueError(f"valeur impossible : {L} unités à la position {p}")
        out.append((p, k)); p += k; L -= k
    return out


def nom_abc(midi, degres):
    """Avec la bonne armure, chaque degré s'écrit LETTRE NUE. Une partition sans
    altération dans le corps se lit d'un coup d'œil ; la même en dièses partout
    est illisible même quand le MIDI est juste."""
    cls = NOMS[int(round(midi)) % 12]
    base = cls.rstrip('#')
    lettre = FR2ABC[base]
    alt = ''
    if cls not in degres:
        alt = '^' if cls.endswith('#') else '='
        lettre = FR2ABC[base]
    o = int(round(midi)) // 12 - 1
    if o < 4:
        return alt + lettre + ',' * (4 - o)
    if o == 4:
        return alt + lettre
    return alt + lettre.lower() + "'" * (o - 5)


def recaler(notes, degres):
    """Poser chaque note sur le degre le plus proche de la gamme retenue.

    Ce n'est PAS anodin et le compte doit etre dit : sur comp-0001, 7 notes
    sur 43 ont bouge et les 36 autres tombaient deja dedans — c'est ce
    chiffre qui a confirme la tonalite APRES l'avoir choisie. Si la moitie
    des notes doit bouger, c'est la tonalite qui est fausse, pas la prise.
    """
    cls = {NOMS.index(d) for d in degres}
    n2, bouge = [], 0
    for n in notes:
        m = int(round(n['midi']))
        if m % 12 not in cls:
            for k in (1, -1, 2, -2):
                if (m + k) % 12 in cls:
                    m += k
                    break
            bouge += 1
        n2.append(dict(n, midi=float(m)))
    return n2, bouge


def ecrire_abc(notes, grille, lev, degres, tonalite, titre, tempo_bpm):
    par_mes = grille['par_mesure']
    U = grille['unite']
    ternaire = grille['mesure'] in ('6/8', '12/8', '9/8')
    t0 = notes[0]['deb']
    ev = []
    for i, n in enumerate(notes):
        pos = round((n['deb'] - t0) / U) + lev
        lim = (round((notes[i + 1]['deb'] - t0) / U) + lev - pos) if i + 1 < len(notes) else None
        d = max(1, round(n['duree'] / U))
        ev.append((pos, n['midi'], max(1, min(d, lim)) if lim else d))
    total = ((ev[-1][0] + ev[-1][2]) // par_mes + 1) * par_mes

    plat, cur, eid = [], 0, 0
    for pos, m, d in ev:
        if pos > cur:
            plat.append((None, pos - cur, -1)); cur = pos
        plat.append((m, d, eid)); eid += 1; cur = pos + d
    if cur < total:
        plat.append((None, total - cur, -1))

    pieces, pos = [], 0
    for m, v, i in plat:
        reste = v
        while reste > 0:
            prend = min(reste, par_mes - (pos % par_mes))
            for pp, k in morceaux(pos % par_mes, prend, m is not None, ternaire):
                pieces.append({'mes': pos // par_mes, 'm': m, 'k': k, 'pp': pp, 'id': i})
            pos += prend; reste -= prend

    # La derniere mesure se compte sur les MORCEAUX reellement produits, pas
    # sur une prevision : une note finale plus longue que son intervalle pousse
    # au-dela du total prevu, et l'index sortait du tableau.
    #
    # ET ELLE SE COMPLETE. Sans ce rembourrage la derniere mesure sort courte :
    # abc2midi previent (« Track 2 is 44 quarter notes long not 43 ») mais
    # ecrit quand meme, et les voix d'accompagnement debordent d'un temps sur
    # une mesure que personne ne regarde. Mesure sur comp-0001 le 2026-09-07.
    fin = pieces[-1]['pp'] + pieces[-1]['k']
    if fin % par_mes:
        manque = par_mes - (fin % par_mes)
        for pp, k in morceaux(fin % par_mes, manque, False, ternaire):
            pieces.append({'mes': pieces[-1]['mes'], 'm': None, 'k': k,
                           'pp': pp, 'id': -1})
    barres = [[] for _ in range(max(pc['mes'] for pc in pieces) + 1)]
    for j, pc in enumerate(pieces):
        # UNE LIAISON NE JOINT QUE DES MORCEAUX DU MÊME ÉVÉNEMENT. Sans cette
        # règle, deux attaques voisines sur la même hauteur fondent en une seule
        # note : 43 deviennent 40, sans une erreur affichée.
        lie = pc['id'] >= 0 and j + 1 < len(pieces) and pieces[j + 1]['id'] == pc['id']
        tok = ('z' if pc['m'] is None else nom_abc(pc['m'], degres))
        tok += '' if pc['k'] == 1 else str(pc['k'])
        tok += '-' if lie else ''
        barres[pc['mes']].append((pc['pp'], tok))

    groupe = 3 if ternaire else (4 if grille['L'] == '1/16' else 2)
    mesures = []
    for b in barres:
        s = ''
        for k, (pp, tok) in enumerate(b):
            # Les ESPACES DE LA SOURCE décident de la ligature. Un espace par
            # temps : ses croches sont groupées par temps, sa préférence n° 1.
            if k > 0 and pp % groupe == 0:
                s += ' '
            s += tok
        mesures.append(s)

    med = sorted(n['midi'] for n in notes)[len(notes) // 2]
    cle = 'bass' if med < 60 else 'treble'
    # ARMURE PRATIQUE, pas theorique. « la# mineur » demande sept dieses et
    # ne s'ecrit jamais : c'est si bemol mineur, cinq bemols. Un lecteur a qui
    # on tend du la# mineur rit avant d'avoir lu la premiere note.
    BEMOLS = {'do#': 'Db', 'ré#': 'Eb', 'fa#': 'Gb', 'sol#': 'Ab', 'la#': 'Bb'}
    EXOTIQUE_MAJ = {'do#', 'ré#', 'sol#', 'la#'}
    EXOTIQUE_MIN = {'ré#', 'sol#', 'la#'}
    tonique = tonalite.split()[0]
    mineur = 'mineur' in tonalite
    if tonique in (EXOTIQUE_MIN if mineur else EXOTIQUE_MAJ):
        armure = BEMOLS[tonique]
    else:
        armure = FR2ABC[tonique.rstrip('#')] + ('#' if tonique.endswith('#') else '')
    armure += 'm' if mineur else ''

    L = ["% Partition écrite par jamai-grille.py — la grille a été MESURÉE avant",
         "% d'écrire, jamais devinée. Le tableau des grilles candidates est dans",
         "% la sortie de l'outil ; celle-ci a été retenue sur le nombre de valeurs",
         "% distinctes à erreur acceptable.",
         f"% grille retenue : {grille['nom']} · unité {U:.3f} s · erreur médiane"
         f" {grille['err_ms']:.0f} ms · {grille['valeurs']} valeurs distinctes",
         f"% levée : {lev} unités",
         f"% tonalité : {tonalite}",
         "X:1", f"T:{titre}", "C:Jerry ⚡ la prise · JamAI 🎸 le relevé",
         f"M:{grille['mesure']}", f"L:{grille['L']}",
         # PIÈGE 5 : abc2midi TRONQUE un tempo décimal sans avertir. 90.18 → 90.
         f"Q:{'3/8' if ternaire else '1/4'}={int(round(tempo_bpm))}",
         "%%measurenb 1", f"K:{armure}",
         f'V:1 name="Sa ligne" sname="Mél" clef={cle}',
         "%%MIDI gchordoff", "%%MIDI program 74",
         # FluidSynth réverbère par défaut et le publieur ne passe pas -R 0.
         "%%MIDI control 91 0", "%%MIDI control 93 0", "%"]
    for i, m in enumerate(mesures, 1):
        L.append(f"[V:1] {m}{' |]' if i == len(mesures) else ' |'}")
        # PIÈGE 1 : une LIGNE VIDE termine le morceau. MIDI valide, zéro note,
        # zéro avertissement. On sépare par un pour-cent, jamais par du vide.
        L.append("%")
    return '\n'.join(L) + '\n', len(mesures)


# ────────────────────────────────────────────────────────────────────── rapport

def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('prise')
    ap.add_argument('--tonalite'); ap.add_argument('--grille')
    ap.add_argument('--levee', type=int); ap.add_argument('--abc')
    ap.add_argument('--titre', default='sans titre'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--brut', action='store_true')
    ap.add_argument('--bpm', type=float)
    a = ap.parse_args()

    if a.prise.lower().endswith(('.mid', '.midi')):
        notes = relever_midi(a.prise); source = 'MIDI, lu note pour note'
    else:
        sig, sr = charger(a.prise)
        notes = relever(sig, sr); source = 'audio, relevé par FFT fine 16384'
    if len(notes) < 4:
        sys.exit(f"  ✗ seulement {len(notes)} notes tenues — rien à mesurer ici")

    med_c, hors = justesse(notes)
    # Le pouls d'une ligne chantée se devine mal sur ses seules attaques : sur « Monde immonde »
    # (2026-11-27) les candidats tirés de la voix étaient 0,21 · 0,42 · 0,63 s, et aucun n'était
    # le temps de la guitare (0,464 s, 129 BPM, que jamai-measure.py mesure sur la prise).
    # --bpm l'impose : la grille se compare alors sur le vrai temps.
    p = [60.0 / a.bpm] if a.bpm else pouls(notes)
    if not p:
        sys.exit("  ✗ pouls introuvable : les attaques sont trop espacées")
    phr = phrases(notes)
    gammes, cnt = tonalites(notes)
    lignes, retenue = comparer(phr, p)
    p_ret = float(re.search(r'pouls ([\d.]+)s', retenue['nom']).group(1))
    if a.grille:
        retenue = next((l for l in lignes if a.grille in l['nom']), retenue)
    # un temps = par_mesure / nombre de temps de la mesure
    TEMPS = {'4/4': 4, '2/4': 2, '3/4': 3, '6/8': 2, '12/8': 4, '9/8': 3}
    forts = max(1, retenue['par_mesure'] // TEMPS.get(retenue['mesure'], 4))
    lev, tab_lev = levee(phr, retenue['unite'], retenue['par_mesure'], forts)
    if a.levee is not None:
        lev = a.levee
    ton = a.tonalite or gammes[0]['nom']
    degres = next((g['degres'] for g in gammes if g['nom'] == ton), gammes[0]['degres'])

    if a.json:
        print(json.dumps({'notes': len(notes), 'justesse_cents': med_c, 'hors_35c': hors,
                          'pouls_candidats': p, 'pouls_retenu': p_ret, 'phrases': [len(x) for x in phr],
                          'gammes': gammes[:6], 'grilles': lignes, 'retenue': retenue,
                          'levee': lev, 'levees': tab_lev, 'tonalite': ton},
                         ensure_ascii=False, indent=1))
    else:
        print(f"# {a.prise} — {len(notes)} notes tenues ({source})")
        print(f"\n## justesse")
        print(f"  écart médian au tempérament égal : {med_c:.0f} cents"
              f"   ({hors}/{len(notes)} au-delà de 35)")
        if med_c > 25:
            print("  ⚠ au-delà de 25 cents les noms de notes sont des APPROXIMATIONS,")
            print("    pas une dictée. Dis-le à qui lit la partition.")
        print(f"\n## pouls\n  " + (f"imposé : {p[0]:.3f} s ({a.bpm:.1f} BPM)" if a.bpm else
              f"intervalle d'attaque médian {p[0]:.3f} s ; candidats testés : "
              + " · ".join(f"{x:.3f}s ({60/x:.0f} BPM)" for x in p)))
        print(f"  {len(phr)} phrases : " + " · ".join(str(len(x)) for x in phr) + " notes")
        print(f"\n## tonalité — l'outil PROPOSE, il ne tranche pas")
        for g in gammes[:4]:
            print(f"  {g['nom']:22s} {g['couverture']:5.1f} %   tonique entendue {g['poids_tonique']} fois")
        print(f"  → retenue : {ton}"
              + ("  (imposée)" if a.tonalite else "  (proposée — ton oreille peut la contredire)"))
        print(f"\n## les grilles, AVANT d'écrire")
        print(f"  {'grille':22s} {'unité':>7} {'err.méd':>8} {'sil.int':>8} {'valeurs':>8} {'sur 1 unité':>12}")
        for l in lignes:
            m = ' ←' if l is retenue else ''
            print(f"  {l['nom']:22s} {l['unite']:6.3f}s {l['err_ms']:7.0f}ms"
                  f" {l['silence']:7.1f}% {l['valeurs']:8d} {l['part_unite']:11.0f}%{m}")
        print(f"\n## levée — « commencer sur le troisième ou quatrième temps ? »")
        for t in tab_lev:
            print(f"  levée {t['levee']} : {t['sur_temps']}/{t['sur']} attaques sur un temps fort"
                  + ("  ←" if t['levee'] == lev else ""))

    if a.abc:
        try:
            jouees, bouge = (notes, 0) if a.brut else recaler(notes, degres)
            if bouge:
                alerte = '   ⚠ au-dela du quart : doute de la tonalite' if bouge > len(notes) // 4 else ''
                print('\n  recalage sur %s : %d/%d notes deplacees%s'
                      % (ton, bouge, len(notes), alerte))
            texte, n = ecrire_abc(jouees, retenue, lev, degres, ton, a.titre, 60 / p_ret)
        except ValueError as e:
            sys.exit(f"\n  ✗ REFUS D'ÉCRIRE : {e}\n"
                     "    Une valeur non notable serait gravée à trois points sans\n"
                     "    qu'aucune erreur ne s'affiche. Change de grille.")
        open(a.abc, 'w').write(texte)
        print(f"\n  → {a.abc} · {n} mesures")
        print("    Regarde l'image avant de livrer : abcm2ps -g -O s.svg puis rsvg-convert.")


if __name__ == '__main__':
    main()
