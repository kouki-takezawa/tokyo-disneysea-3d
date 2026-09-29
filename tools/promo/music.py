"""The promo film's music: an original music-box waltz in F major with a harp and a string pad, and the sounds of the film
(the book landing, pages turning, the dive, the volcano, the castle, fireworks, the book closing), timed to promo.html.

    python tools/promo/music.py    # -> output/disneysea/promo/music.m4a (about 50 s; the page plays it, record.py lays it under the film)

Everything is synthesised here with numpy (no samples), from a fixed seed, so it comes out the same every time.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "disneysea" / "promo" / "music.m4a"
SR = 44100
DUR = 50.0
rng = np.random.default_rng(20260929)
mix = np.zeros((2, int(SR * (DUR + 3))))

BAR, BAR0 = 2.5, 1.5     # 3/4 at 72 bpm; bar 1 starts at 1.5 s, so bar 5 lands on the dive's white-out (11.5 s)
BEAT = BAR / 3


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def put(at, sig, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= mix.shape[1]:
        return
    sig = sig[: mix.shape[1] - i] * gain
    mix[0, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    mix[1, i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def tt(d):
    return np.arange(int(d * SR)) / SR


def music_box(m, amp=0.16):
    f, t = hz(m), tt(3.0)
    k = (440 / f) ** 0.3
    s = np.zeros_like(t)
    for ratio, a, dec in [(1, 1, 1.1), (2.0, 0.32, 0.7), (3.0, 0.1, 0.45), (5.04, 0.1, 0.18), (8.2, 0.05, 0.08)]:
        if f * ratio < SR / 2.2:
            s += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / (dec * k))
    s *= np.minimum(1, t / 0.002)
    return s * amp


def harp(m, amp=0.1):
    f, t = hz(m), tt(2.4)
    s = sum(np.sin(2 * np.pi * f * n * t) / n ** 1.4 * np.exp(-t / (1.5 / n ** 0.6)) for n in range(1, 7) if f * n < SR / 2.2)
    return s * np.minimum(1, t / 0.003) * amp


def pad(ms, d, amp=0.022):
    t = tt(d + 1.0)
    env = np.minimum(1, t / 0.7) * np.clip((d + 1.0 - t) / 1.0, 0, 1)
    s = np.zeros_like(t)
    for m in ms:
        for det in (-0.12, 0, 0.12):
            f = hz(m + det)
            s += sum(np.sin(2 * np.pi * f * n * t + rng.uniform(0, 6.3)) / n ** 1.6 for n in range(1, 5))
    return s * env * amp


def bass(m, amp=0.13):
    f, t = hz(m), tt(2.2)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.9) * np.minimum(1, t / 0.01) * amp


def noise(d):
    return rng.standard_normal(int(d * SR))


def band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def low(x, fc):
    return sosfilt(butter(2, fc, btype="low", fs=SR, output="sos"), x)


def thud(amp=0.5):
    t = tt(0.6)
    f = 70 * np.exp(-t * 3) + 38
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) + 0.4 * low(noise(0.6), 300) * np.exp(-t / 0.05)) * amp


def swish(d=0.22, amp=0.12):
    t = tt(d)
    return band(noise(d), 1500, 7000) * np.sin(np.pi * t / d) ** 2 * amp


def glitter(at, d, n, amp=0.05, lo=84, hi=108):
    notes = [m for m in range(lo, hi) if m % 12 in (5, 7, 9, 0, 2)]   # F major pentatonic
    for _ in range(n):
        m = int(rng.choice(notes))
        t = tt(0.5)
        put(at + rng.uniform(0, d), np.sin(2 * np.pi * hz(m) * t) * np.exp(-t / 0.12) * amp, rng.uniform(-0.8, 0.8))


def gliss(at, d, m0, m1, amp=0.1):
    notes = [m for m in range(m0, m1 + 1) if m % 12 in (5, 7, 9, 0, 2)]
    for i, m in enumerate(notes):
        put(at + d * i / len(notes), music_box(m, amp), -0.6 + 1.2 * i / len(notes))


def whoosh(at, d, amp=0.2):
    t = tt(d)
    x = band(noise(d), 400, 4000) * (t / d) ** 2 * np.minimum(1, (d - t) / 0.05)
    put(at, x * amp)


def rumble(at, d, amp=0.35):
    t = tt(d)
    put(at, low(noise(d), 110) * np.minimum(1, t / 0.15) * np.exp(-t / (d * 0.35)) * amp * 3)


def firework(t0, pan):
    t = tt(0.9)   # the rocket's whistle
    f = 900 + 900 * t / 0.9
    put(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.2) * (1 - t / 0.9) * 0.018, pan)
    b = t0 + 0.9   # the burst: a soft boom and a crackle
    tb = tt(1.2)
    put(b, (np.sin(2 * np.pi * np.cumsum(55 * np.exp(-tb * 2) + 32) / SR) * np.exp(-tb / 0.35) + 0.5 * low(noise(1.2), 900) * np.exp(-tb / 0.12)) * 0.32, pan * 0.5)
    for _ in range(40):
        tc = tt(0.02)
        put(b + 0.15 + rng.uniform(0, 1.4) ** 1.5, band(noise(0.02), 3000, 9000) * np.exp(-tc / 0.004) * rng.uniform(0.03, 0.09), rng.uniform(-0.9, 0.9))


# ---- the tune: 8 bars, (midi, beats); chords as the harp's arpeggio notes and the bass
A = [[(84, 1), (81, .5), (84, .5), (89, 1)], [(88, 1.5), (86, .5), (81, 1)], [(86, 1), (84, .5), (82, .5), (86, 1)], [(84, 2), (79, 1)],
     [(81, 1), (84, .5), (89, .5), (93, 1)], [(91, 1.5), (89, .5), (88, 1)], [(86, 1), (84, 1), (88, 1)], [(89, 3)]]
CH = {"F": [53, 60, 65, 69], "Dm": [50, 57, 62, 65], "Bb": [46, 53, 58, 62], "C": [48, 55, 60, 64], "Am": [45, 52, 57, 60]}
CA = ["F", "Dm", "Bb", "C", "F", "Am", "Bb", "F"]


def melody(at, bar, amp=0.16, octave=0):
    b = at
    for m, n in bar:
        put(b, music_box(m + octave, amp), rng.uniform(-0.25, 0.25))
        b += n * BEAT


def waltz_box(at, ch):   # the music box's own accompaniment: a low note, then two chord notes
    c = CH[ch]
    put(at, music_box(c[0] + 12, 0.08), -0.3)
    put(at + BEAT, music_box(c[2] + 12, 0.05), 0.3)
    put(at + 2 * BEAT, music_box(c[3] + 12, 0.05), 0.3)


def harp_bar(at, ch, amp=0.075, chords2=None):
    c = CH[ch]
    seq = [c[0] + 12, c[1] + 12, c[2] + 12, c[3] + 12, c[2] + 12, c[1] + 12]
    if chords2:   # two chords in the bar (the Bb | C bar)
        c2 = CH[chords2]
        seq = [c[0] + 12, c[1] + 12, c[2] + 12, c2[0] + 12, c2[1] + 12, c2[2] + 12]
    for i, m in enumerate(seq):
        put(at + i * BEAT / 2, harp(m, amp), -0.5 + (i % 3) * 0.3)


def bar_at(k):
    return BAR0 + BAR * (k - 1)


# 0 - 1.5 s: a shimmer in the dark
put(0.0, pad(CH["F"][1:], 1.6, 0.012))
glitter(0.3, 1.2, 10, 0.025)
# bars 1 - 4: the music box alone, the book opens
for k in range(4):
    at = bar_at(k + 1)
    melody(at, A[k], 0.15)
    waltz_box(at, CA[k] if k != 3 else "C")
put(bar_at(1), pad(CH["F"][1:], 4 * BAR, 0.012))
# bars 5 - 12: into the book; the harp and the strings join
for k in range(8):
    at = bar_at(k + 5)
    melody(at, A[k], 0.16)
    melody(at, A[k], 0.05, -12)
    ch = CA[k]
    harp_bar(at, "Bb" if k == 6 else ch, chords2="C" if k == 6 else None)
    put(at, bass(CH["Bb" if k == 6 else ch][0]))
    put(at, pad([m + 12 for m in CH["Bb" if k == 6 else ch][1:]], BAR, 0.016 + 0.002 * k))
# bars 13 - 16: dusk, the castle, fireworks: fuller, the tune an octave up
for i, (k, ch, ch2) in enumerate([(4, "F", None), (5, "Am", None), (2, "Bb", None), (6, "Bb", "C")]):
    at = bar_at(13 + i)
    melody(at, A[k], 0.15)
    melody(at, A[k], 0.08, -12)
    harp_bar(at, ch, 0.09, ch2)
    put(at, bass(CH[ch][0], 0.15))
    put(at, pad([m + 12 for m in CH[ch][1:]] + [CH[ch][1] + 24], BAR, 0.026))
# bar 17: the match cut, back on the desk: a quiet F, the music box only
at = bar_at(17)
for i, m in enumerate([77, 81, 84, 89, 84, 81]):
    put(at + i * BEAT / 2, music_box(m, 0.07), -0.4 + 0.16 * i)
put(at, pad(CH["F"][1:], BAR, 0.014))
# 44.0 - 45.7: Bb, then C held while the book closes; 45.7: the last chord
put(44.0, music_box(86, 0.12)); put(44.0, harp(58, 0.07)); put(44.0, pad(CH["Bb"][1:], 0.85, 0.016))
put(44.85, music_box(84, 0.12)); put(44.85, harp(60, 0.07)); put(44.85, pad(CH["C"][1:], 0.85, 0.016))
END = 45.7
for i, m in enumerate([65, 69, 72, 77, 81, 84, 89]):
    put(END + i * 0.06, music_box(m + 12, 0.1 if i < 6 else 0.16), -0.5 + i / 6)
put(END, bass(41, 0.18)); put(END, pad([65, 69, 72, 77], 4.0, 0.024))
glitter(END + 0.2, 2.0, 16, 0.03)

# ---- the sounds of the film
put(2.0, thud(0.35))                                                    # the book lands on the desk
for t in (3.54, 3.82, 4.10):
    put(t, swish(), rng.uniform(-0.3, 0.3))                              # pages turn
glitter(4.65, 1.4, 24, 0.04)                                            # the pop-ups stand
glitter(5.6, 0.9, 30, 0.05); gliss(5.6, 0.5, 84, 101, 0.05)            # the burst at the castle
glitter(6.45, 0.9, 20, 0.04)                                            # the gold fountain
whoosh(9.4, 2.1, 0.25); gliss(10.5, 1.0, 72, 101, 0.07)                 # the dive
glitter(11.5, 1.5, 36, 0.05)                                            # the white-out: inside the book
rumble(21.4, 3.5)                                                       # the volcano
gliss(30.9, 0.9, 77, 96, 0.06); glitter(31.9, 1.2, 30, 0.05)            # the castle stands
FW = [35.2, 35.9, 36.5, 37.0, 37.4, 37.9, 38.3, 38.7, 39.0, 39.25, 39.5, 39.7, 40.0]
for i, t0 in enumerate(FW):
    firework(t0, [-0.5, 0.4, 0, -0.6, 0.6, -0.2, 0.3][i % 7])
whoosh(40.2, 0.8, 0.12); gliss(40.3, 0.7, 84, 108, 0.05)                # the cream flash, the match cut
for t in (43.0, 43.5, 44.0):
    put(t, swish(0.3, 0.07))                                            # the pop-ups fold down
put(END, thud(0.45))                                                    # the book closes

# ---- a room: convolve with a decaying noise tail, one per side
ir_t = tt(2.6)
wet = np.zeros_like(mix)
for ch in range(2):
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.55)
    ir = low(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet[ch] = fftconvolve(mix[ch], ir)[: mix.shape[1]]
out = mix + 0.32 * wet
out = out[:, : int(SR * DUR)]
t = np.arange(out.shape[1]) / SR
out *= np.clip((DUR - t) / 0.8, 0, 1)   # the last fade with the picture
out /= np.max(np.abs(out)) / 0.89

OUT.parent.mkdir(parents=True, exist_ok=True)
pcm = (np.clip(out.T, -1, 1) * 32767).astype("<i2").tobytes()
import imageio_ffmpeg  # noqa: E402

subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(OUT)], input=pcm, check=True)
print(OUT)
