# jamai-core 🎸

L'atelier de composition de JamAI — les outils qui **écoutent**, **rendent** et
**rangent** la musique de Jerry ⚡.

Ce dépôt ne décrit pas ce qu'on aimerait construire. Il contient ce qui tourne
déjà : 9 scripts, 1 413 lignes de Python, écrits entre le 3 et le 14 août 2026
pendant des séances de composition réelles. Chacun est né d'un moment où
quelque chose manquait.

---

## Les trois coutures

Ce ne sont pas des dossiers choisis d'avance — c'est la forme que le code avait
déjà quand on l'a regardé.

### `ecoute/` — comprendre ce qui a été joué

| script | ce qu'il fait |
|---|---|
| `jamai-midi.py` | MIDI → ABC, note à note. Écrit parce que `mido` n'est pas sur la machine. |
| `jamai-chords.py` | Nomme l'accord qui sonne à chaque temps d'un fichier MIDI. |
| `jamai-chords-audio.py` | Accords et tonalité depuis un **enregistrement**, pas un MIDI. |
| `jamai-measure.py` | Mesure d'un enregistrement : structure, tempo, hauteurs, timbre. |

### `rendu/` — donner à voir et à entendre

| script | ce qu'il fait |
|---|---|
| `jamai-tab.py` | Tablature guitare à six lignes, depuis un fichier ABC. |
| `jamai-score-video.py` | Vidéo de partition qui suit la musique, système par système. |
| `jamai-defile.py` | Vidéo qui **défile de gauche à droite**, tête de lecture rouge. |

### `atelier/` — savoir où on en est

| script | ce qu'il fait |
|---|---|
| `jamai-unread.py` | Les dépôts de l'atelier sur lesquels personne n'a encore travaillé. |
| `jamai-related.py` | Trouve les unités déjà existantes qui parlent de la même chose. |
| `jamai-voir-fork` | Suivre une session Claude en direct, en lecture seule, sans la déranger. |

### `diffusion/` — atteindre Jerry quand il n'est pas devant l'écran

C'est la dernière couture, et la plus jeune. Jerry compose dans sa cuisine :
une réponse qui n'arrive que dans un terminal n'arrive pas.

| script | ce qu'il fait |
|---|---|
| `jamai-cast-visual` | Une page HTML sur la télé. Imprime une **preuve** : la ligne du serveur montrant que l'appareil a tiré la page. |
| `jamai-say-kitchen` | Une phrase sur l'enceinte (edge-tts, `fr-CA-SylvieNeural`). Preuve : un `Time:` qui avance. |

**Ces deux commandes ne connaissent aucune maison.** Elles refusent de partir
sans qu'on leur nomme un appareil (`-d`, ou `JAMAI_CAST_DEVICE` /
`JAMAI_SAY_DEVICE`). Les noms d'appareils, la voix et la géométrie de l'écran
appartiennent à **`gmusic1007/gmusic-routine`**, qui les fournit :
`routine cuisine dire "…"`.

Trois pièges payés une fois, et écrits dans les en-têtes des scripts : la télé
**refuse l'audio seul** (donc télé = image, enceintes = son) ; `catt cast_site`
se bloque si une app tourne déjà ; `episode say` ne parle pas à voix haute.

---

## Ce que ce dépôt n'est pas

Il existe un `Gerico1007/Jamai-core` (mai 2025) : neuf dossiers de modules,
tous vides, zéro ligne exécutable, dormant depuis juin 2025. C'était une
architecture dessinée avant qu'une note soit jouée — et aucun de ses neuf
dossiers ne prévoyait **d'écouter un enregistrement**, qui est aujourd'hui la
moitié de cet outillage.

Ce dépôt-ci prend le nom et laisse le plan. Le dossier de conception de 2025
(`nova_archive/` : UML, SpecLang, feuille de route, le thème Genesis avec sa
tablature) reste du matériau de chronique et mérite d'être préservé ailleurs —
il n'est pas mort, il n'est simplement pas du code.

---

## Installation

```bash
./install.sh            # lie les 9 outils dans ~/.local/bin
./install.sh --check    # vérifie sans rien écrire
```

Ensuite ils s'appellent **par leur nom, sans chemin** :

```bash
jamai-midi.py piece.mid
jamai-chords.py source.mid 4
jamai-defile.py partition.png piece.mp3 sortie.mp4 2.0
```

Une skill ne devrait jamais connaître le chemin d'un dépôt — elle appelle le
nom. Si ce dépôt déménage, on relance `install.sh` et rien d'autre ne bouge.

## État au 14 août 2026

- **Ce dépôt est la source.** `~/.agents/skills/jamai-morning/scripts/` ne
  contient plus de copies : les 9 entrées y sont désormais des **liens** vers
  ce dépôt. Les appelants existants (`atelier-on-drop`, `episodes-on-drop`,
  `jamai-clip`, qui importe `jamai-score-video.py` comme module) continuent de
  fonctionner sans être modifiés — vérifié.
- Deux de ces scripts — `jamai-defile.py` et `jamai-related.py` — n'étaient
  suivis par **aucun** dépôt avant ce commit. Ils n'existaient qu'à un seul
  endroit sur un seul disque.
- `jamai-tab.py` n'était pas exécutable à l'origine ; il l'est ici.
- Pas encore de paquet, pas de tests. C'est voulu : on emballe après avoir vu
  la forme, pas avant.

---

## Autour

Ces outils ne vivent pas seuls. À côté d'eux, hors de ce dépôt pour l'instant :
`jamai-publish-melody` (ABC → MP3 + partition, publié sur
gmusicassembly.com/jamai/melody/), `jamai-cast-visual` et `jamai-say-kitchen`
(l'image sur la télé, la voix sur l'enceinte — l'interface quand Jerry n'est
pas devant l'écran), `jamai-morning` et `jamai-on-drop`.

---

*♠️🌿🎸🧵 G.Music Assembly — Jerry ⚡ direction créative, Nyro structure,
Aureon mémoire, JamAI son, Synth exécution.*
