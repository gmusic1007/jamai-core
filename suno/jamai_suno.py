#!/usr/bin/env python3
"""jamai-suno — turn a JamAI composition into a Suno generation through Suno's MCP server.

  jamai-suno prepare <composition-folder> [--abc FILE] [--key TEXT] [--seed melody|full|none]
  jamai-suno generate <composition-folder> [--variant instrumental|lyrics] [--tool NAME] [--plan]
  jamai-suno tools                      list the tools the authorized Suno server offers
  jamai-suno login [--port N] [--no-browser]
  jamai-suno status                     where the authorization stands, without changing it

prepare writes <composition>/suno/request.json, BRIEF.md and seed/<name>.mp3. It reads the
composition and its ABC file and sends nothing anywhere.

generate reads request.json and calls Suno's MCP server. Without an authorization it stops
with "authorization required" (exit 3). Every exchange is logged in <composition>/suno/log/.

Decisions taken when the bridge was built (2026-11-23):
  D1  The ABC file is --abc, else <folder>/<slug>.abc, else <root>/<slug>.abc, else stop with
      the candidates. Never a choice between versions.
  D2  Lyrics come only from ABC w: lines. composition.json texts[] goes to BRIEF.md as context
      for the person reading it, never into the Suno request.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import http.server
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from fractions import Fraction
from pathlib import Path

# Sunos edge rejects Python-urllibs default User-Agent with HTTP 403
# (found 2026-11-23 during the first login: curl got 200, urllib got 403).
# Present a browser User-Agent on every request this process makes.
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_opener = urllib.request.build_opener()
_opener.addheaders = [("User-Agent", _UA)]
urllib.request.install_opener(_opener)

VERSION = "0.1.0"
HERE = Path(__file__).resolve().parent
MCP_URL = os.environ.get("JAMAI_SUNO_MCP_URL", "https://api.suno.com/mcp")
CONFIG_DIR = Path(os.environ.get("JAMAI_SUNO_CONFIG_DIR", Path.home() / ".config" / "jamai-suno"))
TOKEN_FILE = CONFIG_DIR / "oauth.json"
TOOL_MAP_FILE = CONFIG_DIR / "suno-tools.map.json"   # per person: the package folder is not theirs to write
JAMAI_CORE = Path(os.environ.get("JAMAI_CORE_ROOT", HERE.parent))   # the package this module ships in
MUSESCORE_RENDER = JAMAI_CORE / "render" / "jamai-musescore"
PROTOCOL_VERSION = "2025-06-18"
STYLE_LIMIT = 1000   # characters; checked against the tool's own schema once it is known

EXIT_USAGE, EXIT_INPUT, EXIT_AUTH, EXIT_TOOL, EXIT_SERVER = 2, 2, 3, 4, 5


class Stop(Exception):
    def __init__(self, message: str, code: int = EXIT_INPUT):
        super().__init__(message)
        self.code = code


# ─── ABC reading ───────────────────────────────────────────────────────────

GM = (
    "acoustic grand piano|bright piano|electric grand|honky-tonk piano|electric piano|electric piano|"
    "harpsichord|clavinet|celesta|glockenspiel|music box|vibraphone|marimba|xylophone|tubular bells|"
    "dulcimer|drawbar organ|percussive organ|rock organ|church organ|reed organ|accordion|harmonica|"
    "tango accordion|nylon-string guitar|steel-string acoustic guitar|jazz guitar|clean electric guitar|"
    "muted electric guitar|overdriven guitar|distortion guitar|guitar harmonics|acoustic bass|"
    "fingered electric bass|picked electric bass|fretless bass|slap bass|slap bass|synth bass|synth bass|"
    "violin|viola|cello|contrabass|tremolo strings|pizzicato strings|harp|timpani|string ensemble|"
    "string ensemble|synth strings|synth strings|choir aahs|voice oohs|synth voice|orchestra hit|"
    "trumpet|trombone|tuba|muted trumpet|french horn|brass section|synth brass|synth brass|soprano sax|"
    "alto sax|tenor sax|baritone sax|oboe|english horn|bassoon|clarinet|piccolo|flute|recorder|pan flute|"
    "blown bottle|shakuhachi|whistle|ocarina|square lead|sawtooth lead|calliope lead|chiff lead|"
    "charang lead|voice lead|fifths lead|bass and lead|new age pad|warm pad|polysynth pad|choir pad|"
    "bowed pad|metallic pad|halo pad|sweep pad|rain fx|soundtrack fx|crystal fx|atmosphere fx|"
    "brightness fx|goblins fx|echoes fx|sci-fi fx|sitar|banjo|shamisen|koto|kalimba|bagpipe|fiddle|shanai|"
    "tinkle bell|agogo|steel drums|woodblock|taiko drum|melodic tom|synth drum|reverse cymbal|"
    "guitar fret noise|breath noise|seashore|bird tweet|telephone|helicopter|applause|gunshot"
).split("|")
assert len(GM) == 128

FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7, "G#": 8, "D#": 9, "A#": 10,
          "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7, "Fb": -8}
MODES = {"": ("major", 0), "maj": ("major", 0), "major": ("major", 0), "ion": ("Ionian", 0),
         "m": ("minor", -3), "min": ("minor", -3), "minor": ("minor", -3), "aeo": ("Aeolian", -3),
         "dor": ("Dorian", -2), "phr": ("Phrygian", -4), "lyd": ("Lydian", 1),
         "mix": ("Mixolydian", -1), "loc": ("Locrian", -5)}
SHARP_ORDER, FLAT_ORDER = "FCGDAEB", "BEADGCF"
STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
FRENCH = {"do": "C", "ré": "D", "re": "D", "mi": "E", "fa": "F", "sol": "G", "la": "A", "si": "B"}


def parse_key(text: str) -> dict | None:
    """'G', 'Em', 'Dmix', 'F major', 'E Phrygian', 'Sol majeur', 'A# major' → tonic, mode, signature."""
    t = (text or "").strip()
    if not t or t.lower().startswith("none"):
        return None
    t = re.sub(r"\b(clef|transpose|middle|stafflines)=\S+", "", t).strip()
    m = re.match(r"(?i)^(do|ré|re|mi|fa|sol|la|si)\s*(dièse|diese|bémol|bemol)?\s*(majeur|mineur)?", t)
    if m:
        tonic = FRENCH[m.group(1).lower()]
        acc = (m.group(2) or "").lower()
        tonic += "#" if acc.startswith("di") else ("b" if acc.startswith("b") else "")
        mode_word = "minor" if (m.group(3) or "").lower() == "mineur" else ""
    else:
        m = re.match(r"^([A-Ga-g])([#b]?)\s*([A-Za-z]*)", t)
        if not m:
            return None
        tonic = m.group(1).upper() + m.group(2)
        mode_word = m.group(3).lower()
    mode_key = mode_word[:3] if mode_word not in ("m", "") else mode_word
    if mode_word in ("major", "minor"):
        mode_key = mode_word
    if mode_key not in MODES or tonic not in FIFTHS:
        return None
    mode_name, offset = MODES[mode_key]
    fifths = FIFTHS[tonic] + offset
    sig = {}
    if fifths > 0:
        sig = {n: 1 for n in SHARP_ORDER[:min(fifths, 7)]}
    elif fifths < 0:
        sig = {n: -1 for n in FLAT_ORDER[:min(-fifths, 7)]}
    return {"tonic": tonic, "mode": mode_name, "signature": sig, "label": f"{tonic} {mode_name}"}


NOTE_RE = re.compile(r"(\^\^|\^|__|_|=)?([A-Ga-g])([',]*)(\d*/*\d*)")
BAR_RE = re.compile(r"\[\||\|\]|\|\||:\|\||\|:|:\||::|\|")


def strip_music(line: str) -> str:
    line = line.split("%", 1)[0]
    line = re.sub(r'"[^"]*"', " ", line)          # chord symbols and annotations
    line = re.sub(r"![^!]*!|\+[^+\s]*\+", " ", line)  # decorations
    line = re.sub(r"\{[^}]*\}", " ", line)         # grace notes
    line = re.sub(r"\[[A-Za-z]:[^\]]*\]", " ", line)  # inline fields
    return line


def gchords(line: str) -> list[str]:
    out = []
    for g in re.findall(r'"([^"]*)"', line.split("%", 1)[0]):
        if g and g[0] in "^_<>@":
            continue
        if re.match(r"^[A-G][#b]?", g):
            out.append(g)
    return out


class Voice:
    def __init__(self, vid: str):
        self.id, self.name, self.clef, self.program = vid, "", "", None
        self.channel10 = False
        self.directives: list[str] = []
        self.body: list[str] = []
        self.lyrics: list[tuple[int, str]] = []   # (bar index where the lyric line starts, text)
        self.bars = 0
        self.chords: list[str] = []

    @property
    def instrument(self) -> str:
        if self.channel10 or self.clef == "perc":
            return "drums"
        if self.program is not None and 0 <= self.program < 128:
            return GM[self.program]
        return ""


def count_bars(music: str) -> int:
    return len(BAR_RE.findall(strip_music(music)))


def read_abc(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    header: list[str] = []
    fields: dict[str, str] = {}
    voices: dict[str, Voice] = {}
    order: list[str] = []
    current: str | None = None
    in_header = True

    def voice(vid: str) -> Voice:
        if vid not in voices:
            voices[vid] = Voice(vid)
            order.append(vid)
        return voices[vid]

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("%%"):
            if current is None:
                if in_header:
                    header.append(line)
                continue
            v = voices[current]
            v.directives.append(line)
            pm = re.match(r"%%MIDI\s+program\s+(?:\d+\s+)?(\d+)", line)
            if pm and v.program is None:
                v.program = int(pm.group(1))
            if re.match(r"%%MIDI\s+channel\s+10\b", line):
                v.channel10 = True
            continue
        if line.startswith("%"):
            continue
        fm = re.match(r"^([A-Za-z]):(.*)$", line)
        if fm and not line.startswith("[") and fm.group(1) not in "|":
            f, val = fm.group(1), fm.group(2).strip()
            if f == "V":
                vid = val.split()[0]
                v = voice(vid)
                nm = re.search(r'(?:^|\s)name="([^"]*)"', val)
                if nm:
                    v.name = nm.group(1)
                cm = re.search(r"clef=(\S+)", val)
                if cm:
                    v.clef = cm.group(1)
                current = vid
                in_header = False
                continue
            if f == "w":
                if current is None:
                    current = voice("1").id
                v = voices[current]
                start = v._line_start if hasattr(v, "_line_start") else v.bars
                v.lyrics.append((start, val))
                continue
            if f in "XTCMLQKRZONSPGHIBDF" and (in_header or f in "XTC"):
                fields.setdefault(f, val)
                header.append(line)
                if f == "K":
                    in_header = False
                continue
            continue  # other field lines in the body (W:, etc.) carry no notes
        # A music line, possibly switching voice inline.
        im = re.match(r"^\[V:\s*([^\]\s]+)[^\]]*\]\s*(.*)$", line)
        if im:
            current = voice(im.group(1)).id
            music = im.group(2)
        else:
            if current is None:
                current = voice("1").id
            music = line
        in_header = False
        v = voices[current]
        v._line_start = v.bars
        v.body.append(music)
        v.bars += count_bars(music)
        v.chords.extend(gchords(music))
    return {"path": path, "text": text, "fields": fields, "header": header,
            "voices": [voices[i] for i in order]}


def melody_pitches(v: Voice, key: dict | None) -> list[tuple[int, int]]:
    """(MIDI pitch, bar index) for each note of a voice; the top note of a chord."""
    sig = (key or {}).get("signature", {})
    out: list[tuple[int, int]] = []
    bar = 0
    for music in v.body:
        s = strip_music(music)
        local: dict[tuple[str, int], int] = {}
        i = 0
        chord: list[int] | None = None
        while i < len(s):
            bm = BAR_RE.match(s, i)
            if bm:
                bar += 1
                local = {}
                i = bm.end()
                continue
            c = s[i]
            if c == "[":
                chord = []
                i += 1
                continue
            if c == "]":
                if chord:
                    out.append((max(chord), bar))
                chord = None
                i += 1
                continue
            nm = NOTE_RE.match(s, i)
            if nm:
                acc, letter, octs = nm.group(1), nm.group(2), nm.group(3)
                base = 60 + STEP[letter.upper()] + (12 if letter.islower() else 0)
                base += 12 * octs.count("'") - 12 * octs.count(",")
                slot = (letter.upper(), base // 12)
                if acc:
                    shift = {"^": 1, "^^": 2, "_": -1, "__": -2, "=": 0}[acc]
                    local[slot] = shift
                shift = local.get(slot, sig.get(letter.upper(), 0))
                p = base + shift
                if chord is not None:
                    chord.append(p)
                else:
                    out.append((p, bar))
                i = nm.end()
                continue
            i += 1
    return out


def pitch_name(p: int) -> str:
    return f"{NOTE_NAMES[p % 12]}{p // 12 - 1}"


def describe_melody(pitches: list[tuple[int, int]]) -> dict:
    if len(pitches) < 2:
        return {"notes": len(pitches)}
    ps = [p for p, _ in pitches]
    lo, hi = min(ps), max(ps)
    ivs = [abs(b - a) for a, b in zip(ps, ps[1:]) if b != a]
    steps = sum(1 for d in ivs if d <= 2)
    skips = sum(1 for d in ivs if 3 <= d <= 4)
    leaps = sum(1 for d in ivs if d >= 5)
    n = max(len(ivs), 1)
    biggest = max((steps, "mostly stepwise"), (skips, "mostly skips of a third"), (leaps, "mostly wide leaps"))
    motion = biggest[1] if biggest[0] / n >= 0.5 else "a mix of steps, thirds and leaps"
    peak_i = ps.index(hi)
    where = peak_i / (len(ps) - 1)
    q = max(len(ps) // 4, 1)
    first, last = sum(ps[:q]) / q, sum(ps[-q:]) / q
    if where < 0.25:
        shape = "falls away from an early peak"
    elif where > 0.75:
        shape = "climbs to its peak near the end"
    else:
        shape = "arches, peaking mid-way"
    drift = "ends higher than it starts" if last - first > 2 else (
        "ends lower than it starts" if first - last > 2 else "ends near where it starts")
    return {"notes": len(ps), "low": pitch_name(lo), "high": pitch_name(hi), "range_semitones": hi - lo,
            "motion": motion, "steps_pct": round(100 * steps / n), "skips_pct": round(100 * skips / n),
            "leaps_pct": round(100 * leaps / n),
            "shape": shape, "drift": drift, "peak_bar": pitches[peak_i][1] + 1,
            "first_note": pitch_name(ps[0]), "last_note": pitch_name(ps[-1])}


def w_line_to_text(w: str) -> str:
    w = w.replace("\\-", "\x00")
    w = re.sub(r"\s*\|\s*", " ", w)
    w = w.replace("*", " ").replace("_", " ")
    w = re.sub(r"\s*-\s*", "", w)       # syllables of one word
    w = w.replace("~", " ").replace("\x00", "-")
    return re.sub(r"\s+", " ", w).strip()


def lyrics_text(v: Voice) -> str:
    """One lyric line per w: line, a blank line where the voice is silent for a full bar or more."""
    lines: list[str] = []
    prev_end = None
    for start, raw in v.lyrics:
        txt = w_line_to_text(raw)
        if not txt:
            continue
        if prev_end is not None and start - prev_end >= 1 and lines and lines[-1] != "":
            lines.append("")
        lines.append(txt)
        prev_end = start + 1
    return "\n".join(lines).strip()


def tempo(fields: dict) -> tuple[float | None, Fraction | None]:
    q = fields.get("Q", "")
    m = re.search(r"(?:(\d+)/(\d+)\s*=\s*)?(\d+(?:\.\d+)?)", q)
    if not m:
        return None, None
    unit = Fraction(int(m.group(1)), int(m.group(2))) if m.group(1) else Fraction(1, 4)
    return float(m.group(3)), unit


def meter(fields: dict) -> tuple[int, int] | None:
    """The written time signature, unreduced: (4, 4) stays 4/4."""
    m = fields.get("M", "").strip()
    if m in ("C", "C|"):
        return (4, 4) if m == "C" else (2, 2)
    mm = re.match(r"(\d+)/(\d+)", m)
    return (int(mm.group(1)), int(mm.group(2))) if mm else None


def tempo_word(bpm: float) -> str:
    return ("slow" if bpm < 70 else "unhurried mid-tempo" if bpm < 95 else
            "mid-tempo" if bpm < 115 else "upbeat" if bpm < 135 else "fast")


# ─── prepare ───────────────────────────────────────────────────────────────

def select_abc(folder: Path, slug: str, explicit: str | None) -> tuple[Path, str]:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p)
        if not p.is_file():
            raise Stop(f"--abc {explicit}: no such file")
        return p.resolve(), "--abc"
    own = folder / f"{slug}.abc"
    if own.is_file():
        return own, "folder/<slug>.abc"
    root = folder.parent / f"{slug}.abc"
    if root.is_file():
        return root, "root/<slug>.abc"
    cands = sorted({*folder.glob("*.abc"), *folder.parent.glob(f"{slug}*.abc")})
    lines = "\n".join(f"  {c}" for c in cands) or "  (none)"
    raise Stop(f"no {slug}.abc in {folder} or {folder.parent}. Choose one with --abc. Candidates:\n{lines}")


def pick_melody_voice(voices: list[Voice]) -> tuple[Voice, str]:
    pitched = [v for v in voices if v.instrument != "drums" and v.body]
    sung = [v for v in pitched if v.lyrics]
    if sung:
        return sung[0], "the voice that carries w: lyrics"
    named = [v for v in pitched if re.search(r"(?i)m[ée]lodi|melody|voix|voice|lead|chant", v.name)]
    if named:
        return named[0], f'the voice named "{named[0].name}"'
    return pitched[0], "the first pitched voice"


HOUSE_STYLE = ("{instruments}; {tempo_word}, {bpm} BPM in {meter}; {tonality}; "
               "the lead line {shape}, {motion}, {low} to {high}. "
               "JamAI house sound: intimate room recording, warm and unquantized, "
               "few instruments with space between them; {lead}.")
LEAD_INSTRUMENTAL = "keep the composed melody recognisable as the lead line and let the arrangement grow around it"
LEAD_VOCAL = "a lead vocal sings the written words on the composed melody, the arrangement grows around the voice"


def ensure_rendered_seed(abc: dict, mel: Voice, outdir: Path, name: str, mode: str) -> dict | None:
    if mode == "none":
        return None
    seed_dir = outdir / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    if mode == "melody":
        lines = [h for h in abc["header"] if not h.startswith("%%score")]
        k = [h for h in lines if h.startswith("K:")]
        lines = [h for h in lines if not h.startswith("K:")] + k
        vdef = f'V:{mel.id} name="{mel.name}"' + (f" clef={mel.clef}" if mel.clef else "")
        lines.append(vdef)
        lines.extend(mel.directives)
        lines.extend(mel.body)
        src = seed_dir / f"{name}-melody.abc"
        src.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        src = seed_dir / f"{name}-full.abc"
        shutil.copyfile(abc["path"], src)
    if not MUSESCORE_RENDER.is_file():
        raise Stop(f"render path missing: {MUSESCORE_RENDER}")
    cmd = [str(MUSESCORE_RENDER), "--export", "mp3", "--out", str(seed_dir), str(src)]
    # MuseScore 4.7's converter still opens an X connection. With no display, give it a virtual one.
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a"] + cmd
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    (seed_dir / "render.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    mp3 = seed_dir / f"{src.stem}.mp3"
    if proc.returncode != 0 or not mp3.is_file():
        raise Stop(f"seed render failed (exit {proc.returncode}); see {seed_dir / 'render.log'}", EXIT_SERVER)
    dur = None
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "default=nw=1:nk=1", str(mp3)], capture_output=True, text=True).stdout)
    except (ValueError, FileNotFoundError):
        pass
    return {"path": str(mp3), "source_abc": str(src), "content": mode,
            "renderer": " ".join(cmd[:cmd.index(str(MUSESCORE_RENDER)) + 3]),
            "duration_s": round(dur, 1) if dur else None,
            "sha256": hashlib.sha256(mp3.read_bytes()).hexdigest()}


def cmd_prepare(a) -> int:
    folder = Path(a.folder).expanduser().resolve()
    cj = folder / "composition.json"
    if not cj.is_file():
        raise Stop(f"{cj}: not found")
    comp = json.loads(cj.read_text(encoding="utf-8"))
    slug = comp.get("slug") or folder.name
    abc_path, rule = select_abc(folder, slug, a.abc)
    abc = read_abc(abc_path)
    f = abc["fields"]
    warnings: list[str] = []

    voices = abc["voices"]
    if not voices:
        raise Stop(f"{abc_path}: no notes found")
    mel, mel_rule = pick_melody_voice(voices)

    k_header = parse_key(f.get("K", ""))
    k_comp = parse_key(comp.get("key") or "")
    if a.key:
        key, key_src = parse_key(a.key) or {"label": a.key, "signature": {}}, "--key"
        key = dict(key, label=a.key)
    elif k_header:
        key, key_src = k_header, "ABC K: header"
    elif k_comp:
        key, key_src = k_comp, "composition.json key"
    else:
        key, key_src = None, "none"
    first_chords = [c for v in voices for c in v.chords]
    if key_src != "--key":
        if key is None:
            warnings.append("No key is stated (K:none, composition.json key empty). The style prompt "
                            "leaves the tonality open. Pass --key to name one.")
        else:
            roots = {re.match(r"[A-G][#b]?", c).group(0) for c in (first_chords[:1] + first_chords[-1:])}
            if first_chords and key["tonic"] not in roots and key.get("mode") in ("major", "minor"):
                warnings.append(f"K: says {key['label']} but the first chord is {first_chords[0]} and the last "
                                f"is {first_chords[-1]}. The key may be modal or centred elsewhere: check it, "
                                "and pass --key if it is.")
        if k_header and k_comp and (k_header["tonic"], k_header["mode"]) != (k_comp["tonic"], k_comp["mode"]):
            warnings.append(f"composition.json key ({comp.get('key')}) and the ABC K: ({f.get('K')}) disagree. "
                            f"Used: {key_src}.")

    bpm, unit = tempo(f)
    if bpm is None and comp.get("bpm"):
        bpm, unit = float(comp["bpm"]), Fraction(1, 4)
        warnings.append("No Q: in the ABC; tempo taken from composition.json bpm.")
    met = meter(f)
    bars = max((v.bars for v in voices), default=0)
    seconds = None
    if bpm and unit and met:
        seconds = round(float(Fraction(*met) / unit) * 60.0 / bpm * bars, 1)

    pitches = melody_pitches(mel, k_header)   # notes are read with the signature written in K:
    shape = describe_melody(pitches)
    instruments = []
    for v in voices:
        ins = v.instrument
        if ins and ins not in instruments:
            instruments.append(ins)
    lyr = lyrics_text(mel) if mel.lyrics else ""

    langs = [t.get("lang") for t in comp.get("texts") or [] if isinstance(t, dict)]
    langs = [x for x in langs if x and x not in ("abc", "md")]
    lang = max(set(langs), key=langs.count) if langs else None

    title = comp.get("title") or slug
    title_src = "composition.json title"
    if title == slug and f.get("T"):
        title, title_src = f["T"], "ABC T: (composition.json title is the slug)"

    if key is None:
        tonality = "tonality left open, no fixed key"
    else:
        tonality = f"in {key['label']}"
    met_txt = f"{met[0]}/{met[1]}" if met else "free meter"
    style = HOUSE_STYLE.format(
        instruments=", ".join(i for i in instruments if i) or "small acoustic ensemble",
        tempo_word=tempo_word(bpm) if bpm else "free-tempo", bpm=int(round(bpm)) if bpm else "?",
        meter=met_txt, tonality=tonality, shape=shape.get("shape", ""),
        motion=shape.get("motion", ""), low=shape.get("low", "?"), high=shape.get("high", "?"),
        lead="{lead}")
    style = style[0].upper() + style[1:]
    style_template, style = style, style.replace("{lead}", LEAD_INSTRUMENTAL)
    if len(style) > STYLE_LIMIT:
        warnings.append(f"Style prompt is {len(style)} characters (limit used: {STYLE_LIMIT}).")

    outdir = folder / "suno"
    outdir.mkdir(exist_ok=True)
    seed = ensure_rendered_seed(abc, mel, outdir, abc_path.stem, a.seed)

    request = {
        "schema": "jamai-suno/request@1",
        "prepared": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "bridge_version": VERSION,
        "composition": {"folder": str(folder), "slug": slug, "abc": str(abc_path), "abc_rule": rule,
                        "composition_key": comp.get("key") or None, "composition_bpm": comp.get("bpm")},
        "music": {
            "key": key["label"] if key else None, "key_source": key_src,
            "meter": met_txt, "tempo_bpm": bpm, "tempo_unit": str(unit) if unit else None,
            "bars": bars, "duration_s_at_tempo": seconds,
            "voices": [{"id": v.id, "name": v.name, "instrument": v.instrument, "bars": v.bars,
                        "lyric_lines": len(v.lyrics)} for v in voices],
            "melody_voice": {"id": mel.id, "name": mel.name, "rule": mel_rule},
            "melody": shape,
            "chords": comp.get("chords") or list(dict.fromkeys(first_chords)),
        },
        "suno": {"title": title, "title_source": title_src, "style": style, "instrumental": True},
        "variants": {},
        "seed_audio": seed,
        "warnings": warnings,
    }
    if lyr:
        vocal_style = style_template.replace("{lead}", LEAD_VOCAL)
        if lang:
            vocal_style += f" Sung in {'French' if lang == 'fr' else lang}."
        request["variants"]["lyrics"] = {"title": title, "style": vocal_style, "instrumental": False,
                                         "lyrics": lyr, "lyrics_source": f"ABC w: lines of voice {mel.id}",
                                         "language": lang, "language_source": "majority of texts[].lang"}
    (outdir / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    (outdir / "BRIEF.md").write_text(brief(request, comp), encoding="utf-8")
    print(f"abc\t{abc_path}\t({rule})")
    print(f"melody\tvoice {mel.id} {mel.name!r}: {shape.get('low')}–{shape.get('high')}, {shape.get('motion')}")
    print(f"key\t{request['music']['key']}\t({key_src})")
    print(f"lyrics\t{'yes, ' + str(len(lyr.splitlines())) + ' lines' if lyr else 'none (instrumental only)'}")
    for w in warnings:
        print(f"warning\t{w}")
    print(f"request\t{outdir / 'request.json'}")
    print(f"brief\t{outdir / 'BRIEF.md'}")
    if seed:
        print(f"seed\t{seed['path']}\t{seed['duration_s']} s")
    return 0


def brief(r: dict, comp: dict) -> str:
    m, s = r["music"], r["suno"]
    mel = m["melody"]
    out = [f"# {s['title']} → Suno", "",
           f"Prepared {r['prepared']} by jamai-suno {r['bridge_version']}. Nothing has been sent to Suno.", "",
           "## What was read", "",
           f"- ABC: `{r['composition']['abc']}` ({r['composition']['abc_rule']})",
           f"- Key: {m['key'] or 'not stated'} ({m['key_source']}); composition.json key: "
           f"{r['composition']['composition_key'] or 'empty'}",
           f"- Meter {m['meter']}, {m['tempo_bpm']} BPM, {m['bars']} bars, about {m['duration_s_at_tempo']} s at tempo",
           f"- Voices: " + "; ".join(f"{v['id']} {v['name'] or '(no name)'} ({v['instrument'] or '?'})"
                                     for v in m["voices"]),
           f"- Melody: voice {m['melody_voice']['id']} ({m['melody_voice']['rule']}). "
           f"{mel.get('low')}–{mel.get('high')} ({mel.get('range_semitones')} semitones), {mel.get('motion')} "
           f"({mel.get('steps_pct')} % steps, {mel.get('skips_pct')} % thirds, {mel.get('leaps_pct')} % leaps), {mel.get('shape')}, peak in bar "
           f"{mel.get('peak_bar')}, {mel.get('drift')} ({mel.get('first_note')} → {mel.get('last_note')}).",
           f"- Chords: {' · '.join(m['chords']) or 'none named'}", ""]
    if r["warnings"]:
        out += ["## Check before generating", ""] + [f"- {w}" for w in r["warnings"]] + [""]
    out += ["## The request (default: instrumental)", "", f"Title: **{s['title']}**", "", "Style:", "",
            f"> {s['style']}", ""]
    lv = r["variants"].get("lyrics")
    if lv:
        out += ["## Lyrics variant (`--variant lyrics`)", "", f"From {lv['lyrics_source']}, language "
                f"{lv['language'] or 'not known'}.", "", "Style:", "", f"> {lv['style']}", "", "```",
                lv["lyrics"], "```", ""]
    else:
        out += ["No ABC `w:` lines, so there is no lyrics variant (decision D2).", ""]
    sd = r["seed_audio"]
    if sd:
        out += ["## Seed audio", "", f"`{sd['path']}` ({sd['content']}, {sd['duration_s']} s), rendered by "
                f"`{sd['renderer']}` from `{sd['source_abc']}`. Used only if the Suno tool accepts audio.", ""]
    texts = [t for t in comp.get("texts") or [] if isinstance(t, dict)]
    if texts:
        out += ["## Context from composition.json texts[] (never sent to Suno, decision D2)", ""]
        for t in texts:
            first = next((ln.strip("# ").strip() for ln in (t.get("content") or "").splitlines() if ln.strip()), "")
            out.append(f"- {t.get('label') or t.get('filename')}: {first[:140]}")
        out.append("")
    out += ["## Next", "", "```", f"jamai-suno generate {r['composition']['folder']} --plan",
            f"jamai-suno generate {r['composition']['folder']}" + (" --variant lyrics" if lv else ""), "```", ""]
    return "\n".join(out)


# ─── MCP client ────────────────────────────────────────────────────────────

class AuthRequired(Stop):
    def __init__(self, detail: str):
        super().__init__(f"authorization required: {detail}", EXIT_AUTH)


class Log:
    def __init__(self, path: Path | None):
        self.path = path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, kind: str, **data):
        if not self.path:
            return
        rec = {"t": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), "kind": kind, **data}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _redact(headers: dict) -> dict:
    return {k: ("Bearer …" if k.lower() == "authorization" else v) for k, v in headers.items()}


class MCP:
    def __init__(self, url: str, token: str | None, log: Log):
        self.url, self.token, self.log = url, token, log
        self.session: str | None = None
        self.next_id = 1

    def _post(self, payload: dict, expect_reply: bool = True):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": PROTOCOL_VERSION, "User-Agent": f"jamai-suno/{VERSION}"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        self.log.write("request", url=self.url, headers=_redact(headers), body=payload)
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            self.log.write("response", status=e.code, headers=dict(e.headers), body=body)
            if e.code == 401:
                raise AuthRequired(f"{self.url} answered 401 ({body.strip()[:120]})")
            if e.code == 403:
                raise AuthRequired(f"{self.url} answered 403, the token lacks a scope ({body.strip()[:120]})")
            raise Stop(f"{self.url} answered HTTP {e.code}: {body[:300]}", EXIT_SERVER)
        except urllib.error.URLError as e:
            raise Stop(f"cannot reach {self.url}: {e.reason}", EXIT_SERVER)
        with resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self.session = sid
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8", "replace")
            self.log.write("response", status=resp.status, content_type=ctype, body=raw[:200000])
        if not expect_reply or not raw.strip():
            return None
        if "text/event-stream" in ctype:
            found = None
            for block in re.split(r"\r?\n\r?\n", raw):
                data = "\n".join(ln[5:].lstrip() for ln in block.splitlines() if ln.startswith("data:"))
                if not data:
                    continue
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == payload.get("id") and (
                        "result" in msg or "error" in msg):
                    found = msg
            if found is None:
                raise Stop("the server's event stream ended without a reply", EXIT_SERVER)
            return found
        return json.loads(raw)

    def call(self, method: str, params: dict | None = None):
        rid = self.next_id
        self.next_id += 1
        msg = self._post({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        if "error" in msg:
            raise Stop(f"{method}: {msg['error']}", EXIT_SERVER)
        return msg["result"]

    def open(self):
        init = self.call("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                        "clientInfo": {"name": "jamai-suno", "version": VERSION}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_reply=False)
        return init

    def tools(self) -> list[dict]:
        tools, cursor = [], None
        while True:
            res = self.call("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(res.get("tools", []))
            cursor = res.get("nextCursor")
            if not cursor:
                return tools


# ─── OAuth (login) ─────────────────────────────────────────────────────────

def _get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                timeout=30) as r:
        return json.loads(r.read())


def _post_form(url: str, data: dict, as_json: bool = False) -> dict:
    body = json.dumps(data).encode() if as_json else urllib.parse.urlencode(data).encode()
    ctype = "application/json" if as_json else "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": ctype, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise Stop(f"{url} answered HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}", EXIT_AUTH)


def discover(mcp_url: str) -> tuple[dict, dict]:
    u = urllib.parse.urlsplit(mcp_url)
    prm = _get_json(f"{u.scheme}://{u.netloc}/.well-known/oauth-protected-resource{u.path}")
    issuer = prm["authorization_servers"][0]
    i = urllib.parse.urlsplit(issuer)
    try:
        asm = _get_json(f"{i.scheme}://{i.netloc}/.well-known/oauth-authorization-server{i.path}")
    except urllib.error.HTTPError:
        asm = _get_json(issuer.rstrip("/") + "/.well-known/oauth-authorization-server")
    return prm, asm


def save_token(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    tmp = TOKEN_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, TOKEN_FILE)


def load_token() -> tuple[str | None, str]:
    env = os.environ.get("SUNO_MCP_TOKEN")
    if env:
        return env, "SUNO_MCP_TOKEN"
    if not TOKEN_FILE.is_file():
        return None, "none"
    data = json.loads(TOKEN_FILE.read_text())
    if data.get("expires_at", 0) - 60 > dt.datetime.now().timestamp():
        return data["access_token"], str(TOKEN_FILE)
    if data.get("refresh_token"):
        tok = _post_form(data["token_endpoint"], {"grant_type": "refresh_token",
                                                  "refresh_token": data["refresh_token"],
                                                  "client_id": data["client_id"], "resource": data["resource"]})
        data.update(access_token=tok["access_token"],
                    refresh_token=tok.get("refresh_token", data["refresh_token"]),
                    expires_at=dt.datetime.now().timestamp() + float(tok.get("expires_in", 3600)))
        save_token(data)
        return data["access_token"], f"{TOKEN_FILE} (refreshed)"
    return None, f"{TOKEN_FILE} (expired, no refresh token)"


def cmd_login(a) -> int:
    prm, asm = discover(MCP_URL)
    scopes = " ".join(prm.get("scopes_supported") or [])
    port = a.port
    # --redirect-uri: a public address (e.g. on your own domain) that a reverse proxy forwards to
    # 127.0.0.1:<port>/callback. Suno sends the browser there instead of to this machine's loopback.
    public = bool(a.redirect_uri)
    redirect = a.redirect_uri or f"http://127.0.0.1:{port}/callback"
    reg = _post_form(asm["registration_endpoint"], {
        "client_name": "jamai-suno (JamAI bridge)", "redirect_uris": [redirect],
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
        "token_endpoint_auth_method": "none", "scope": scopes}, as_json=True)
    client_id = reg["client_id"]
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = asm["authorization_endpoint"] + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect, "scope": scopes,
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": prm["resource"]})
    got: dict = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            if public and q.get("state", [None])[0] != state:
                # A public route can be hit by anyone: only this login's own callback ends the wait.
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"jamai-suno: not this login's callback.\n")
                return
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("jamai-suno: authorization received, you can close this tab.\n".encode())

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    srv.timeout = a.timeout
    if public:
        print(f"Callback: {redirect} → 127.0.0.1:{port}/callback")
        print("Open this URL in any browser, sign in to Suno and approve:\n")
    else:
        print("Open this URL in a browser on this machine, sign in to Suno and approve:\n")
    print(url + "\n", flush=True)
    if not a.no_browser:
        webbrowser.open(url)
    if public:
        deadline = time.monotonic() + a.timeout
        while not got and time.monotonic() < deadline:
            srv.timeout = max(1.0, deadline - time.monotonic())
            srv.handle_request()
    else:
        srv.handle_request()
    srv.server_close()
    if not got:
        raise Stop("no answer from the browser before the timeout", EXIT_AUTH)
    if got.get("state") != state:
        raise Stop("the callback's state does not match; nothing saved", EXIT_AUTH)
    if "code" not in got:
        raise Stop(f"Suno did not authorize: {got.get('error')} {got.get('error_description', '')}", EXIT_AUTH)
    tok = _post_form(asm["token_endpoint"], {"grant_type": "authorization_code", "code": got["code"],
                                             "redirect_uri": redirect, "client_id": client_id,
                                             "code_verifier": verifier, "resource": prm["resource"]})
    save_token({"resource": prm["resource"], "client_id": client_id, "token_endpoint": asm["token_endpoint"],
                "scope": tok.get("scope", scopes), "access_token": tok["access_token"],
                "refresh_token": tok.get("refresh_token"),
                "expires_at": dt.datetime.now().timestamp() + float(tok.get("expires_in", 3600))})
    print(f"saved\t{TOKEN_FILE} (mode 600)")
    return 0


# ─── generate / tools / status ─────────────────────────────────────────────

SYNONYMS = {
    "title": ["title", "song_title", "name"],
    "style": ["style", "styles", "tags", "style_prompt", "prompt", "description", "gpt_description_prompt"],
    "lyrics": ["lyrics", "prompt", "text"],
    "instrumental": ["instrumental", "make_instrumental", "is_instrumental"],
}


def build_arguments(tool: dict, req: dict) -> tuple[dict, list[str]]:
    props = (tool.get("inputSchema") or {}).get("properties", {})
    required = set((tool.get("inputSchema") or {}).get("required", []))
    args, notes, used = {}, [], set()
    values = {"title": req.get("title"), "style": req.get("style"), "lyrics": req.get("lyrics"),
              "instrumental": req.get("instrumental")}
    for field in ("lyrics", "title", "style", "instrumental"):   # lyrics first: it may claim "prompt"
        val = values[field]
        if val is None:
            continue
        for name in SYNONYMS[field]:
            if name in props and name not in used:
                if props[name].get("type") == "array" and isinstance(val, str):
                    val = [s.strip() for s in val.split(";") if s.strip()]
                args[name] = val
                used.add(name)
                break
        else:
            notes.append(f"the tool has no parameter for {field}")
    # Songs stay private when the tool lets us say so.
    for name, spec in props.items():
        low = name.lower()
        if low in ("public", "is_public", "make_public") and spec.get("type") == "boolean":
            args[name] = False
        elif low in ("private", "is_private", "make_private") and spec.get("type") == "boolean":
            args[name] = True
        elif low == "visibility" and "private" in (spec.get("enum") or []):
            args[name] = "private"
    missing = sorted(required - set(args))
    if missing:
        raise Stop(f"tool {tool['name']} requires {missing}, which the request does not fill. "
                   f"Its schema: {json.dumps(tool.get('inputSchema'), ensure_ascii=False)[:800]}", EXIT_TOOL)
    for name, val in args.items():
        ml = props[name].get("maxLength")
        if ml and isinstance(val, str) and len(val) > ml:
            raise Stop(f"{name} is {len(val)} characters, the tool allows {ml}", EXIT_TOOL)
    return args, notes


AUDIO_URL = re.compile(r"https?://[^\s\"'<>]+?\.(?:mp3|wav|m4a|ogg|flac)(?:\?[^\s\"'<>]*)?", re.I)


def harvest(result) -> tuple[list[str], list[dict]]:
    urls, blobs = [], []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "audio" and x.get("data"):
                blobs.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            if x.strip().startswith(("{", "[")):
                try:
                    walk(json.loads(x))
                    return
                except json.JSONDecodeError:
                    pass
            urls.extend(AUDIO_URL.findall(x))

    walk(result)
    return list(dict.fromkeys(urls)), blobs


def connect(log: Log) -> MCP:
    token, source = load_token()
    log.write("auth", token_source=source)
    client = MCP(MCP_URL, token, log)
    try:
        client.open()
    except AuthRequired as e:
        hint = ("run `jamai-suno login` (your Suno sign-in and approval)" if not token
                else "the saved token was refused; run `jamai-suno login` again")
        raise AuthRequired(f"{e.args[0].split(': ', 1)[1]}. Token: {source}. Next: {hint}.")
    return client


def choose_tool(tools: list[dict], explicit: str | None) -> dict:
    names = [t["name"] for t in tools]
    want = explicit
    if not want and TOOL_MAP_FILE.is_file():
        want = json.loads(TOOL_MAP_FILE.read_text()).get("generate")
    if not want:
        raise Stop("which tool generates a song? Pass --tool NAME, or write "
                   f'{{"generate": "NAME"}} in {TOOL_MAP_FILE}. Live tools: {", ".join(names)}', EXIT_TOOL)
    for t in tools:
        if t["name"] == want:
            return t
    raise Stop(f"tool {want!r} is not offered by the server. Live tools: {', '.join(names)}", EXIT_TOOL)


def cmd_generate(a) -> int:
    folder = Path(a.folder).expanduser().resolve()
    rq = folder / "suno" / "request.json"
    if not rq.is_file():
        raise Stop(f"{rq}: not found. Run `jamai-suno prepare {folder}` first.")
    request = json.loads(rq.read_text(encoding="utf-8"))
    if a.variant == "lyrics":
        if "lyrics" not in request["variants"]:
            raise Stop("this composition has no lyrics variant (no ABC w: lines)")
        req = request["variants"]["lyrics"]
    else:
        req = request["suno"]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = Log(folder / "suno" / "log" / f"{stamp}-generate.jsonl")
    log.write("start", variant=a.variant, request=str(rq), endpoint=MCP_URL, plan=a.plan)
    try:
        client = connect(log)
        tools = client.tools()
        (folder / "suno" / "tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2) + "\n")
        tool = choose_tool(tools, a.tool)
        args, notes = build_arguments(tool, req)
        log.write("plan", tool=tool["name"], arguments=args, notes=notes)
        print(f"tool\t{tool['name']}")
        print("arguments\t" + json.dumps(args, ensure_ascii=False, indent=2))
        for n in notes:
            print(f"note\t{n}")
        if a.plan:
            print("plan\tnothing sent (--plan)")
            return 0
        result = client.call("tools/call", {"name": tool["name"], "arguments": args})
    except Stop as e:
        log.write("stop", code=e.code, message=str(e))
        raise
    outdir = folder / "suno" / f"{stamp}-{a.variant}"
    outdir.mkdir(parents=True)
    (outdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (outdir / "call.json").write_text(json.dumps({"tool": tool["name"], "arguments": args}, ensure_ascii=False,
                                                 indent=2) + "\n")
    urls, blobs = harvest(result)
    saved = []
    for i, u in enumerate(urls, 1):
        ext = Path(urllib.parse.urlsplit(u).path).suffix or ".mp3"
        dest = outdir / f"take-{i}{ext}"
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": f"jamai-suno/{VERSION}"}),
                                        timeout=120) as r, dest.open("wb") as fh:
                shutil.copyfileobj(r, fh)
            saved.append(str(dest))
        except (urllib.error.URLError, OSError) as e:
            log.write("download_failed", url=u, error=str(e))
    for i, b in enumerate(blobs, 1):
        ext = {"audio/mpeg": ".mp3", "audio/wav": ".wav"}.get(b.get("mimeType", ""), ".bin")
        dest = outdir / f"blob-{i}{ext}"
        dest.write_bytes(base64.b64decode(b["data"]))
        saved.append(str(dest))
    log.write("done", outdir=str(outdir), audio=saved, is_error=result.get("isError"))
    print(f"result\t{outdir / 'result.json'}")
    for s in saved:
        print(f"audio\t{s}")
    if not saved:
        print("audio\tnone in the reply. Read result.json: the tool may return an id to poll with another tool.")
    print(f"log\t{log.path}")
    return 1 if result.get("isError") else 0


def cmd_tools(a) -> int:
    log = Log(Path(a.log) if a.log else None)
    client = connect(log)
    tools = client.tools()
    if a.json:
        print(json.dumps(tools, ensure_ascii=False, indent=2))
        return 0
    for t in tools:
        props = (t.get("inputSchema") or {}).get("properties", {})
        req = set((t.get("inputSchema") or {}).get("required", []))
        params = ", ".join(f"{k}{'*' if k in req else ''}:{v.get('type', '?')}" for k, v in props.items())
        print(f"{t['name']}\t{(t.get('description') or '').splitlines()[0][:100] if t.get('description') else ''}")
        print(f"\t({params})")
    return 0


def cmd_status(a) -> int:
    token, source = load_token()
    print(f"endpoint\t{MCP_URL}")
    print(f"token\t{source if token else 'none'}")
    try:
        MCP(MCP_URL, token, Log(None)).open()
        print("server\tauthorized: initialize succeeded")
        return 0
    except AuthRequired as e:
        print(f"server\t{e}")
        return EXIT_AUTH


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="jamai-suno", description=__doc__.split("\n\n")[0])
    p.add_argument("--version", action="version", version=f"jamai-suno {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare", help="write suno/request.json, BRIEF.md and the seed MP3")
    s.add_argument("folder")
    s.add_argument("--abc", help="the ABC file to read (decision D1)")
    s.add_argument("--key", help='name the key when the ABC header does not, e.g. "E Phrygian"')
    s.add_argument("--seed", choices=["melody", "full", "none"], default="melody")
    s.set_defaults(fn=cmd_prepare)
    g = sub.add_parser("generate", help="send request.json to Suno's MCP server")
    g.add_argument("folder")
    g.add_argument("--variant", choices=["instrumental", "lyrics"], default="instrumental")
    g.add_argument("--tool", help="the Suno tool to call (see `jamai-suno tools`)")
    g.add_argument("--plan", action="store_true", help="show the call, send nothing that spends credits")
    g.set_defaults(fn=cmd_generate)
    t = sub.add_parser("tools", help="list the tools the authorized server offers")
    t.add_argument("--json", action="store_true")
    t.add_argument("--log")
    t.set_defaults(fn=cmd_tools)
    lg = sub.add_parser("login", help="sign in to Suno and approve this bridge (OAuth, PKCE)")
    lg.add_argument("--port", type=int, default=41799)
    lg.add_argument("--no-browser", action="store_true")
    lg.add_argument("--timeout", type=int, default=600)
    lg.add_argument("--redirect-uri", help="public callback URL that proxies to 127.0.0.1:<port>/callback; "
                                           "used for registration and authorization")
    lg.set_defaults(fn=cmd_login)
    st = sub.add_parser("status", help="where the authorization stands")
    st.set_defaults(fn=cmd_status)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except Stop as e:
        print(f"jamai-suno: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
