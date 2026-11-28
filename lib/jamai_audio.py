"""jamai_audio — what the listen/ tools share to hear a recording: numpy only.

    import jamai_audio as ja
    x, sr = ja.load("prise.m4a")                 # mono, 22 050 Hz, any format ffmpeg reads
    env, fps = ja.onset_envelope(x, sr)
    bpm, candidates = ja.tempo(env, fps)
    beats = ja.beats(env, fps, bpm)              # seconds
    bass, treble = ja.bass_treble(x, sr, start, end)
    rows = [ja.chord_scores(t, b) for b, t in segments]  # then ja.smooth(rows) → one chord each

Written on 2026-11-27, after « Monde immonde ». Two faults of the first listen/ tools were
measured on that live recording, and this module exists so they are fixed once:

- A stereo WAV read with `wave` as if it were mono doubles its duration and halves its tempo.
  jamai-measure said 279.98 s and 64.6 BPM for a take of 140 s at 129. Everything goes
  through ffmpeg, which mixes the channels down.
- A chroma taken from a 2048-point FFT at 44.1 kHz has bins 21.5 Hz apart: below 500 Hz the
  energy of a note lands on the pitch class of the nearest bin, not its own. The guitar stem
  of « Monde immonde » came out with si at 1.75 % in a song built on Em and B7. Here the FFT
  has 16 384 points at 22 050 Hz (1.35 Hz), enough to separate E1 from F1.

The beat tracker and the bass/treble split come from the session's librosa scripts
(beats.py, beatchroma.py), rewritten without librosa: the dynamic-programming tracker of
Ellis (2007), the one librosa.beat.beat_track uses, and a bass chroma kept apart so that the
bass, not the alphabet, chooses between two chords made of the same notes (Em7 and G6).
"""
import math
import os
import shutil
import subprocess
import tempfile
import wave

import numpy as np

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FR = ['do', 'do#', 'ré', 'ré#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si']
SR = 22050


# ─────────────────────────────────────────────────────────────────── reading

def load(path, sr=SR):
    """Mono float samples at `sr`, from any file ffmpeg reads (wav, m4a, mp3, mp4, flac).

    Without ffmpeg, only a 16-bit PCM WAV is read, and its channels are averaged."""
    if shutil.which("ffmpeg"):
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            done = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-map", "0:a:0",
                                   "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", tmp], capture_output=True)
            if done.returncode != 0:
                raise ValueError("no audio stream ffmpeg can read in %s: %s"
                                 % (path, done.stderr.decode(errors="replace").strip()[-300:]))
            return _read_wav(tmp)[0], sr
        finally:
            os.unlink(tmp)
    x, file_sr = _read_wav(path)
    if file_sr != sr:
        # Linear resampling: rough, and only used when ffmpeg is missing.
        n = int(round(len(x) * sr / file_sr))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    return x, sr


def _read_wav(path):
    with wave.open(path, "rb") as w:
        ch, width, file_sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError("%s is %d-bit PCM; install ffmpeg to read it" % (path, 8 * width))
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, file_sr


# ─────────────────────────────────────────────────────────────────── spectra

def frames(x, n_fft, hop):
    """Magnitude spectra, one row per frame, Hann window. Yields (start_sample, magnitude)."""
    win = np.hanning(n_fft)
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    for s in range(0, len(x) - n_fft + 1, hop):
        yield s, np.abs(np.fft.rfft(x[s:s + n_fft] * win))


def onset_envelope(x, sr, n_fft=2048, hop=512):
    """Spectral flux on log magnitude, half-wave rectified, local mean removed.

    Returns (envelope, frames per second). Frame i is centred at (i * hop + n_fft / 2) / sr."""
    prev, out = None, []
    for _, mag in frames(x, n_fft, hop):
        lm = np.log1p(1000.0 * mag)
        out.append(0.0 if prev is None else float(np.maximum(0.0, lm - prev).sum()))
        prev = lm
    env = np.array(out)
    if len(env) > 16:
        k = 16
        local = np.convolve(env, np.ones(k) / k, mode="same")
        env = np.maximum(0.0, env - local)
    peak = env.max() if len(env) else 0.0
    return (env / peak if peak > 0 else env), sr / hop


def frame_time(i, fps, n_fft=2048, hop=512):
    """Time of envelope frame i, in seconds: where the hop that frame i adds to frame i−1 ends.

    Calibrated against librosa on « Monde immonde »: with the window centre instead, every
    beat came 46 ms before librosa's, a constant offset of two frames."""
    return (i + n_fft / float(hop)) / fps


def tempo(env, fps, lo=50, hi=200, prior=120.0):
    """Tempo by autocorrelation of the onset envelope, weighted by a log-normal prior around
    `prior` BPM (one octave wide), the way librosa does it. A raw autocorrelation peak is
    often half or double the pulse a musician counts; the prior picks the musician's octave,
    and the candidates are returned so the choice can be contradicted.

    Returns (bpm, [(bpm, strength), …] strongest first)."""
    e = env - env.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    if ac[0] <= 0:
        return 0.0, []
    ac = ac / ac[0]
    lags = np.arange(len(ac))
    lo_l, hi_l = max(1, int(fps * 60 / hi)), min(len(ac) - 1, int(fps * 60 / lo))
    if hi_l <= lo_l:
        return 0.0, []
    seg = lags[lo_l:hi_l]
    bpm = 60.0 * fps / seg
    weight = np.exp(-0.5 * (np.log2(bpm / prior) / 1.0) ** 2)
    score = ac[lo_l:hi_l] * weight
    order = np.argsort(-score)
    picked, cands = [], []
    for j in order:
        if any(abs(seg[j] - p) <= 1 for p in picked):
            continue
        picked.append(seg[j])
        # parabolic interpolation around the lag peak, for a tempo finer than one frame
        L = seg[j]
        if 1 <= L < len(ac) - 1:
            a, b, c = ac[L - 1], ac[L], ac[L + 1]
            d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        else:
            d = 0.0
        cands.append((60.0 * fps / (L + d), float(ac[L])))
        if len(cands) == 6:
            break
    return (cands[0][0] if cands else 0.0), cands


def beats(env, fps, bpm, tightness=100.0):
    """Beat times in seconds, by dynamic programming (Ellis 2007): each beat is an onset
    peak, and the gap between two beats stays close to the period of `bpm`."""
    if bpm <= 0 or len(env) < 4:
        return []
    period = fps * 60.0 / bpm
    # The penalty below is on the scale of an envelope divided by its standard deviation, as
    # in Ellis (2007) and librosa. Divided by its maximum instead, the onsets weigh twenty
    # times less than the penalty and the beats become a metronome that drifts off the music.
    # Measured on the guitar stem of « Monde immonde »: 32 % of the beats within 70 ms of
    # librosa's before, 65 % once the scale was right (and the frame time calibrated).
    sd = float(np.std(env))
    env = env / sd if sd > 0 else env
    # smooth the envelope with a Gaussian a tenth of a period wide
    w = max(1, int(round(period / 10)))
    g = np.exp(-0.5 * (np.arange(-2 * w, 2 * w + 1) / w) ** 2)
    local = np.convolve(env, g / g.sum(), mode="same")
    n = len(local)
    score = local.copy()
    back = -np.ones(n, dtype=int)
    lo, hi = int(round(period / 2)), int(round(2 * period))
    offsets = np.arange(-hi, -lo + 1)
    penalty = -tightness * (np.log(-offsets / period)) ** 2
    for i in range(n):
        cand = i + offsets
        ok = cand >= 0
        if not ok.any():
            continue
        c = cand[ok]
        vals = score[c] + penalty[ok]
        k = int(np.argmax(vals))
        if vals[k] > 0:
            score[i] = local[i] + vals[k]
            back[i] = c[k]
    # the last beat: the best score among the final period, among frames that are local peaks
    tail = np.arange(max(0, n - int(round(period))), n)
    i = int(tail[np.argmax(score[tail])]) if len(tail) else n - 1
    path = []
    while i >= 0:
        path.append(i)
        i = back[i]
    path.reverse()
    # trim weak beats at both ends (silence before the first note and after the last)
    thr = 0.5 * np.median(local[path]) if path else 0
    while path and local[path[0]] < thr:
        path.pop(0)
    while path and local[path[-1]] < thr:
        path.pop()
    return [frame_time(i, fps) for i in path]


def local_tempi(beat_times, span=10.0):
    """Tempo in each span of `span` seconds, from the median gap between beats inside it."""
    out = []
    if len(beat_times) < 3:
        return out
    end = beat_times[-1]
    t = 0.0
    while t < end:
        b = [x for x in beat_times if t <= x < t + span]
        if len(b) >= 3:
            out.append((t, t + span, 60.0 / float(np.median(np.diff(b)))))
        t += span
    return out


# ──────────────────────────────────────────────────────────────────── chroma

N_FFT_PITCH = 16384     # 1.35 Hz per bin at 22 050 Hz
HOP_PITCH = 2048
BASS = (28, 52)         # E1 to E3: the bass the chord stands on
TREBLE = (48, 96)       # C3 to C7: the chord itself


def _note_weights(sr, n_fft):
    """A matrix (notes 21–108) × (bins) of triangular weights: each bin feeds the semitone it
    is closest to, more when it sits at its centre."""
    f = np.arange(n_fft // 2 + 1) * sr / n_fft
    with np.errstate(divide="ignore"):
        midi = 69 + 12 * np.log2(np.maximum(f, 1e-6) / 440.0)
    notes = np.arange(21, 109)
    d = np.abs(midi[None, :] - notes[:, None])
    W = np.clip(1.0 - 2.0 * d, 0.0, None)
    W[:, f < 30] = 0.0
    return notes, W


_W = {}


def semitone_spectrum(x, sr, start=0.0, end=None, n_fft=N_FFT_PITCH, hop=HOP_PITCH):
    """Energy per semitone (MIDI 21–108) between `start` and `end` seconds: the mean spectrum of
    the stretch, then the strongest bin inside each semitone.

    The strongest bin, not the sum: a high semitone spans eighty bins and a low one two, and a
    sum lets the noise floor of the high register outvote the notes. Measured on the guitar
    stem of « Monde immonde » while choosing, beat by beat: the sum of log magnitudes found
    35 % of the chord roots, the maximum 62 %."""
    if (sr, n_fft) not in _W:
        _W[(sr, n_fft)] = _note_weights(sr, n_fft)
    notes, W = _W[(sr, n_fft)]
    a = int(start * sr)
    b = len(x) if end is None else int(end * sr)
    seg = x[a:b]
    if len(seg) < n_fft // 4:
        return notes, np.zeros(len(notes))
    acc, k = None, 0
    for _, mag in frames(seg, n_fft, hop if len(seg) >= n_fft else n_fft):
        acc = mag if acc is None else acc + mag
        k += 1
    return notes, (W * (acc / k)[None, :]).max(axis=1)


def chroma_of(notes, energy, lo, hi):
    c = np.zeros(12)
    m = (notes >= lo) & (notes <= hi)
    np.add.at(c, notes[m] % 12, energy[m])
    return c


def bass_treble(x, sr, start=0.0, end=None):
    """(bass chroma, treble chroma) of a stretch of the recording. Not normalised: a silent
    stretch gives near-zero vectors, which chord() reports as no chord."""
    notes, e = semitone_spectrum(x, sr, start, end)
    return chroma_of(notes, e, *BASS), chroma_of(notes, e, *TREBLE)


# ──────────────────────────────────────────────────────────────────── chords

# Semitones above the root. Two templates with the same notes (G6 and Em7, Asus4 and Dsus2)
# can only be told apart by their bass: chord() adds the bass's weight on the root.
TEMPLATES = [
    ('', (0, 4, 7)), ('m', (0, 3, 7)),
    ('7', (0, 4, 7, 10)), ('m7', (0, 3, 7, 10)), ('maj7', (0, 4, 7, 11)),
    ('sus4', (0, 5, 7)), ('sus2', (0, 2, 7)),
    ('6', (0, 4, 7, 9)), ('add9', (0, 2, 4, 7)), ('madd9', (0, 2, 3, 7)),
    ('dim', (0, 3, 6)),
]
SIMPLE = {'', 'm'}


CANDIDATES = [(r, suf, iv) for suf, iv in TEMPLATES for r in range(12)]


def chord_scores(treble, bass, bass_weight=0.6, extension_cost=0.04):
    """One score per entry of CANDIDATES, or None for silence.

    score = cosine(treble, template) − 0.3·(treble energy outside the template)
            + bass_weight · (share of the bass on the root) − extension_cost per note above three"""
    tsum, bsum = float(treble.sum()), float(bass.sum())
    if tsum <= 1e-9:
        return None
    v = treble / tsum
    b = bass / bsum if bsum > 1e-9 else np.zeros(12)
    nv = np.linalg.norm(v)
    out = np.empty(len(CANDIDATES))
    for j, (r, _, iv) in enumerate(CANDIDATES):
        g = np.zeros(12)
        g[[(r + i) % 12 for i in iv]] = 1.0
        out[j] = (float(v @ g) / (nv * math.sqrt(len(iv))) - 0.3 * float(v[g == 0].sum())
                  + bass_weight * b[r] - extension_cost * (len(iv) - 3))
    return out


def label(j):
    r, suf, _ = CANDIDATES[j]
    return NAMES[r] + suf


def force(scores, j):
    """Margin of candidate j over the best candidate with a DIFFERENT root. Two names for one
    root (E and E7) are a nuance; two roots are a doubt. Below 0.03 the tool hesitates."""
    r = CANDIDATES[j][0]
    other = max(s for k, s in enumerate(scores) if CANDIDATES[k][0] != r)
    return float(scores[j] - other)


def smooth(score_rows, penalty=0.2):
    """The chord path through a list of score rows (None = silence) that maximises the total
    score minus `penalty` for each change of chord: a Viterbi path.

    A strummed guitar does not change chord on every beat, but a beat taken alone often looks
    like its neighbour's chord, or like a passing bass note. Measured on the guitar stem of
    « Monde immonde »: beat by beat 60 % of the roots were right, with a penalty of 0.2 per
    change 73 %.
    Returns one candidate index per row (None where the row is silence)."""
    idx = [i for i, s in enumerate(score_rows) if s is not None]
    path = [None] * len(score_rows)
    if not idx:
        return path
    S = np.array([score_rows[i] for i in idx])
    n, k = S.shape
    D = S[0].copy()
    B = np.zeros((n, k), dtype=int)
    for i in range(1, n):
        best = int(np.argmax(D))
        move = D[best] - penalty
        B[i] = np.where(D >= move, np.arange(k), best)
        D = np.maximum(D, move) + S[i]
    j = int(np.argmax(D))
    rev = [j]
    for i in range(n - 1, 0, -1):
        j = int(B[i][j])
        rev.append(j)
    for i, j in zip(idx, reversed(rev)):
        path[i] = j
    return path


def chord(treble, bass, **kw):
    """Name the chord of one stretch on its own: (label, force, bass_name), or (None, 0, None)."""
    s = chord_scores(treble, bass, **kw)
    if s is None:
        return None, 0.0, None
    j = int(np.argmax(s))
    bsum = float(bass.sum())
    return label(j), force(s, j), (NAMES[int(np.argmax(bass))] if bsum > 1e-9 else None)


# ─────────────────────────────────────────────────────────────────────── key

KRUM_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUM_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_profile(chroma):
    """Krumhansl correlation for the 24 keys, best first: [(r, 'C major'), …]."""
    v = chroma / (chroma.sum() or 1.0)
    out = []
    for t in range(12):
        out.append((float(np.corrcoef(v, np.roll(KRUM_MAJ, t))[0, 1]), "%s major" % NAMES[t], t, 'major'))
        out.append((float(np.corrcoef(v, np.roll(KRUM_MIN, t))[0, 1]), "%s minor" % NAMES[t], t, 'minor'))
    out.sort(key=lambda z: -z[0])
    return out


def key_from_chords(timeline):
    """The key whose functions explain the most chord time. `timeline` is [(root, quality,
    seconds)]. A minor key counts its own V and V7 (harmonic minor), because a song in E minor
    plays B7, and a Krumhansl profile then hears D# as a stranger and votes for D major.

    Returns [(share, 'E minor'), …] best first."""
    MAJ = {0: ('', 'maj7', '6', 'add9', 'sus2', 'sus4'), 2: ('m', 'm7', 'madd9', 'sus4', 'sus2'),
           4: ('m', 'm7'), 5: ('', 'maj7', '6', 'add9', 'sus2', 'sus4'), 7: ('', '7', 'sus4', 'sus2'),
           9: ('m', 'm7', 'madd9', 'sus4', 'sus2'), 11: ('dim',)}
    MIN = {0: ('m', 'm7', 'madd9', 'sus4', 'sus2'), 2: ('dim',), 3: ('', 'maj7', '6', 'add9', 'sus2'),
           5: ('m', 'm7', '', '7', 'sus4', 'sus2'), 7: ('m', 'm7', '', '7', 'sus4'),
           8: ('', 'maj7', 'add9'), 10: ('', '7', 'sus4', 'sus2')}
    total = sum(d for _, _, d in timeline) or 1.0
    out = []
    for t in range(12):
        for name, fn in (('major', MAJ), ('minor', MIN)):
            fit = sum(d for r, q, d in timeline if q in fn.get((r - t) % 12, ()))
            # the tonic chord itself weighs double: a key is where the music comes home
            home = sum(d for r, q, d in timeline if (r - t) % 12 == 0 and q in fn.get(0, ()))
            out.append(((fit + home) / (2 * total), "%s %s" % (NAMES[t], name)))
    out.sort(key=lambda z: -z[0])
    return out
