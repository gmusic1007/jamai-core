#!/usr/bin/env python3
"""Trouver les unités déjà existantes qui parlent de la même chose qu'un dépôt.

Corpus : les dossiers `~/compositions-<atelier>`. Une unité = un dossier
(son `composition.json` + les `transcription_*.txt` qui l'accompagnent).

Index : BM25 reconstruit à chaque appel. Le corpus entier fait ~270 Ko —
le construire coûte quelques millisecondes, donc rien n'est persisté et
rien ne peut devenir périmé.

Coût : zéro token de modèle. Aucun réseau. Que du disque et du CPU.

Un lien n'est proposé que s'il est justifiable : le score seul ne suffit pas,
il faut aussi un nombre minimum de termes discriminants partagés, et chaque
terme retenu est imprimé avec son poids. Une sortie sans preuve est un bug.

  jamai-related.py <fichier-requête> [--top N] [--json] [--min-terms N]
  jamai-related.py - < texte
"""
import sys, os, json, math, re, unicodedata, glob, time, argparse

HOME = os.path.expanduser("~")

# Mots vides FR + EN. Avec 12 documents, l'IDF seul ne suffit pas à les
# éteindre : un mot présent partout garde un poids résiduel qui bruite le
# classement. On les retire à la source.
STOP = set("""
alors au aucun aussi autre avec avoir bien car ce cela ces cet cette ceux chaque
chez comme comment dans de des du dedans dehors depuis deux donc dont elle elles
en encore est et eux fait faire fois font hors ici il ils je juste la le les leur
là ma mais me meme même mes mien moins mon mot ni nommes nos notre nous on ont ou
où par parce pas peu peut plupart pour pourquoi quand que quel quelle quelles
quels qui sa sans se ses seulement si sien son sont sous soyez sujet sur ta tandis
tellement tels tes ton tous tout trop très tu un une vos votre vous ça étaient
état étions été être avait avais avons étais sera serait faut fait faites vais
vas allez peux pouvez doit dois devez ai as
quelque quelques chose choses truc trucs vraiment beaucoup plutot plutôt ainsi
deja déjà autant partout ailleurs peuvent pouvait etait était etaient sois
a an an and are as at be been but by can did do does for from get had has have here
his how i if in into is it its just like make me more my no not of on one only or
other our out over said same see she should so some such than that the their them
then there these they this those to too two up use very was way we were what when
which who will with would you your
"""
.split())

TOKEN = re.compile(r"[a-zà-öø-ÿ0-9][a-zà-öø-ÿ0-9_-]{2,}", re.IGNORECASE)

# 34,7 % du corpus mesuré le 2026-08-05 est du code : chemins, commandes,
# blocs collés dans les notes. Ce vocabulaire est identique dans toutes les
# unités — il fait donc gagner `head`, `usr`, `git` et ne prouve aucun sujet
# commun. Jerry parle en prose ; on compare de la prose à de la prose.
CODEISH = re.compile(r"""
      ^\s*(?:\#!|\$|>|\||```|https?:|/|~/|[-+*]\s|\[|\]|\{|\})
    | ^\s*[A-Za-z_./~-]+\s*=
    | \b(?:git|bash|sudo|curl|chmod|mkdir|python3|npm|sed|awk|grep|find|echo|cat|ls|ssh|rm|mv|cp)\s
    | ^\s*[a-z_]+\(
    | ^\s*(?:import|from|def|class|return|except|try|else|elif|with|print|const|let|var|function|for|while|if)\b.*[:(]
""", re.VERBOSE)


DATEISH = re.compile(r"[0-9][0-9a-z_-]*|[0-9a-f]{7,40}")

# Un identifiant d'unité — ep-NNN, op-NNN, jr-NNN — est un lien DÉCLARÉ, traité
# comme tel en amont. Le laisser dans le vocabulaire le ferait compter deux fois
# et le ferait passer pour une preuve de sujet, ce qu'il n'est pas.
IDENT = re.compile(r"(?:ep|op|jr)-\d{3}.*")


def strip_code(text):
    keep = []
    for line in text.splitlines():
        if CODEISH.search(line) or line.count("/") >= 2 or line.count("|") >= 2:
            continue
        keep.append(line)
    return "\n".join(keep)


def tokenise(text, prose_only=True):
    if prose_only:
        text = strip_code(text)
    text = unicodedata.normalize("NFC", text.lower())
    # Une date partagée ne prouve rien : deux unités du même jour parlent du
    # même jour, pas du même sujet.
    return [t for t in TOKEN.findall(text)
            if t not in STOP and not DATEISH.fullmatch(t)
            and not IDENT.fullmatch(t)]


def bigrams(tokens):
    """Un mot partagé est une coïncidence ; deux mots à la suite sont un sujet."""
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def unit_text(folder):
    """Tout le texte d'une unité : le manifeste et ses transcriptions."""
    parts = []
    manifest = os.path.join(folder, "composition.json")
    if os.path.isfile(manifest):
        try:
            m = json.load(open(manifest, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            m = {}
        for key in ("title", "slug", "notes", "rhythm", "key"):
            v = m.get(key)
            if isinstance(v, str):
                parts.append(v)
        # `texts` et `clips` portent des libellés écrits à la main : ce sont
        # souvent les mots les plus proches de ce que Jerry dit à l'oral.
        for entry in m.get("texts", []) or []:
            if isinstance(entry, dict):
                parts += [str(entry.get(k, "")) for k in ("title", "body", "text")]
            elif isinstance(entry, str):
                parts.append(entry)
        for clip in m.get("clips", []) or []:
            if isinstance(clip, dict):
                parts.append(str(clip.get("label", "")))
    for t in sorted(glob.glob(os.path.join(folder, "transcription_*.txt"))):
        try:
            parts.append(open(t, encoding="utf-8", errors="replace").read())
        except OSError:
            pass
    return "\n".join(parts)


def build_corpus(roots):
    units = []
    for root in roots:
        atelier = os.path.basename(root).replace("compositions-", "")
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            folder = os.path.join(root, name)
            if not os.path.isdir(folder) or name.startswith("."):
                continue
            text = unit_text(folder)
            toks = tokenise(text)
            if not toks:
                continue
            units.append({
                "atelier": atelier, "slug": name, "folder": folder,
                "tokens": toks, "bigrams": set(bigrams(toks)),
                "bytes": len(text.encode()), "raw": len(text.encode()),
            })
    return units


def shared_phrases(units, qtokens, floor=0.9):
    """Bigrammes partagés, pondérés par leur rareté dans le corpus."""
    N = len(units)
    bdf = {}
    for u in units:
        for g in u["bigrams"]:
            bdf[g] = bdf.get(g, 0) + 1
    qb = set(bigrams(qtokens))
    per_unit = {}
    for u in units:
        hits = []
        for g in qb & u["bigrams"]:
            n = bdf[g]
            idf = math.log((N - n + 0.5) / (n + 0.5) + 1.0)
            if idf >= floor:
                hits.append((g, idf, n))
        hits.sort(key=lambda x: -x[1])
        per_unit[u["slug"]] = hits
    return per_unit


def bm25(units, query_tokens, k1=1.5, b=0.75):
    """BM25 classique. Renvoie (score, contributions par terme) par unité."""
    N = len(units)
    if N == 0:
        return []
    avgdl = sum(len(u["tokens"]) for u in units) / N
    df = {}
    freqs = []
    for u in units:
        f = {}
        for t in u["tokens"]:
            f[t] = f.get(t, 0) + 1
        freqs.append(f)
        for t in f:
            df[t] = df.get(t, 0) + 1

    qset = {}
    for t in query_tokens:
        qset[t] = qset.get(t, 0) + 1

    out = []
    for u, f in zip(units, freqs):
        dl = len(u["tokens"])
        score, terms = 0.0, []
        for t in qset:
            if t not in f:
                continue
            n = df[t]
            # IDF BM25 ; peut devenir négatif pour un terme présent presque
            # partout — on le plancherise plutôt que de le laisser soustraire.
            idf = max(0.01, math.log((N - n + 0.5) / (n + 0.5) + 1.0))
            tf = f[t]
            contrib = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
            score += contrib
            terms.append((t, contrib, idf, tf, n))
        terms.sort(key=lambda x: -x[1])
        out.append((score, terms, u))
    out.sort(key=lambda x: -x[0])
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("query", help="fichier de la requête, ou - pour stdin")
    ap.add_argument("--top", type=int, default=5)
    # Seuil mesuré sur les 31 transcriptions du corpus, chacune en requête à
    # l'aveugle (son unité exclue) le 2026-08-05 :
    #   2 → 52 liens, 6/31 muettes    3 → 36 liens, 12/31    4 → 28 liens, 14/31
    #   5 → 25 liens, 15/31           6 → 18 liens, 18/31
    # 4 tient 0,90 lien par dépôt et laisse près d'une requête sur deux muette.
    ap.add_argument("--min-phrases", type=int, default=4,
                    help="bigrammes rares partagés exigés — la preuve du lien")
    ap.add_argument("--min-idf", type=float, default=0.9,
                    help="au-dessous, un terme est trop répandu pour prouver un lien")
    ap.add_argument("--roots", nargs="*", default=sorted(glob.glob(os.path.join(HOME, "compositions-*"))))
    ap.add_argument("--exclude", default=None,
                    help="slug à retirer du corpus (par défaut : l'unité qui contient la requête)")
    ap.add_argument("--json", action="store_true", help="fragment links[] sur stdout")
    ap.add_argument("--write", metavar="DOSSIER", default=None,
                    help="fusionne le résultat dans le links[] du composition.json "
                         "de DOSSIER — lecture, fusion, réécriture entière")
    args = ap.parse_args()

    t0 = time.time()
    if args.query == "-":
        qtext, qfolder = sys.stdin.read(), None
    else:
        qtext = open(args.query, encoding="utf-8", errors="replace").read()
        qfolder = os.path.basename(os.path.dirname(os.path.abspath(args.query)))

    exclude = args.exclude if args.exclude is not None else qfolder
    units = [u for u in build_corpus(args.roots) if u["slug"] != exclude]
    t_index = time.time() - t0

    qtok = tokenise(qtext)
    ranked = bm25(units, qtok)
    t_all = time.time() - t0

    phrases = shared_phrases(units, qtok, args.min_idf)

    kept, dropped = [], []
    for score, terms, u in ranked[:args.top]:
        ph = phrases[u["slug"]]
        if len(ph) < args.min_phrases:
            dropped.append((score, u, ph))
            continue
        strong = [t for t in terms if t[2] >= args.min_idf]
        kept.append((score, ph, strong, u))

    entries = [{
        "slug": u["slug"], "atelier": u["atelier"], "relation": "related",
        "score": round(score, 2),
        "phrases": [g[0] for g in ph[:6]],
        "terms": [t[0] for t in strong[:6]],
        "by": "jamai-related", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    } for score, ph, strong, u in kept]

    if args.write:
        # Vérifié le 2026-08-05 dans web/pixel-recorder.js du dépôt gmtermux :
        #   PUT /api/compositions/:slug (l.885) relit le disque entier, ne
        #   recopie que 9 clés autorisées (l.889, `links` absente) et réécrit
        #   l'objet complet → un links[] posé sur disque SURVIT à un PUT, mais
        #   ne peut pas y être écrit (200 et rien d'écrit).
        #   POST /api/forest/compositions/:slug (l.732) fait
        #   `fs.writeFileSync(json, JSON.stringify(req.body))` sans fusion et
        #   sans authentification → il EFFACE tout ce que le client n'a pas
        #   envoyé. C'est la seule route qui détruit un links[].
        # D'où le choix : on écrit sur le disque, jamais par l'API.
        target = os.path.join(args.write, "composition.json")
        doc = json.load(open(target, encoding="utf-8"))
        existing = {(l.get("atelier"), l.get("slug")): l
                    for l in doc.get("links", []) if isinstance(l, dict)}
        for e in entries:
            existing[(e["atelier"], e["slug"])] = e
        doc["links"] = sorted(existing.values(), key=lambda l: -l.get("score", 0))
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
        print(f"{len(entries)} lien(s) fusionné(s) dans {target} "
              f"— links[] contient {len(doc['links'])} entrée(s)")
        return

    if args.json:
        print(json.dumps([{
            "slug": u["slug"], "atelier": u["atelier"], "relation": "related",
            "score": round(score, 2),
            "phrases": [g[0] for g in ph[:6]],
            "terms": [t[0] for t in strong[:6]],
            "by": "jamai-related", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        } for score, ph, strong, u in kept], ensure_ascii=False, indent=2))
        return

    print(f"# requête   : {args.query}   ({len(qtok)} mots de prose retenus)")
    print(f"# corpus    : {len(units)} unités, "
          f"{sum(u['bytes'] for u in units)} octets bruts, exclu={exclude}")
    print(f"# index     : {t_index*1000:.0f} ms   total {t_all*1000:.0f} ms   "
          f"0 token de modèle, 0 appel réseau")
    print(f"# retenu    : {len(kept)} / {len(ranked)} "
          f"(preuve exigée : >= {args.min_phrases} bigrammes d'idf >= {args.min_idf})")
    if not kept:
        print("\naucun lien justifiable — c'est une réponse, pas un échec.")
    for score, ph, strong, u in kept:
        print(f"\n  {u['atelier']}/{u['slug']}   score {score:.2f}")
        print(f"    ce qui est dit des deux côtés ({len(ph)} bigrammes) :")
        for g, idf, n in ph[:8]:
            print(f"      « {g} »".ljust(46) + f"idf {idf:4.2f}  dans {n} unité(s)")
        if strong:
            print("    mots isolés à l'appui : "
                  + ", ".join(t[0] for t in strong[:8]))
    # Ce qui a été écarté compte autant que ce qui est retenu.
    if dropped:
        print("\n# écartés malgré un score haut — score sans phrase commune :")
        for s, u, ph in dropped:
            print(f"    {u['atelier']}/{u['slug']:<44} score {s:6.2f}   "
                  f"{len(ph)} bigramme(s)")


if __name__ == "__main__":
    main()
