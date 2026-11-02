#!/usr/bin/env python3
"""Writes the 35 sampled effects (sfx_<id>.wav) and preview.wav of the clean sound set.

Spec: docs/clean_pack/sounds.md section 4.  Run from anywhere:  python make_sounds.py [id ...]
Python 3 + numpy + the standard wave module.  Deterministic: every effect has its own
RandomState seeded from its id, so the files are the same on every run.

Method (all of it our own synthesis): every effect is built at 8 x 5,576 = 44,608 Hz from
sine oscillators, harmonic "voices" shaped by moving formants, filtered noise, damped
resonances and little physical-ish models (drops, knocks, rattles).  The result is
low-passed with a long windowed-sinc FIR (-6 dB at 2.45 kHz, stopband from ~2.65 kHz),
decimated by 8, given a soft start/end so the first and last 8 samples are almost zero,
and scaled to the table's peak.  The frame counts equal the table's.
"""
import os
import sys
import wave

import numpy as np

FS_OUT = 5576
OS = 8
FS = FS_OUT * OS
TWO_PI = 2.0 * np.pi
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------------------------
# generic helpers (all at the oversampled rate FS)
# ----------------------------------------------------------------------------------------
def T(n):
    """Time axis (s) of an effect of n output frames."""
    return np.arange(n * OS) / FS


def phase(f):
    """Phase (radians) of an oscillator whose frequency curve is f (Hz)."""
    return TWO_PI * np.cumsum(f) / FS


def rc(t, a, b, fa, fb=None):
    """Raised-cosine window: 0 before a, rises over fa, 1, falls over fb to b, 0 after."""
    if fb is None:
        fb = fa
    up = np.clip((t - a) / fa, 0.0, 1.0)
    dn = np.clip((b - t) / fb, 0.0, 1.0)
    return np.sin(0.5 * np.pi * up) ** 2 * np.sin(0.5 * np.pi * dn) ** 2


def expd(t, t0, tau):
    """exp(-(t-t0)/tau) from t0 on, 0 before."""
    return np.where(t >= t0, np.exp(-np.maximum(t - t0, 0.0) / tau), 0.0)


def lpnoise(R, t, rate):
    """Smooth random curve (unit-ish variance), new random value `rate` times a second."""
    m = int(t[-1] * rate) + 3
    c = R.randn(m)
    return np.interp(t, np.arange(m) / rate, c)


def bandpass(x, lo, hi, order=2):
    """Zero-phase Butterworth-shaped band-pass by FFT (lo or hi may be None)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    m = np.ones_like(f)
    if hi:
        m = m / np.sqrt(1.0 + (f / hi) ** (2 * order))
    if lo:
        m = m / np.sqrt(1.0 + (lo / np.maximum(f, 1e-9)) ** (2 * order))
    return np.fft.irfft(X * m, len(x))


def nz(x):
    """Scale to unit standard deviation."""
    return x / (np.std(x) + 1e-12)


def svf_bp(x, fc, q):
    """State-variable band-pass with a moving centre frequency (Hz, array or float)."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    F = (2.0 * np.sin(np.pi * np.minimum(fc, FS / 6.5) / FS)).tolist()
    qi = 1.0 / q
    xl = x.tolist()
    out = [0.0] * len(xl)
    low = 0.0
    band = 0.0
    for i in range(len(xl)):
        low += F[i] * band
        high = xl[i] - low - qi * band
        band += F[i] * high
        out[i] = band
    return np.array(out)


def add_blip(out, t0, f0, f1, tf, tau, amp, h2=0.0, att=0.002):
    """A droplet/bubble: a sine gliding from f0 to f1 (time constant tf), damped by tau."""
    i0 = int(t0 * FS)
    L = int(min(tau * 8.0 + att * 4.0, 0.3) * FS)
    i1 = min(len(out), i0 + L)
    if i1 <= i0:
        return
    tl = np.arange(i1 - i0) / FS
    f = f1 + (f0 - f1) * np.exp(-tl / tf)
    ph = phase(f)
    s = np.sin(ph) + h2 * np.sin(2 * ph)
    e = (1.0 - np.exp(-tl / att)) * np.exp(-tl / tau)
    out[i0:i1] += amp * s * e


def add_knock(out, t0, f, tau, amp, fdrop=0.0, tdrop=0.02):
    """A damped sine (a knock, a wooden resonance)."""
    i0 = int(t0 * FS)
    L = int(min(tau * 8.0, 0.4) * FS)
    i1 = min(len(out), i0 + L)
    if i1 <= i0:
        return
    tl = np.arange(i1 - i0) / FS
    ff = f * (1.0 - fdrop * np.exp(-tl / tdrop))
    out[i0:i1] += amp * np.sin(phase(ff)) * np.exp(-tl / tau)


def voice(f0, forms, slope=1.0, sub=0.0, fmax=2300.0, floor=0.04):
    """Harmonic source shaped by formants.
    f0: fundamental curve (Hz); forms: [(F, bandwidth, gain)] with F a number or a curve;
    slope: source tilt (amplitude k**-slope); sub: level of the half-integer partials
    (a period-doubling growl)."""
    ph = phase(f0)
    out = np.zeros_like(f0)
    kmax = int(fmax / max(float(f0.min()), 1.0))
    ks = [float(k) for k in range(1, kmax + 1)]
    if sub > 0:
        ks = [0.5 * j for j in range(1, 2 * kmax + 1)]
    for k in ks:
        fk = k * f0
        if fk.min() > fmax + 250:
            continue
        res = floor
        for (F, B, g) in forms:
            res = res + g / (1.0 + ((fk - F) / (0.5 * B)) ** 2)
        a = (k ** -slope) * res * np.clip((fmax + 250 - fk) / 250.0, 0.0, 1.0)
        if sub > 0 and abs(k - round(k)) > 0.1:
            a = a * sub
        out += a * np.sin(k * ph)
    return out


# ----------------------------------------------------------------------------------------
# the effects.  Each returns a float array of n*OS samples (any scale; it is normalised)
# ----------------------------------------------------------------------------------------
def fx1(R, n):
    """Two short, low, soft-edged buzzes, the second a little lower: 'nope'."""
    t = T(n)
    out = np.zeros_like(t)
    for (t0, dur, f) in [(0.004, 0.058, 150.0), (0.072, 0.060, 108.0)]:
        fr = f * (1.0 - 0.10 * np.clip((t - t0) / dur, 0, 1))
        ph = phase(fr)
        s = sum(np.sin(k * ph) / k ** 1.2 for k in range(1, 8))
        out += s * rc(t, t0, t0 + dur, 0.014)
    return out


def fx2(R, n):
    """Friendly bright rising two-note beep (a fifth up)."""
    t = T(n)
    out = np.zeros_like(t)
    for (t0, t1, f, a) in [(0.008, 0.150, 587.3, 0.85), (0.150, 0.298, 880.0, 1.0)]:
        ph = phase(np.full_like(t, f))
        s = np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
        e = rc(t, t0, t1 + 0.012, 0.005, 0.03) * np.exp(-np.maximum(t - t0, 0) / 0.16)
        out += a * s * e
    return out


def fx4(R, n):
    """One short bright beep."""
    t = T(n)
    D = t[-1]
    ph = phase(np.full_like(t, 988.0))
    s = np.sin(ph) + 0.18 * np.sin(2 * ph)
    return s * rc(t, 0.0, D, 0.004, 0.07)


def fx5(R, n):
    """One medium beep with a slight warble."""
    t = T(n)
    D = t[-1]
    f = 587.0 * (1.0 + 0.035 * np.sin(TWO_PI * 6.5 * t))
    ph = phase(f)
    s = np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.10 * np.sin(3 * ph)
    return s * rc(t, 0.0, D, 0.02, 0.14)


def fx6(R, n):
    """A very short high pip with a little ring."""
    t = T(n)
    D = t[-1]
    ph = phase(np.full_like(t, 1320.0))
    s = np.sin(ph) + 0.08 * np.sin(2 * ph)
    return s * np.exp(-t / 0.032) * rc(t, 0.0, D, 0.002, 0.04)


def fx7(R, n):
    """A whistled bird call: two quick chirps and a longer trilled one, each up and down."""
    t = T(n)
    out = np.zeros_like(t)
    chirps = [(0.045, 0.17, 700.0, 1250.0, 0.0), (0.275, 0.17, 750.0, 1300.0, 0.0),
              (0.505, 0.34, 650.0, 1180.0, 1.0)]
    for (t0, dur, fa, fb, trill) in chirps:
        u = np.clip((t - t0) / dur, 0.0, 1.0)
        f = fa + (fb - fa) * np.sin(np.pi * u ** 0.75)
        if trill:
            f = f + 45.0 * np.sin(TWO_PI * 26.0 * t) * np.sin(np.pi * u)
        ph = phase(f)
        s = np.sin(ph) + 0.12 * np.sin(2 * ph)
        out += s * rc(t, t0, t0 + dur, 0.03)
    return out


def fx8(R, n):
    """A synthetic horn chord (D major add 9) that swells and fades."""
    t = T(n)
    D = t[-1]
    swell = rc(t, 0.0, D, 0.65, 1.5)
    bright = 450.0 + 950.0 * swell
    out = np.zeros_like(t)
    vib = 1.0 + 0.004 * np.sin(TWO_PI * 5.2 * t) * np.clip(t / 0.6, 0, 1)
    for (f, det, a) in [(146.8, 1.0, 1.0), (220.0, 1.004, 0.9), (293.7, 0.997, 0.8),
                        (370.0, 1.003, 0.6), (440.0, 0.998, 0.4)]:
        ph = phase(f * det * vib)
        for k in range(1, int(2300 / f) + 1):
            amp = k ** -1.0 / (1.0 + (k * f / bright) ** 4)
            out += a * amp * np.sin(k * ph + 0.7 * k)
    return out * swell


def fx10(R, n):
    """Comic rubbery descending gurgle with a clean attack (works at 10x speed too)."""
    t = T(n)
    D = t[-1]
    f = 150.0 + 950.0 * np.exp(-t / 0.115)
    f = f * (1.0 + 0.07 * np.sin(TWO_PI * 22.0 * t)) \
        * (1.0 + 0.10 * np.exp(-t / 0.06) * np.sin(TWO_PI * 31.0 * t))
    ph = phase(f)
    s = np.sin(ph) + 0.45 * np.sin(2 * ph + 0.5) + 0.2 * np.sin(3 * ph + 1.0)
    gur = 0.62 + 0.38 * np.sin(phase(26.0 - 10.0 * t / D) + 1.0)
    env = (1.0 - 0.45 * t / D) * rc(t, 0.0, D, 0.001, 0.12)
    crack = nz(bandpass(R.randn(len(t)), 500.0, 2300.0)) * expd(t, 0.0, 0.004)
    return 1.0 * s * gur * env + 0.55 * crack * np.clip(t / 0.0006, 0, 1)


def fx11(R, n):
    """An insect drone: a nasal buzzing hum with a slow wobble and wing flutter."""
    t = T(n)
    D = t[-1]
    f0 = 168.0 * (1.0 + 0.03 * np.sin(TWO_PI * 4.3 * t) + 0.015 * np.sin(TWO_PI * 10.7 * t + 1.0))
    s = voice(f0, [(850.0, 500.0, 1.0), (1500.0, 600.0, 0.6)], slope=0.7, floor=0.08)
    flutter = 1.0 + 0.28 * np.sin(TWO_PI * 29.0 * t)
    wob = 0.85 + 0.15 * np.sin(TWO_PI * 1.7 * t)
    return s * flutter * wob * rc(t, 0.0, D, 0.16, 0.3)


def fx13(R, n):
    """A cat's meow: pitch rises and falls, the vowel goes mm-ee-aa-oo."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, .12, .45, .75, 1], [320, 430, 600, 480, 290])
    f0 = f0 * (1.0 + 0.012 * lpnoise(R, t, 40))
    F1 = np.interp(u, [0, .2, .5, .8, 1], [320, 480, 780, 560, 400])
    F2 = np.interp(u, [0, .2, .5, .8, 1], [1000, 1550, 1850, 1100, 800])
    s = voice(f0, [(F1, 220.0, 1.0), (F2, 320.0, 0.6)], slope=1.1)
    env = rc(t, 0.0, D, 0.05, 0.1) * np.interp(u, [0, .15, .3, 1], [0.45, 0.5, 1.0, 1.0])
    return s * env


def fx14(R, n):
    """A longer angry cat yowl: harsher, rough, with breath noise."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, .1, .35, .6, .85, 1], [260, 420, 720, 640, 420, 230])
    f0 = f0 * (1.0 + 0.03 * np.sin(TWO_PI * 6.0 * t)) * (1.0 + 0.03 * lpnoise(R, t, 70))
    F1 = np.interp(u, [0, .1, .35, .6, .85, 1], [400, 700, 900, 800, 600, 450])
    F2 = np.interp(u, [0, .1, .35, .6, .85, 1], [1100, 1500, 1700, 1300, 1000, 800])
    s = voice(f0, [(F1, 260.0, 1.0), (F2, 380.0, 0.7)], slope=0.8, sub=0.25)
    rough = 1.0 + 0.35 * np.sin(phase(np.full_like(t, 41.0))) + 0.15 * lpnoise(R, t, 60)
    env = rc(t, 0.0, D, 0.06, 0.22) * np.interp(u, [0, .2, .8, 1], [0.7, 1.0, 0.85, 0.6])
    breath = nz(bandpass(R.randn(len(t)), 700.0, 2300.0)) * 0.12 * np.std(s)
    return (s * rough + breath) * env


def fx20(R, n):
    """One small dry paw-step: a soft pad on the floor."""
    t = T(n)
    k = nz(bandpass(R.randn(len(t)), 120.0, 900.0)) * expd(t, 0.0, 0.012)
    b = np.sin(TWO_PI * 170.0 * t) * expd(t, 0.0, 0.015)
    return 0.8 * k + 0.7 * b


def fx21(R, n):
    """A short whimper, rising, trembling."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, 1], [420, 760]) * (1.0 + 0.04 * np.sin(TWO_PI * 11.0 * t))
    F1 = np.interp(u, [0, 1], [350, 450])
    F2 = np.interp(u, [0, 1], [1700, 1850])
    s = voice(f0, [(F1, 220.0, 1.0), (F2, 400.0, 0.45)], slope=1.2)
    trem = 1.0 + 0.2 * np.sin(TWO_PI * 11.0 * t + 1.0)
    return s * trem * rc(t, 0.0, D, 0.04, 0.09)


def fx22(R, n):
    """A longer whine, falling, trembling."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, .15, 1], [700, 820, 360]) * (1.0 + 0.05 * np.sin(TWO_PI * 8.0 * t))
    F1 = np.interp(u, [0, 1], [400, 550])
    F2 = np.interp(u, [0, 1], [1700, 1100])
    s = voice(f0, [(F1, 220.0, 1.0), (F2, 400.0, 0.5)], slope=1.2)
    trem = 1.0 + 0.15 * np.sin(TWO_PI * 8.0 * t + 0.5)
    return s * trem * rc(t, 0.0, D, 0.05, 0.16)


def fx23(R, n):
    """A single sharp yap: high bright onset, pitch dropping into a decaying growly tail."""
    t = T(n)
    D = t[-1]
    f0 = np.interp(t, [0, 0.03, 0.10, 0.25, D], [520, 840, 640, 420, 290])
    f0 = f0 * (1.0 + 0.02 * lpnoise(R, t, 60))
    F1 = np.interp(t, [0, 0.04, 0.2, D], [600, 900, 650, 480])
    F2 = np.interp(t, [0, 0.04, 0.2, D], [1300, 1500, 1200, 950])
    s = voice(f0, [(F1, 300.0, 1.0), (F2, 400.0, 0.7)], slope=0.9, sub=0.12)
    env = (1.0 - np.exp(-t / 0.004)) * np.exp(-t / 0.13) * rc(t, 0.0, D, 0.001, 0.2)
    burst = nz(bandpass(R.randn(len(t)), 500.0, 2300.0)) * expd(t, 0.0, 0.02) * 0.6 * np.std(s)
    return s * env + burst * (1.0 - np.exp(-t / 0.002))


def fx24(R, n):
    """A wooden door banging shut: dull crack, ringing wood, then a short rattle."""
    t = T(n)
    out = np.zeros_like(t)
    nb = R.randn(len(t))
    crack = nz(bandpass(nb, 150.0, 1500.0)) * expd(t, 0.003, 0.008) * (1 - np.exp(-t / 0.0015))
    out += 1.0 * crack
    add_knock(out, 0.002, 110.0, 0.05, 1.2, fdrop=0.3)
    for (f, a, tau) in [(210.0, 0.55, 0.045), (390.0, 0.4, 0.03), (640.0, 0.22, 0.02)]:
        add_knock(out, 0.003, f, tau, a)
    nb2 = nz(bandpass(R.randn(len(t)), 200.0, 1200.0))
    for (t0, a) in [(0.072, 0.55), (0.117, 0.40), (0.152, 0.28), (0.18, 0.18)]:
        out += a * nb2 * expd(t, t0, 0.006) * (t >= t0)
        add_knock(out, t0, 260.0, 0.014, a * 0.9)
    return out


def fx26(R, n):
    """A single water drip: a small sine bubble gliding up."""
    out = np.zeros_like(T(n))
    add_blip(out, 0.001, 600.0, 1150.0, 0.012, 0.014, 1.0, att=0.001)
    return out


def fx27(R, n):
    """A soft round liquid 'bloop': a sine rising in pitch."""
    out = np.zeros_like(T(n))
    add_blip(out, 0.002, 280.0, 680.0, 0.04, 0.05, 1.0, h2=0.15, att=0.006)
    return out


def fx28(R, n):
    """A soft small 'plop': a sine dropping in pitch."""
    t = T(n)
    out = np.zeros_like(t)
    add_blip(out, 0.001, 520.0, 170.0, 0.018, 0.02, 1.0, att=0.004)
    soft = nz(bandpass(R.randn(len(t)), 100.0, 700.0)) * expd(t, 0.002, 0.005)
    return out + 0.12 * soft


def fx29(R, n):
    """A tiny dry tick, soft at the edges."""
    t = T(n)
    k = np.sin(TWO_PI * 1050.0 * t) * expd(t, 0.0, 0.004)
    c = nz(bandpass(R.randn(len(t)), 600.0, 2200.0)) * expd(t, 0.0, 0.0015)
    return (k + 0.35 * c) * (1.0 - np.exp(-t / 0.0010))


def fx31(R, n):
    """A slow food drip followed by a few small wet bubbles."""
    t = T(n)
    out = np.zeros_like(t)
    add_blip(out, 0.004, 380.0, 780.0, 0.03, 0.04, 1.0, h2=0.1, att=0.004)
    for (t0, a, f) in [(0.095, 0.38, 620.0), (0.14, 0.28, 760.0), (0.185, 0.2, 560.0),
                       (0.225, 0.14, 700.0), (0.27, 0.1, 640.0)]:
        add_blip(out, t0, f, f * 1.7, 0.01, 0.014, a, att=0.002)
    wet = nz(bandpass(R.randn(len(t)), 300.0, 1500.0)) * expd(t, 0.02, 0.07) * rc(t, 0.02, 1.0, 0.03)
    return out + 0.09 * wet


def fx32(R, n):
    """A wet splat: a big soft impact, then many small bits landing."""
    t = T(n)
    D = t[-1]
    out = np.zeros_like(t)
    imp = nz(bandpass(R.randn(len(t)), 200.0, 1800.0)) * expd(t, 0.004, 0.05) \
        * (1.0 - np.exp(-t / 0.004))
    out += 0.9 * imp
    add_blip(out, 0.003, 300.0, 110.0, 0.05, 0.06, 0.9, att=0.004)
    times = 0.03 + 0.52 * R.rand(30) ** 1.7
    for ti in sorted(times):
        a = 0.45 * np.exp(-ti / 0.3) * (0.4 + 0.6 * R.rand())
        f = 450.0 + 1000.0 * R.rand()
        add_blip(out, ti, f, f * 1.35, 0.008, 0.006 + 0.01 * R.rand(), a, att=0.0015)
    return out


def fx33(R, n):
    """A sucking, squelching pull: a rising gurgle with irregular bubbling and a final pop."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = (110.0 + 330.0 * u ** 1.5) * (1.0 + 0.06 * lpnoise(R, t, 30))
    F1 = 300.0 + 600.0 * u
    s = voice(f0, [(F1, 300.0, 1.0), (1400.0, 600.0, 0.35)], slope=1.0, sub=0.3)
    bub = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(phase(14.0 + 30.0 * u) + 2.0 * lpnoise(R, t, 8))) ** 1.5
    nb = svf_bp(R.randn(len(t)), 400.0 + 1300.0 * u, 4.0)
    s = s / (np.std(s) + 1e-9)
    nb = nb / (np.std(nb) + 1e-9)
    out = (s + 0.5 * nb) * bub * rc(t, 0.0, D - 0.04, 0.09, 0.07)
    add_blip(out, D - 0.06, 420.0, 180.0, 0.02, 0.02, 1.6 * np.std(out), att=0.003)
    return out


def fx34(R, n):
    """A heavy, muffled human footstep: heel thud, toe slap, a low rumble."""
    t = T(n)
    out = np.zeros_like(t)
    add_blip(out, 0.0, 110.0, 52.0, 0.03, 0.075, 1.2, att=0.004)
    out += 0.7 * nz(bandpass(R.randn(len(t)), 40.0, 300.0)) * expd(t, 0.0, 0.05) * (1 - np.exp(-t / 0.004))
    t2 = 0.13
    out += 0.4 * nz(bandpass(R.randn(len(t)), 80.0, 500.0)) * expd(t, t2, 0.04) * (1 - np.exp(-np.maximum(t - t2, 0) / 0.004))
    add_blip(out, t2, 95.0, 62.0, 0.03, 0.04, 0.45, att=0.004)
    out += 0.45 * nz(bandpass(R.randn(len(t)), 50.0, 200.0)) * expd(t, 0.0, 0.14)
    return out


def fx36(R, n):
    """A low engine motor: steady rough buzz with a regular four-stroke chop, no envelope."""
    t = T(n)
    D = t[-1]
    out = np.zeros_like(t)
    period = 1.0 / 47.0
    pat = [1.0, 0.72, 0.9, 0.6]
    k = 0
    tk = 0.0
    while tk < D:
        a = pat[k % 4] * (0.9 + 0.2 * R.rand())
        add_knock(out, tk, 135.0, 0.012, a)
        add_knock(out, tk, 330.0, 0.006, 0.5 * a)
        add_knock(out, tk, 70.0, 0.02, 0.7 * a)
        k += 1
        tk = k * period * (1.0 + 0.01 * R.randn())
    saw = sum(np.sin(j * phase(np.full_like(t, 94.0))) / j for j in range(1, 11))
    chop = 0.6 + 0.4 * np.maximum(0.0, np.sin(phase(np.full_like(t, 47.0))))
    rough = nz(bandpass(R.randn(len(t)), 150.0, 1500.0)) * chop
    return nz(out) + 0.35 * nz(saw) * chop + 0.2 * rough


def fx37(R, n):
    """A crisp crunch: a handful of small cracks with a dull body under the first."""
    t = T(n)
    out = np.zeros_like(t)
    base = nz(bandpass(R.randn(len(t)), 300.0, 2300.0))
    for (t0, a, tau) in [(0.004, 1.0, 0.010), (0.034, 0.7, 0.008), (0.062, 0.85, 0.009),
                         (0.1, 0.5, 0.007), (0.133, 0.6, 0.008), (0.172, 0.4, 0.007),
                         (0.22, 0.3, 0.007), (0.27, 0.2, 0.006)]:
        out += a * np.roll(base, int(t0 * 777 + 311)) * expd(t, t0, tau) \
            * (1 - np.exp(-np.maximum(t - t0, 0) / 0.0008))
    for (t0, f, a) in [(0.004, 170.0, 0.6), (0.034, 210.0, 0.4), (0.062, 190.0, 0.5)]:
        add_knock(out, t0, f, 0.02, a)
    return out


def fx38(R, n):
    """A short low gravelly roar."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, .2, 1], [85, 95, 55]) * (1.0 + 0.08 * lpnoise(R, t, 70))
    F1 = np.interp(u, [0, .3, 1], [450, 650, 500])
    F2 = np.interp(u, [0, .3, 1], [900, 1200, 800])
    s = voice(f0, [(F1, 300.0, 1.0), (F2, 400.0, 0.6)], slope=0.8, sub=0.5)
    am = np.clip(1.0 + 0.45 * lpnoise(R, t, 45), 0.1, 2.0)
    nb = nz(bandpass(R.randn(len(t)), 100.0, 1200.0)) * 0.35 * np.std(s)
    env = rc(t, 0.0, D, 0.03, 0.14) * (1.0 - 0.3 * u)
    return (s + nb) * am * env


def fx39(R, n):
    """A longer low snarl with a slowly moving vowel and a rattly 'rrr'."""
    t = T(n)
    D = t[-1]
    u = t / D
    f0 = np.interp(u, [0, .15, .5, .8, 1], [70, 85, 62, 75, 50]) * (1.0 + 0.06 * lpnoise(R, t, 60))
    F1 = np.interp(u, [0, .3, .6, 1], [350, 650, 500, 400])
    F2 = np.interp(u, [0, .3, .6, 1], [800, 1300, 1000, 700])
    s = voice(f0, [(F1, 300.0, 1.0), (F2, 450.0, 0.55)], slope=0.8, sub=0.45)
    am = np.clip(1.0 + 0.4 * np.sin(phase(np.full_like(t, 27.0))) + 0.35 * lpnoise(R, t, 40), 0.1, 2.2)
    nb = nz(bandpass(R.randn(len(t)), 100.0, 1100.0)) * 0.3 * np.std(s)
    env = rc(t, 0.0, D, 0.2, 0.55) * (0.75 + 0.25 * np.sin(TWO_PI * 1.3 * t + 0.5))
    return (s + nb) * am * env


def fx40(R, n):
    """A short hollow pop."""
    t = T(n)
    out = np.zeros_like(t)
    add_knock(out, 0.0, 300.0, 0.007, 1.0, fdrop=0.35, tdrop=0.01)
    add_knock(out, 0.0, 640.0, 0.005, 0.25)
    return out * (1.0 - np.exp(-t / 0.0015))


def fx41(R, n):
    """Soft steady shower: hiss and random patter, fading in and out."""
    t = T(n)
    D = t[-1]
    hiss = nz(bandpass(R.randn(len(t)), 700.0, 2300.0, order=2))
    out = 0.55 * hiss
    rate = 130.0
    m = int(rate * D)
    times = R.rand(m) * (D - 0.05)
    for ti in times:
        a = 0.35 + 0.65 * R.rand()
        f = 600.0 + 1500.0 * R.rand()
        i0 = int(ti * FS)
        L = int(0.012 * FS)
        tl = np.arange(L) / FS
        d = np.sin(TWO_PI * f * tl) * np.exp(-tl / 0.0025) * (1 - np.exp(-tl / 0.0006))
        out[i0:i0 + L] += a * 1.2 * d
    swell = 0.8 + 0.2 * np.tanh(lpnoise(R, t, 1.2))
    env = rc(t, 0.0, D, 0.5, 0.7) * swell
    y = out * env
    return np.tanh(0.9 * y / (np.std(y) + 1e-9))


def fx42(R, n):
    """Comic retching: three rough heaves and a final wet gurgle."""
    t = T(n)
    D = t[-1]
    pts_t = [0, 0.02, 0.13, 0.15, 0.17, 0.30, 0.32, 0.46, 0.47, D]
    pts_f = [100, 100, 170, 170, 110, 190, 120, 210, 260, 120]
    f0 = np.interp(t, pts_t, pts_f)
    f0 = f0 * (1.0 + 0.06 * np.sin(TWO_PI * 8.0 * t) * (t > 0.47)) * (1.0 + 0.07 * lpnoise(R, t, 70))
    F1 = np.interp(t, [0, 0.15, 0.3, 0.47, 0.5, D], [450, 520, 550, 600, 800, 750])
    F2 = np.interp(t, [0, 0.15, 0.3, 0.47, 0.5, D], [1000, 1100, 1200, 1250, 1100, 1000])
    s = voice(f0, [(F1, 300.0, 1.0), (F2, 450.0, 0.55)], slope=0.8, sub=0.45)
    am = np.clip(1.0 + 0.5 * lpnoise(R, t, 60), 0.1, 2.0)
    env = (0.8 * rc(t, 0.02, 0.15, 0.03, 0.04) + 0.9 * rc(t, 0.17, 0.30, 0.03, 0.04)
           + 1.0 * rc(t, 0.32, 0.47, 0.03, 0.05) + 0.8 * rc(t, 0.47, D, 0.03, 0.12))
    heaves = env * (t < 0.47)
    nb = nz(bandpass(R.randn(len(t)), 300.0, 1800.0)) * 0.45 * np.std(s) * heaves
    out = (s * am + nb) * env
    sd = np.std(out)
    for ti in [0.50, 0.53, 0.55, 0.575, 0.59]:
        f = 400.0 + 500.0 * R.rand()
        add_blip(out, ti, f, f * 1.6, 0.01, 0.012, 0.9 * sd, att=0.002)
    return out


def fx44(R, n):
    """A short wet slurp: a sweeping bubbly suck, ending in a smack."""
    t = T(n)
    D = t[-1]
    u = t / D
    nb = svf_bp(R.randn(len(t)), 500.0 + 1500.0 * u ** 1.5, 5.0)
    nb = nb / (np.std(nb) + 1e-9)
    bub = (0.5 + 0.5 * np.sin(phase(np.full_like(t, 31.0)) + 0.5)) ** 1.5
    tone = np.sin(phase(300.0 + 650.0 * u ** 1.3))
    out = (nb * 0.8 + tone * 0.6) * (0.35 + 0.65 * bub) * rc(t, 0.0, D - 0.05, 0.04, 0.03)
    add_blip(out, D - 0.062, 800.0, 380.0, 0.012, 0.014, 1.5 * np.std(out), att=0.002)
    return out


def fx45(R, n):
    """A longer, drawn-out slurp with a gulp at the end."""
    t = T(n)
    D = t[-1]
    u = t / D
    nb = svf_bp(R.randn(len(t)), 400.0 + 1200.0 * u ** 1.4, 5.0)
    nb = nb / (np.std(nb) + 1e-9)
    bub = (0.5 + 0.5 * np.sin(phase(24.0 + 14.0 * u) + 0.5)) ** 1.5
    tone = np.sin(phase(250.0 + 550.0 * u ** 1.2))
    body = (nb * 0.8 + tone * 0.6) * (0.35 + 0.65 * bub) * rc(t, 0.0, D - 0.11, 0.06, 0.04)
    out = body
    sd = np.std(body)
    add_blip(out, D - 0.09, 230.0, 85.0, 0.035, 0.05, 2.0 * sd, h2=0.2, att=0.008)
    add_blip(out, D - 0.125, 700.0, 340.0, 0.012, 0.012, 1.1 * sd, att=0.002)
    return out


def fx47(R, n):
    """A tiny dry tap, with an even tinier bounce."""
    t = T(n)
    out = np.zeros_like(t)
    nb = nz(bandpass(R.randn(len(t)), 500.0, 2000.0))
    for (t0, a) in [(0.0, 1.0), (0.026, 0.4)]:
        out += a * (0.7 * nb * expd(t, t0, 0.002) + 0.6 * np.sin(TWO_PI * 760.0 * (t - t0)) * expd(t, t0, 0.008))
    return out * (1.0 - np.exp(-t / 0.0009))


def fx49(R, n):
    """A ripping, tearing rasp made of stick-slip pulses of noise in three rips."""
    t = T(n)
    D = t[-1]
    base = nz(bandpass(R.randn(len(t)), 350.0, 1700.0))
    g = np.abs(lpnoise(R, t, 70.0)) ** 1.0 + 0.15
    g2 = 0.55 + 0.45 * np.sin(phase(np.full_like(t, 95.0)))
    low = nz(bandpass(R.randn(len(t)), 80.0, 500.0)) * 0.4
    env = (1.0 * rc(t, 0.01, 0.18, 0.02, 0.06) * (0.5 + 0.5 * (t - 0.01) / 0.17)
           + 0.8 * rc(t, 0.2, 0.33, 0.02, 0.05)
           + 0.6 * rc(t, 0.35, D, 0.02, 0.06))
    return (base * g * g2 + low * g) * env


# id -> (tier, frames in the table, peak in the table, function)
EFFECTS = {
    1: ('A', 752, 121, fx1), 2: ('A', 1672, 127, fx2), 4: ('B', 1244, 90, fx4),
    5: ('B', 2784, 120, fx5), 6: ('B', 1040, 124, fx6), 7: ('A', 4960, 127, fx7),
    8: ('B', 12736, 128, fx8), 10: ('A', 2706, 127, fx10), 11: ('B', 6688, 127, fx11),
    13: ('A', 2016, 120, fx13), 14: ('A', 5196, 128, fx14), 20: ('B', 436, 109, fx20),
    21: ('A', 1742, 107, fx21), 22: ('A', 2874, 115, fx22), 23: ('A', 4010, 127, fx23),
    24: ('A', 1480, 122, fx24), 26: ('B', 330, 125, fx26), 27: ('A', 804, 128, fx27),
    28: ('A', 436, 127, fx28), 29: ('A', 172, 121, fx29), 31: ('B', 1812, 117, fx31),
    32: ('A', 3374, 115, fx32), 33: ('B', 3862, 110, fx33), 34: ('B', 3628, 119, fx34),
    36: ('A', 1864, 55, fx36), 37: ('A', 1888, 124, fx37), 38: ('A', 2880, 127, fx38),
    39: ('B', 11692, 128, fx39), 40: ('A', 184, 115, fx40), 41: ('A', 12896, 127, fx41),
    42: ('A', 3484, 128, fx42), 44: ('A', 1824, 125, fx44), 45: ('A', 3296, 128, fx45),
    47: ('A', 466, 110, fx47), 49: ('A', 2428, 124, fx49),
}


# ----------------------------------------------------------------------------------------
# output stage: low-pass, decimate, soft edges, scale
# ----------------------------------------------------------------------------------------
def _fir():
    ntap = 1201
    m = np.arange(ntap) - ntap // 2
    fc = 2450.0 / FS
    h = 2 * fc * np.sinc(2 * fc * m) * np.blackman(ntap)
    return h / h.sum()


_H = _fir()


def finalize(x, n, peak):
    """Low-pass, decimate by OS, soft zero edges (first/last 8 samples), scale to `peak`."""
    x = np.asarray(x, dtype=float)
    x = np.nan_to_num(x)
    y = np.convolve(x, _H, mode='same')[::OS]
    if len(y) < n:
        y = np.concatenate([y, np.zeros(n - len(y))])
    y = y[:n].copy()
    lim = 3.0 / min(peak, 127)               # first/last 8 samples stay under ~3 units
    w = np.ones(n)
    r = 6
    for i in range(8):
        w[i] = lim * i / 7.0
    for j in range(r):
        w[8 + j] = lim + (1 - lim) * 0.5 * (1 - np.cos(np.pi * (j + 1) / (r + 1)))
    w[n - 8:] = w[:8][::-1]
    w[n - 8 - r:n - 8] = w[8:8 + r][::-1]
    y *= w
    y -= 0.0
    y[0] = 0.0
    y[-1] = 0.0
    pk = np.max(np.abs(y)) + 1e-12
    y = y * (min(peak, 127) * 256.0 / pk)
    return np.clip(np.round(y), -32767, 32767).astype('<i2')


def write_wav(path, samples):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS_OUT)
        w.writeframes(samples.astype('<i2').tobytes())


def main():
    ids = [int(a) for a in sys.argv[1:]] or sorted(EFFECTS)
    rendered = {}
    print('id  tier  frames/target   peak/target   seconds')
    for i in sorted(EFFECTS):
        tier, n, pk, fn = EFFECTS[i]
        if i not in ids and len(ids) != len(EFFECTS):
            continue
        R = np.random.RandomState(1000 + i)
        s = finalize(fn(R, n), n, pk)
        write_wav(os.path.join(HERE, 'sfx_%d.wav' % i), s)
        rendered[i] = s
        p8 = int(min(127, np.max(np.abs(np.round(s / 256.0)))))
        print('%2d   %s   %6d/%-6d   %4d/%-4d (%3.0f%%)  %.3f' %
              (i, tier, len(s), n, p8, pk, 100.0 * p8 / pk, len(s) / FS_OUT))
    if len(ids) == len(EFFECTS):
        gap = np.zeros(FS_OUT // 4, dtype='<i2')
        parts = []
        for i in sorted(EFFECTS):
            parts += [rendered[i], gap]
        write_wav(os.path.join(HERE, 'preview.wav'), np.concatenate(parts))
        print('wrote preview.wav')


if __name__ == '__main__':
    main()
