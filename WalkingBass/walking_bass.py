#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2026 asc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Contour-based jazz walking bass generator -> Standard MIDI File.

Implements the algorithm of:
  R. Dias & C. Guedes, "A Contour-Based Jazz Walking Bass Generator",
  Proc. Sound and Music Computing Conference (SMC), Stockholm, 2013.

Paper rules implemented (section numbers refer to the paper)
-------------------------------------------------------------
2.1 Target note   : the last note of each phrase is the ROOT of the NEXT chord
                    (100% fundamental, as in the paper). Which octave is picked
                    is set by a DIRECTION parameter:
                    lowest | down | nearest | up | highest
                    (can be fixed manually or chosen automatically).
2.2 Trajectory    : one bar of 4/4 in quarter notes = 5 notes, the 5th being the
                    first note of the next bar (the target). The 3 middle notes
                    are computed from strongest to weakest beat: beat 3, then
                    beat 2, then beat 4.
                    - strong beat (3)  -> chord tone
                    - weak beats (2,4) -> scale notes used as passing notes
                    - last beat (4)    -> may be a chromatic approach to target
                    An OPENNESS parameter sets how direct (closed) or wide (open)
                    the path is.
2.3 Ornaments     : eighth-note-triplet / swung-eighth anticipations, set by a
                    single probability. A note is anticipated by one triplet
                    with the same or another pitch.

Additions requested for this project (NOT in the paper)
-------------------------------------------------------
* Loopable: the target of the last bar is forced to the first note of bar 1,
  and the MIDI end-of-track marker sits exactly at the end of the last bar.
* Swing = the randomness source: the ornament probability, a random swing
  ratio per anticipation, plus small timing/velocity humanization.
  Use --seed for repeatable output.
* Ballad feel: slow tempo, legato gate, soft dynamics, and an optional
  "two-feel" bar (notes on beats 1 and 3 only) chosen with --two-feel.
  Two-feel is a common ballad device but is my extension, not the paper's.

Where the paper is vague I made the interpretation choices marked
"INTERPRETATION" below.

Usage:  python walking_bass.py --show
        python walking_bass.py --seed 7 --bpm 60 --choruses 4 --out take.mid
"""
import argparse
import random
import struct
import sys
from collections import namedtuple

PPQ = 480
BEATS_PER_BAR = 4
NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# --------------------------------------------------------------------------
# Chords
# --------------------------------------------------------------------------
Chord = namedtuple("Chord", "name root tones scale")
_Q = {}


def _add(names, tones, scale):
    for n in names:
        _Q[n] = (tones, scale)


IONIAN = (0, 2, 4, 5, 7, 9, 11)
DORIAN = (0, 2, 3, 5, 7, 9, 10)
MIXO = (0, 2, 4, 5, 7, 9, 10)
LOCRIAN = (0, 1, 3, 5, 6, 8, 10)
WHOLE_HALF = (0, 2, 3, 5, 6, 8, 9, 11)

_add(["maj7", "M7", "maj", "", "maj9"], (0, 4, 7, 11), IONIAN)
_add(["6"], (0, 4, 7, 9), IONIAN)
_add(["m7", "min7", "-7", "m", "m9", "m11"], (0, 3, 7, 10), DORIAN)
_add(["m6"], (0, 3, 7, 9), DORIAN)
_add(["7", "9", "13", "dom7"], (0, 4, 7, 10), MIXO)
_add(["m7b5", "ø", "ø7"], (0, 3, 6, 10), LOCRIAN)
_add(["dim7", "o7", "dim"], (0, 3, 6, 9), WHOLE_HALF)


def parse_chord(sym):
    root = LETTERS[sym[0].upper()]
    i = 1
    while i < len(sym) and sym[i] in "#b" and not (sym[i] == "b" and sym[i:] == "b5"):
        root += 1 if sym[i] == "#" else -1
        i += 1
    suffix = sym[i:]
    if suffix not in _Q:
        raise ValueError(f"Unsupported chord quality '{suffix}' in '{sym}'")
    tones, scale = _Q[suffix]
    root %= 12
    return Chord(sym, root,
                 {(root + t) % 12 for t in tones},
                 {(root + s) % 12 for s in scale})


def note_name(p):
    return f"{NOTE_NAMES[p % 12]}{p // 12 - 1}"  # MIDI 60 = C4


# --------------------------------------------------------------------------
# 2.1 Target note
# --------------------------------------------------------------------------
def auto_direction(cur, lo, hi, rng):
    """Automatic direction: biased to move back toward the middle of the range."""
    pos = (cur - lo) / float(hi - lo)
    w = {
        "nearest": 0.35,
        "up": 0.15 + 0.35 * (1 - pos),
        "down": 0.15 + 0.35 * pos,
        "lowest": 0.10 * pos ** 2,
        "highest": 0.05 * (1 - pos) ** 2,
    }
    return rng.choices(list(w), weights=list(w.values()))[0]


def pick_target(cur, root_pc, direction, lo, hi, rng):
    cands = [p for p in range(lo, hi + 1) if p % 12 == root_pc]
    if direction == "lowest":
        return cands[0]
    if direction == "highest":
        return cands[-1]
    if direction == "up":
        above = [p for p in cands if p > cur]
        if above:
            return min(above)
    if direction == "down":
        below = [p for p in cands if p < cur]
        if below:
            return max(below)
    # nearest (and fallback when up/down has no room)
    best = min(abs(p - cur) for p in cands)
    return rng.choice([p for p in cands if abs(p - cur) == best])


# --------------------------------------------------------------------------
# 2.2 Trajectory
# --------------------------------------------------------------------------
OPEN_REACH = 10  # INTERPRETATION: semitones beat 3 may stray from the midpoint at openness=1


def _pool(pcs, lo, hi):
    return [p for p in range(lo, hi + 1) if p % 12 in pcs]


def _passing(a, b, pool, exclude, openness, rng, from_end=False):
    """Pick a scale-note passing tone between a and b (stepwise when closed,
    wider skips when open). INTERPRETATION of 'scale notes as passing notes'."""
    d = b - a
    sgn = 1 if d > 0 else -1
    if abs(d) <= 1:
        ideal = (b if from_end else a) + rng.choice((-2, 2))
    else:
        step = min(2 + openness * 5, abs(d) - 1)
        ideal = b - sgn * step if from_end else a + sgn * step
    cands = [p for p in pool if p not in exclude] or pool
    return min(cands, key=lambda p: abs(p - ideal) + rng.uniform(0, 1.2))


def build_trajectory(s, t, chord, openness, cfg, rng):
    """Return notes for beats 1..4; beat 5 is the target t.
    Computed strongest -> weakest beat: 3, then 2, then 4."""
    tones = _pool(chord.tones, cfg.low, cfg.high)
    scale = _pool(chord.scale, cfg.low, cfg.high)

    # Beat 3 (strongest middle beat): chord tone. Closed = near the midpoint of
    # the straight path; open = pushed away from it, a wider chord-tone leap.
    ideal3 = (s + t) / 2.0 + rng.choice((-1, 1)) * openness * OPEN_REACH
    cands = [p for p in tones if p not in (s, t)] or tones
    b3 = min(cands, key=lambda p: abs(p - ideal3) + rng.uniform(0, 2.5))

    # Beat 2: scale passing note between beat 1 and beat 3.
    b2 = _passing(s, b3, scale, {s, b3}, openness, rng)

    # Beat 4: chromatic approach to the target, or a scale passing note.
    b4 = None
    if rng.random() < cfg.chromatic:
        side = 1 if b3 > t else (-1 if b3 < t else rng.choice((-1, 1)))
        c = t + side
        if cfg.low <= c <= cfg.high and c != b3:
            b4 = c
    if b4 is None:
        b4 = _passing(b3, t, scale, {b3, t}, openness, rng, from_end=True)
    return [s, b2, b3, b4]


Bar = namedtuple("Bar", "chord line target direction openness two_feel")


def generate_chorus(chords, start_note, cfg, rng):
    bars = []
    cur = start_note
    n = len(chords)
    for i, ch in enumerate(chords):
        nxt = chords[(i + 1) % n]
        if i == n - 1:
            target, direction = start_note, "loop"   # closes the loop
        else:
            direction = (cfg.direction if cfg.direction != "auto"
                         else auto_direction(cur, cfg.low, cfg.high, rng))
            target = pick_target(cur, nxt.root, direction, cfg.low, cfg.high, rng)
        o = min(1.0, max(0.0, cfg.openness + rng.uniform(-cfg.openness_jitter,
                                                         cfg.openness_jitter)))
        line = build_trajectory(cur, target, ch, o, cfg, rng)
        two_feel = rng.random() < cfg.two_feel
        bars.append(Bar(ch, line, target, direction, o, two_feel))
        cur = target
    return bars


# --------------------------------------------------------------------------
# 2.3 Ornaments (triplet / swing anticipations) + rhythm rendering
# --------------------------------------------------------------------------
Note = namedtuple("Note", "start end pitch vel kind")  # start/end in beats


def render(bars, cfg, rng, first_bar_index):
    notes = []
    accents = [8, 0, 4, -2]
    for bi, bar in enumerate(bars):
        t0 = (first_bar_index + bi) * BEATS_PER_BAR
        full = bar.line + [bar.target]
        if bar.two_feel:
            slots = [(0, 2.0), (2, 2.0)]
            pickup_ks = [2, 4]
        else:
            slots = [(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0)]
            pickup_ks = [1, 2, 3, 4]
        bar_notes = []
        for idx, length in slots:
            vel = cfg.velocity + accents[idx] + rng.randint(-cfg.vel_jitter, cfg.vel_jitter)
            bar_notes.append(Note(t0 + idx, t0 + idx + length * cfg.gate,
                                  full[idx], vel, "walk"))

        # Anticipation by one triplet eighth ("swing" ornament, paper 2.3).
        for k in pickup_ks:
            if rng.random() >= cfg.swing:
                continue
            ratio = rng.uniform(0.62, 0.72)               # swing ratio ~ 2:1 triplet feel
            when = t0 + (k - 1) + ratio
            anticipated = full[k]
            if rng.random() < cfg.same_pitch:
                p = anticipated                            # same pitch
            else:                                          # another pitch: chromatic neighbour
                p = anticipated - 1 if anticipated - 1 >= cfg.low else anticipated + 1
            vel = max(1, cfg.velocity - 12 + rng.randint(-cfg.vel_jitter, cfg.vel_jitter))
            end = when + (1 - ratio) * 0.85
            bar_notes.append(Note(when, end, p, vel, "swing"))
        notes.extend(bar_notes)
    return notes


# --------------------------------------------------------------------------
# MIDI output
# --------------------------------------------------------------------------
def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def meta(kind, data):
    return bytes([0xFF, kind]) + vlq(len(data)) + data


def write_midi(path, notes, bar_chords, cfg, rng):
    ms_to_ticks = cfg.bpm * PPQ / 60000.0
    loop_ticks = len(bar_chords) * BEATS_PER_BAR * PPQ

    # Humanize start times, then enforce monophony (bass = single voice).
    ticks = []
    for n in notes:
        j = rng.uniform(-cfg.humanize_ms, cfg.humanize_ms) * ms_to_ticks
        s = max(0, int(round(n.start * PPQ + j)))
        e = int(round(n.end * PPQ))
        ticks.append([s, max(e, s + 20), n.pitch, n.vel])
    ticks.sort()
    for i, t in enumerate(ticks):
        limit = (ticks[i + 1][0] - 4) if i + 1 < len(ticks) else loop_ticks - 1
        t[1] = max(t[0] + 10, min(t[1], limit, loop_ticks - 1))

    ev = [
        (0, 0, meta(0x03, b"Walking Bass")),
        (0, 0, meta(0x51, round(60_000_000 / cfg.bpm).to_bytes(3, "big"))),
        (0, 0, meta(0x58, bytes([4, 2, 24, 8]))),
        (0, 0, bytes([0xC0, cfg.program])),
    ]
    for i, name in enumerate(bar_chords):
        ev.append((i * BEATS_PER_BAR * PPQ, 0, meta(0x06, name.encode())))
    for s, e, p, v in ticks:
        ev.append((s, 2, bytes([0x90, p, max(1, min(127, v))])))
        ev.append((e, 1, bytes([0x80, p, 0])))
    ev.sort(key=lambda x: (x[0], x[1]))

    body, last = bytearray(), 0
    for tick, _, data in ev:
        body += vlq(tick - last) + data
        last = tick
    body += vlq(max(0, loop_ticks - last)) + meta(0x2F, b"")   # end exactly at loop point

    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ))
        f.write(b"MTrk" + struct.pack(">I", len(body)) + bytes(body))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--progression",
                    default="Fmaj7 Dm7 Gm7 C7 Am7 D7 Gm7 C7",
                    help="one chord per bar, space separated (loops back to the first)")
    ap.add_argument("--bpm", type=int, default=66)
    ap.add_argument("--choruses", type=int, default=1,
                    help="number of freshly generated passes of the progression in the file")
    ap.add_argument("--seed", type=int, default=None, help="repeatable output")
    ap.add_argument("--direction", default="auto",
                    choices=["auto", "lowest", "down", "nearest", "up", "highest"])
    ap.add_argument("--openness", type=float, default=0.35, help="0 = direct, 1 = very open")
    ap.add_argument("--openness-jitter", type=float, default=0.15)
    ap.add_argument("--chromatic", type=float, default=0.5,
                    help="probability beat 4 is a chromatic approach to the target")
    ap.add_argument("--swing", type=float, default=0.35,
                    help="probability of a triplet/swing anticipation (the randomness knob)")
    ap.add_argument("--same-pitch", type=float, default=0.6,
                    help="probability an anticipation repeats the pitch it anticipates")
    ap.add_argument("--two-feel", type=float, default=0.2,
                    help="probability of a half-note 'two-feel' bar (extension, ballad)")
    ap.add_argument("--low", type=int, default=28, help="lowest MIDI note (E1)")
    ap.add_argument("--high", type=int, default=55, help="highest MIDI note (G3; paper uses up to 67)")
    ap.add_argument("--velocity", type=int, default=76)
    ap.add_argument("--vel-jitter", type=int, default=5)
    ap.add_argument("--humanize-ms", type=float, default=10.0)
    ap.add_argument("--gate", type=float, default=0.92, help="legato amount")
    ap.add_argument("--program", type=int, default=32,
                    help="GM program: 32 acoustic bass, 33 electric finger bass")
    ap.add_argument("--out", default="walking_bass_ballad.mid")
    ap.add_argument("--show", action="store_true", help="print the generated line")
    cfg = ap.parse_args()

    if cfg.seed is None:
        cfg.seed = random.SystemRandom().randrange(1_000_000)
    rng = random.Random(cfg.seed)
    chords = [parse_chord(c) for c in cfg.progression.split()]

    # First note: root of chord 1 near the lower-middle of the range.
    root_notes = _pool({chords[0].root}, cfg.low, cfg.high)
    aim = cfg.low + 0.3 * (cfg.high - cfg.low)
    start_note = min(root_notes, key=lambda p: abs(p - aim))

    all_notes, bar_names, bar_no = [], [], 0
    for c in range(cfg.choruses):
        bars = generate_chorus(chords, start_note, cfg, rng)
        all_notes += render(bars, cfg, rng, bar_no)
        bar_no += len(bars)
        bar_names += [b.chord.name for b in bars]
        if cfg.show:
            print(f"--- chorus {c + 1} ---")
            for b in bars:
                line = " ".join(note_name(p) for p in b.line)
                tag = " [two-feel]" if b.two_feel else ""
                print(f"{b.chord.name:7s} {line} -> {note_name(b.target)}"
                      f"   (dir={b.direction}, open={b.openness:.2f}){tag}")

    write_midi(cfg.out, all_notes, bar_names, cfg, rng)
    n_sw = sum(1 for n in all_notes if n.kind == "swing")
    print(f"Wrote {cfg.out}: {bar_no} bars @ {cfg.bpm} BPM, {len(all_notes)} notes "
          f"({n_sw} swing anticipations), seed={cfg.seed}")


if __name__ == "__main__":
    sys.exit(main())
