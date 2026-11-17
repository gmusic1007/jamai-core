#!/usr/bin/env python3
"""Parseur MIDI note à note. mido n'est pas installé sur cette machine."""
import sys, struct

NAMES = ['do','do#','ré','ré#','mi','fa','fa#','sol','sol#','la','la#','si']
ABC_OCT4 = ['C','^C','D','^D','E','F','^F','G','^G','A','^A','B']

# General MIDI program names, 0 to 127.
GM = [
    'Acoustic Grand Piano',
    'Bright Acoustic Piano',
    'Electric Grand Piano',
    'Honky-tonk Piano',
    'Electric Piano 1',
    'Electric Piano 2',
    'Harpsichord',
    'Clavinet',
    'Celesta',
    'Glockenspiel',
    'Music Box',
    'Vibraphone',
    'Marimba',
    'Xylophone',
    'Tubular Bells',
    'Dulcimer',
    'Drawbar Organ',
    'Percussive Organ',
    'Rock Organ',
    'Church Organ',
    'Reed Organ',
    'Accordion',
    'Harmonica',
    'Tango Accordion',
    'Acoustic Guitar (nylon)',
    'Acoustic Guitar (steel)',
    'Electric Guitar (jazz)',
    'Electric Guitar (clean)',
    'Electric Guitar (muted)',
    'Overdriven Guitar',
    'Distortion Guitar',
    'Guitar Harmonics',
    'Acoustic Bass',
    'Electric Bass (finger)',
    'Electric Bass (pick)',
    'Fretless Bass',
    'Slap Bass 1',
    'Slap Bass 2',
    'Synth Bass 1',
    'Synth Bass 2',
    'Violin',
    'Viola',
    'Cello',
    'Contrabass',
    'Tremolo Strings',
    'Pizzicato Strings',
    'Orchestral Harp',
    'Timpani',
    'String Ensemble 1',
    'String Ensemble 2',
    'Synth Strings 1',
    'Synth Strings 2',
    'Choir Aahs',
    'Voice Oohs',
    'Synth Voice',
    'Orchestra Hit',
    'Trumpet',
    'Trombone',
    'Tuba',
    'Muted Trumpet',
    'French Horn',
    'Brass Section',
    'Synth Brass 1',
    'Synth Brass 2',
    'Soprano Sax',
    'Alto Sax',
    'Tenor Sax',
    'Baritone Sax',
    'Oboe',
    'English Horn',
    'Bassoon',
    'Clarinet',
    'Piccolo',
    'Flute',
    'Recorder',
    'Pan Flute',
    'Blown Bottle',
    'Shakuhachi',
    'Whistle',
    'Ocarina',
    'Lead 1 (square)',
    'Lead 2 (sawtooth)',
    'Lead 3 (calliope)',
    'Lead 4 (chiff)',
    'Lead 5 (charang)',
    'Lead 6 (voice)',
    'Lead 7 (fifths)',
    'Lead 8 (bass + lead)',
    'Pad 1 (new age)',
    'Pad 2 (warm)',
    'Pad 3 (polysynth)',
    'Pad 4 (choir)',
    'Pad 5 (bowed)',
    'Pad 6 (metallic)',
    'Pad 7 (halo)',
    'Pad 8 (sweep)',
    'FX 1 (rain)',
    'FX 2 (soundtrack)',
    'FX 3 (crystal)',
    'FX 4 (atmosphere)',
    'FX 5 (brightness)',
    'FX 6 (goblins)',
    'FX 7 (echoes)',
    'FX 8 (sci-fi)',
    'Sitar',
    'Banjo',
    'Shamisen',
    'Koto',
    'Kalimba',
    'Bagpipe',
    'Fiddle',
    'Shanai',
    'Tinkle Bell',
    'Agogo',
    'Steel Drums',
    'Woodblock',
    'Taiko Drum',
    'Melodic Tom',
    'Synth Drum',
    'Reverse Cymbal',
    'Guitar Fret Noise',
    'Breath Noise',
    'Seashore',
    'Bird Tweet',
    'Telephone Ring',
    'Helicopter',
    'Applause',
    'Gunshot',
]

def name(n):        # 60 = do4 (do du milieu)
    return f"{NAMES[n % 12]}{n // 12 - 1}"

def abc(n):
    """MIDI -> ABC, avec do4 = C (middle C)."""
    base = ABC_OCT4[n % 12]
    o = n // 12 - 1          # octave scientifique
    if o >= 5:  return base.lower() + "'" * (o - 5)
    if o == 4:  return base
    return base + "," * (4 - o)

def vlq(d, i):
    v = 0
    while True:
        b = d[i]; i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80: return v, i

path = sys.argv[1]
d = open(path, 'rb').read()
assert d[:4] == b'MThd', "pas un fichier MIDI"
fmt, ntrk, div = struct.unpack('>HHH', d[8:14])
print(f"# {path}  ({len(d)} octets)")
print(f"format {fmt} · {ntrk} piste(s) · division {div} ticks/noire\n")

i = 14
tempo = 500000
for tk in range(ntrk):
    assert d[i:i+4] == b'MTrk', f"piste {tk} malformée"
    ln = struct.unpack('>I', d[i+4:i+8])[0]
    j, end = i + 8, i + 8 + ln
    i = end
    t, run = 0, None
    on, notes, others = {}, [], []
    while j < end:
        dt, j = vlq(d, j); t += dt
        b = d[j]
        if b & 0x80: st = b; j += 1; run = st
        else: st = run
        hi, ch = st & 0xF0, st & 0x0F
        if st == 0xFF:
            mt = d[j]; j += 1
            ml, j = vlq(d, j); pl = d[j:j+ml]; j += ml
            if mt == 0x51:
                tempo = int.from_bytes(pl, 'big')
                others.append((t, f"tempo {60_000_000/tempo:.1f} BPM"))
            elif mt == 0x58:
                others.append((t, f"mesure {pl[0]}/{2**pl[1]}"))
            elif mt == 0x59:
                others.append((t, f"armure sf={struct.unpack('b',pl[:1])[0]} {'min' if pl[1] else 'maj'}"))
            elif mt in (0x01, 0x03, 0x04):
                others.append((t, f"texte {pl.decode('latin1')!r}"))
        elif st in (0xF0, 0xF7):
            ml, j = vlq(d, j); j += ml
        elif hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
            a, b2 = d[j], d[j+1]; j += 2
            if hi == 0x90 and b2 > 0:
                on.setdefault((ch, a), []).append((t, b2))
            elif hi == 0x80 or (hi == 0x90 and b2 == 0):
                k = (ch, a)
                if on.get(k):
                    st0, v = on[k].pop(0)
                    notes.append((st0, t - st0, ch, a, v))
            elif hi == 0xB0:
                others.append((t, f"CC{a}={b2} ch{ch}"))
        elif hi == 0xC0:
            # Lu et jamais affiché jusqu'au 2026-11-17 : les instruments d'un fichier étaient invisibles.
            prog = d[j]; j += 1
            others.append((t, f"programme {prog} ({GM[prog]}) ch{ch}" + (" — percussions" if ch == 9 else "")))
        elif hi == 0xD0:
            j += 1
        else:
            j += 1

    notes.sort()
    print(f"## piste {tk} — {len(notes)} note(s)")
    for t0, ev in others: print(f"   [t={t0}] {ev}")
    if not notes: print("   (aucune note)\n"); continue
    print(f"   {'début(t)':>9} {'temps':>7} {'durée':>6} {'ch':>3} {'midi':>5} {'nom':>7} {'abc':>5} {'vel':>4}")
    for t0, du, ch, n, v in notes:
        print(f"   {t0:9d} {t0/div:7.3f} {du/div:6.3f} {ch:3d} {n:5d} {name(n):>7} {abc(n):>5} {v:4d}")
    span = max(t0+du for t0,du,_,_,_ in notes)
    print(f"   étendue : {span/div:.3f} temps  ({span} ticks)")
    print(f"   ambitus : {name(min(n[3] for n in notes))} → {name(max(n[3] for n in notes))}")
    print(f"   classes de hauteur : {sorted({NAMES[n[3]%12] for n in notes}, key=lambda s: NAMES.index(s))}\n")
