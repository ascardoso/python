#!/usr/bin/env python3
"""
walking_bass.py - rule-based walking bass generator with swing + humanization.

Inspired by Seow & Wang (2026), "Walking Bass as Melodic-Formal Accompaniment:
Selected Paul Chambers Hard-Bop Blues Close Readings" (JOLLS 15(3)).

The paper is analytical, not algorithmic, so the three analytical terms are
turned into generation rules (my interpretation, not the authors' algorithm):

  * Target orientation   -> the first beat of every chord is an "anchor" chosen
                            among root/3rd/5th/7th (not always the root), with a
                            bonus for common tones shared with the previous
                            chord (the D-F-F-C over Bb7 idea in "Bags' Groove").
                            The last beat before each anchor is an approach tone.
  * Chromatic continuity -> approach tones are chromatic (+/-1, sometimes +/-2),
                            sometimes enclosure-like (approach from both sides),
                            and middle beats move by step/chord tone (Viterbi
                            search minimising a melodic cost).
  * Motivic scaling      -> each chorus picks a short contour cell (e.g. up-up-
                            down) that recurs in adapted form across bars, and a
                            registral arc rises into the 2nd half of the chorus
                            and descends again (Ex. 3, "Blue Train").

Swing is a piecewise-linear remap of the beat grid (ratio r:1). Humanization
adds laid-back downbeat delay (cf. Nelias et al. 2022), timing jitter, slow
drift, velocity and note-length variation. Output is a Standard MIDI File
written with no third-party dependencies.

Examples
  python walking_bass.py --preset bags --tempo 130 --choruses 3 --out bags.mid
  python walking_bass.py --preset straight --tempo 220 --swing 1.5 --ride
  python walking_bass.py --chords "Dm7 | G7 | Cmaj7 | A7" --choruses 4 --seed 7
  python walking_bass.py --preset bags --humanize 0 --swing 1    # robotic/straight
"""
from __future__ import annotations

import argparse
import math
import random
import re
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

PPQ = 480
NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# 12-bar forms. "bags" is the chart of Example 1 in the paper (mm. 1-12);
# "straight" follows the Milestones solo form (Example 2 covers mm. 9-12 + 1-8);
# "bluetrain" is a generic Eb blues with turnaround (NOT the paper's transcription).
PRESETS = {
    "bags": "F7 | Bb7 | F7 | F7 | Bb7 | Bb7 | F7 | Am7 D7 | Gm7 | C7 | F7 D7 | Gm7 C7",
    "straight": "F7 | Bb7 | F7 | F7 | Bb7 | Bb7 | F7 | F7 | Gm7 | C7 | F7 | F7",
    "bluetrain": "Eb7 | Ab7 | Eb7 | Eb7 | Ab7 | Ab7 | Eb7 | Eb7 C7 | Fm7 | Bb7 | Eb7 C7 | Fm7 Bb7",
}


# --------------------------------------------------------------------------- #
# Chords
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Chord:
    symbol: str
    root: int                 # pitch class
    tones: Tuple[int, ...]    # pitch classes: root, 3rd, 5th, 7th(6th)
    scale: Tuple[int, ...]    # pitch classes for passing tones


def _quality(q: str):
    if q.startswith(("maj", "M", "^", "Δ")):
        return (0, 4, 7, 11), (0, 2, 4, 5, 7, 9, 11)
    if "m7b5" in q or "ø" in q:
        return (0, 3, 6, 10), (0, 2, 3, 5, 6, 8, 10)
    if q.startswith(("dim", "o")):
        return (0, 3, 6, 9), (0, 2, 3, 5, 6, 8, 9, 11)
    if q.startswith(("m", "-")):
        if q[1:].startswith("6"):
            return (0, 3, 7, 9), (0, 2, 3, 5, 7, 9, 10)
        return (0, 3, 7, 10), (0, 2, 3, 5, 7, 9, 10)
    if q.startswith("6"):
        return (0, 4, 7, 9), (0, 2, 4, 5, 7, 9, 11)
    return (0, 4, 7, 10), (0, 2, 4, 5, 7, 9, 10)  # dominant / default


def parse_chord(sym: str) -> Chord:
    m = re.match(r"^([A-G])([b#]?)(.*)$", sym.strip())
    if not m:
        raise ValueError(f"Cannot parse chord symbol: {sym!r}")
    root = (NOTE_PC[m.group(1)] + {"b": -1, "#": 1, "": 0}[m.group(2)]) % 12
    tones, scale = _quality(m.group(3))
    return Chord(sym.strip(), root,
                 tuple((root + i) % 12 for i in tones),
                 tuple((root + i) % 12 for i in scale))


@dataclass
class Segment:
    chord: Chord
    beat: int          # absolute beat index
    length: int        # beats
    pos: int           # beat position inside the bar (0-3)
    bar: int           # bar index inside chorus
    chorus: int
    chorus_start: bool


@dataclass
class Note:
    beat: float        # absolute position on the straight grid
    dur: float         # beats on the straight grid
    pitch: int
    kind: str          # anchor | pass | approach | eighth | end


def parse_progression(text: str) -> List[List[Chord]]:
    bars: List[List[Chord]] = []
    for bar in text.split("|"):
        toks = bar.split()
        if not toks:
            continue
        chords = []
        for t in toks:
            if t == "%":
                chords.append(bars[-1][-1] if not chords else chords[-1])
            else:
                chords.append(parse_chord(t))
        bars.append(chords)
    if not bars:
        raise ValueError("Empty chord progression")
    return bars


_SPLIT = {1: [4], 2: [2, 2], 3: [2, 1, 1], 4: [1, 1, 1, 1]}


def note_name(p: int) -> str:
    return f"{NAMES[p % 12]}{p // 12 - 1}"


# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #
@dataclass
class Params:
    tempo: float = 140.0
    choruses: int = 2
    seed: Optional[int] = None
    swing: Optional[float] = None     # long:short ratio; None = tempo-dependent
    humanize: float = 1.0             # 0 = machine-exact, 1 = default, 2 = loose
    # composition
    root_bias: float = 0.55           # 0..1, how often anchors are roots
    enclosure_prob: float = 0.15      # enclosure-like approach (bars of 3+ beats)
    eighth_prob: float = 0.10         # swung eighth-note skip on inner beats
    motif_prob: float = 0.55          # chance a bar uses the chorus' contour cell
    register_center: int = 43         # MIDI pitch (43 = G2) the line orbits
    register_arc: float = 6.0         # semitones of rise toward arc_peak
    arc_peak: float = 0.65            # fraction of the chorus where arc peaks
    lo: int = 28                      # E1
    hi: int = 60                      # C4
    # performance (milliseconds at humanize=1)
    lag_ms: float = 12.0              # laid-back downbeat delay
    jitter_ms: float = 5.0
    drift_ms: float = 1.4
    approach_push_ms: float = 4.0     # approach tones lean slightly forward


def auto_swing(tempo: float) -> float:
    """Heuristic: swing ratio flattens as tempo rises (roughly 2.3:1 at 140 bpm,
    1.1:1 at 300+). Override with --swing."""
    return max(1.1, min(3.0, 2.6 - (tempo - 100.0) * 0.008))


# --------------------------------------------------------------------------- #
# Generator
# --------------------------------------------------------------------------- #
CONTOURS = [(1, 1, -1), (1, -1, 1), (-1, -1, 1), (1, 1, 1), (-1, 1, 1), (1, -1, -1)]


class WalkingBass:
    def __init__(self, bars: List[List[Chord]], params: Params):
        self.bars = bars
        self.p = params
        seed = params.seed if params.seed is not None else random.randrange(2 ** 31)
        self.seed = seed
        self.rng = random.Random(seed)          # composition
        self.prng = random.Random(seed + 1)     # performance (independent stream)
        self.ratio = params.swing if params.swing else auto_swing(params.tempo)
        self.segments = self._segments()

    # ---- structure -------------------------------------------------------- #
    def _segments(self) -> List[Segment]:
        segs, beat = [], 0
        for c in range(self.p.choruses):
            for b, chords in enumerate(self.bars):
                pos = 0
                for ch, ln in zip(chords, _SPLIT[min(len(chords), 4)]):
                    segs.append(Segment(ch, beat, ln, pos, b, c, b == 0 and pos == 0))
                    beat += ln
                    pos += ln
        return segs

    @property
    def chorus_beats(self) -> int:
        return 4 * len(self.bars)

    def _center(self, beat_abs: int) -> float:
        x = (beat_abs % self.chorus_beats) / self.chorus_beats
        bump = math.exp(-((x - self.p.arc_peak) / 0.22) ** 2)
        return self.p.register_center + self.p.register_arc * bump

    def _pitches(self, pcs, lo, hi):
        return [q for q in range(lo, hi + 1) if q % 12 in pcs]

    # ---- composition ------------------------------------------------------ #
    def compose(self) -> List[Note]:
        p, rng = self.p, self.rng
        segs = self.segments

        # 1) anchors (target orientation)
        anchors: List[int] = []
        prev_chord, prev = None, None
        for s in segs:
            a = self._pick_anchor(s, prev_chord, prev, self._center(s.beat))
            anchors.append(a)
            prev_chord, prev = s.chord, a
        roots = self._pitches((segs[0].chord.root,), p.lo, p.hi)
        end_anchor = min(roots, key=lambda q: abs(q - anchors[-1]))

        # 2) fill between anchors (chromatic continuity + motivic scaling)
        notes: List[Note] = []
        motif = None
        for i, s in enumerate(segs):
            if s.pos == 0 and s.bar == 0:
                motif = rng.choice(CONTOURS)        # new cell each chorus
            target = anchors[i + 1] if i + 1 < len(anchors) else end_anchor
            use_motif = motif if (s.length == 4 and rng.random() < p.motif_prob) else None
            notes += self._fill(s, anchors[i], target, use_motif)

        notes.append(Note(float(len(segs) and segs[-1].beat + segs[-1].length),
                          3.0, end_anchor, "end"))
        return notes

    def _pick_anchor(self, s: Segment, prev_chord: Optional[Chord],
                     prev: Optional[int], center: float) -> int:
        p, ch = self.p, s.chord
        wd = [0.3 + 2.5 * p.root_bias, 0.8, 0.8, 0.5]       # root, 3rd, 5th, 7th
        if s.length <= 2:
            wd[0] *= 1.6                                    # ii-V: clearer roots
        if s.chorus_start:
            wd[0] *= 5.0
        ref = prev if prev is not None else center
        cands, weights = [], []
        for q in self._pitches(ch.tones, p.lo, p.hi):
            deg = ch.tones.index(q % 12)
            w = wd[min(deg, 3)]
            if prev_chord and deg != 0 and (q % 12) in prev_chord.tones:
                w *= 1.8                                    # common-tone retention
            if q == prev:
                w *= 0.5
            w *= math.exp(-((q - ref) / 7.0) ** 2) * math.exp(-((q - center) / 9.0) ** 2)
            cands.append(q)
            weights.append(w + 1e-9)
        return self.rng.choices(cands, weights)[0]

    def _fill(self, s: Segment, a: int, t: int, motif) -> List[Note]:
        p, rng, ch = self.p, self.rng, s.chord
        n = s.length
        if n == 1:
            return [Note(s.beat, 1.0, a, "anchor")]
        center = self._center(s.beat)

        # candidate sets per beat
        cand: List[List[int]] = [[] for _ in range(n)]
        cand[0] = [a]
        forced = {0}
        if n >= 3 and rng.random() < p.enclosure_prob:      # enclosure-like
            if rng.random() < 0.5:
                cand[n - 2], cand[n - 1] = [t + rng.choice((1, 2))], [t - 1]
            else:
                cand[n - 2], cand[n - 1] = [t - rng.choice((1, 2))], [t + 1]
            forced |= {n - 2, n - 1}
        else:
            cand[n - 1] = [t - 1, t + 1] + ([t - 2, t + 2] if rng.random() < 0.2 else [])
            forced.add(n - 1)
        free_pcs = set(ch.tones) | set(ch.scale)
        for j in range(1, n):
            if j not in forced:
                cand[j] = self._pitches(free_pcs, max(p.lo, a - 12), min(p.hi, a + 12))
            cand[j] = [q for q in cand[j] if p.lo <= q <= p.hi] or [t - 1]

        def node(j: int, q: int) -> float:
            c = 0.5 * ((q - center) / 8.0) ** 2 + 0.05 * abs(q - t) + rng.uniform(0, 0.8)
            if j in forced:
                return c + (0.8 if abs(q - t) == 2 else 0.0)
            strong = (s.pos + j) % 4 in (0, 2)
            if q % 12 in ch.tones:
                c += 0.0 if strong else 0.3
            else:
                c += 1.5 if strong else 0.3
            return c

        def trans(x: int, y: int) -> float:
            d = abs(y - x)
            return {0: 6.0, 1: 0.0, 2: 0.0, 3: 0.4, 4: 0.4, 5: 0.9, 7: 1.1}.get(
                d, 2.0 if d == 6 else (2.2 if d < 10 else 3.0 + 0.3 * (d - 10)))

        costs = {a: 0.0}
        back: List[Dict[int, int]] = []
        for j in range(1, n):
            new, bp = {}, {}
            for q in cand[j]:
                best, arg = None, None
                for x, cx in costs.items():
                    c = cx + trans(x, q)
                    if motif and j - 1 < len(motif):
                        sgn = (q > x) - (q < x)
                        if sgn == motif[j - 1]:
                            c -= 1.2                        # contour resemblance
                    if best is None or c < best:
                        best, arg = c, x
                new[q], bp[q] = best + node(j, q), arg
            costs = new
            back.append(bp)
        end = min(costs, key=costs.get)
        path = [end]
        for bp in reversed(back):
            path.append(bp[path[-1]])
        path = path[::-1][:n]

        out = [Note(s.beat + j, 1.0, q,
                    "anchor" if j == 0 else ("approach" if j == n - 1 else "pass"))
               for j, q in enumerate(path)]

        # optional swung eighth skip: (note_j, chromatic neighbour of note_j+1)
        j = 1
        while j < n - 1:
            if rng.random() < p.eighth_prob:
                nxt = out[j + 1].pitch
                opts = [x for x in (nxt - 1, nxt + 1) if x != out[j].pitch]
                if opts:
                    out[j].dur = 0.5
                    out.insert(j + 1, Note(s.beat + j + 0.5, 0.5, rng.choice(opts), "eighth"))
                    j += 1
            j += 1
        return out

    # ---- swing + humanization -------------------------------------------- #
    def swing_map(self, x: float) -> float:
        """Piecewise-linear remap: the off-beat eighth moves from 0.5 to r/(1+r)."""
        s = self.ratio / (1.0 + self.ratio)
        whole = math.floor(x + 1e-9)
        f = x - whole
        if f <= 0.5 + 1e-9:
            return whole + f * 2 * s
        return whole + s + (f - 0.5) * 2 * (1 - s)

    def perform(self, notes: List[Note]):
        """Return [(on_tick, off_tick, pitch, velocity)] for the bass."""
        p, rng, h = self.p, self.prng, self.p.humanize
        beat_ms = 60000.0 / p.tempo
        ms2ticks = PPQ / beat_ms
        base_vel = {"anchor": 86, "pass": 80, "approach": 78, "eighth": 68, "end": 90}
        lag_w = {0: 1.0, 1: 0.6, 2: 0.9, 3: 0.5}
        drift, vwalk = 0.0, 0.0
        ev: List[List[int]] = []
        for n in sorted(notes, key=lambda z: z.beat):
            is_off = abs(n.beat - round(n.beat)) > 1e-6
            pos = int(math.floor(n.beat + 1e-9)) % 4
            on = self.swing_map(n.beat)
            off_len = self.swing_map(n.beat + n.dur) - on

            drift = 0.97 * drift + rng.gauss(0, p.drift_ms) * h
            drift = max(-25.0, min(25.0, drift))
            lag = p.lag_ms * (0.4 if is_off else lag_w[pos])
            if n.kind == "approach":
                lag -= p.approach_push_ms
            ms = h * lag + rng.gauss(0, p.jitter_ms) * h + drift
            tick = max(0, round(on * PPQ + ms * ms2ticks))

            vwalk = 0.9 * vwalk + rng.gauss(0, 2.0) * h
            vel = base_vel[n.kind] + (4 if pos == 0 and not is_off else 0)
            vel += vwalk + rng.gauss(0, 4.0) * h
            vel = int(max(30, min(120, round(vel))))

            if n.kind == "end":
                gate = 0.95
            elif n.kind == "eighth":
                gate = 0.85
            else:
                gate = 0.93 + rng.gauss(0, 0.035) * h
                if h > 0 and rng.random() < 0.05 * h:
                    gate = 0.6                              # occasional short note
                gate = max(0.55, min(1.0, gate))
            dur = max(12, round(off_len * gate * PPQ))
            ev.append([tick, tick + dur, n.pitch, vel])

        for i in range(1, len(ev)):                         # keep the line monophonic
            if ev[i][0] <= ev[i - 1][0]:
                ev[i][0] = ev[i - 1][0] + 6
                ev[i][1] = max(ev[i][1], ev[i][0] + 12)
            if ev[i - 1][1] >= ev[i][0]:
                ev[i - 1][1] = max(ev[i - 1][0] + 10, ev[i][0] - 2)
        return [tuple(e) for e in ev]

    def ride(self, total_beats: int):
        """Swung ride pattern + hi-hat on 2 and 4, for hearing the lag/swing in context."""
        p, rng, h = self.p, random.Random(self.seed + 2), self.p.humanize
        ms2ticks = PPQ * p.tempo / 60000.0
        out = []
        pat = [(0, 82), (1, 92), (1.5, 62), (2, 82), (3, 92), (3.5, 62)]
        for bar in range(total_beats // 4):
            for off, v in pat:
                t = round(self.swing_map(bar * 4 + off) * PPQ + rng.gauss(0, 3) * h * ms2ticks)
                out.append((max(0, t), max(0, t) + 100, 51, int(v + rng.gauss(0, 4) * h)))
            for off in (1, 3):
                t = round((bar * 4 + off) * PPQ + rng.gauss(0, 3) * h * ms2ticks)
                out.append((max(0, t), max(0, t) + 100, 44, int(72 + rng.gauss(0, 4) * h)))
        return out

    # ---- text view -------------------------------------------------------- #
    def chart(self, notes: List[Note]) -> str:
        lines = []
        by_bar: Dict[int, List[Note]] = {}
        for n in notes:
            by_bar.setdefault(int(n.beat) // 4, []).append(n)
        segs_by_bar: Dict[int, List[Segment]] = {}
        for s in self.segments:
            segs_by_bar.setdefault(s.beat // 4, []).append(s)
        for b in sorted(by_bar):
            if b not in segs_by_bar:
                lines.append(f"{b + 1:>3}  {'(end)':<11} " + note_name(by_bar[b][0].pitch))
                continue
            chords = " ".join(s.chord.symbol for s in segs_by_bar[b])
            txt = " ".join(note_name(n.pitch) + ("&" if n.kind == "eighth" else "")
                           for n in by_bar[b])
            tag = f"  [chorus {segs_by_bar[b][0].chorus + 1}]" if b % len(self.bars) == 0 else ""
            lines.append(f"{b + 1:>3}  {chords:<11} {txt}{tag}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Standard MIDI File writer (no dependencies)
# --------------------------------------------------------------------------- #
def _vlq(n: int) -> bytes:
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _chunk(events) -> bytes:
    events.sort(key=lambda e: (e[0], e[1]))
    body, last = bytearray(), 0
    for tick, _, data in events:
        body += _vlq(tick - last) + data
        last = tick
    body += _vlq(0) + b"\xFF\x2F\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def _name(s: str):
    b = s.encode()
    return (0, -2, b"\xFF\x03" + _vlq(len(b)) + b)


def note_events(notes, channel, program=None):
    ev = []
    if program is not None:
        ev.append((0, -1, bytes([0xC0 | channel, program])))
    for on, off, pitch, vel in notes:
        ev.append((on, 1, bytes([0x90 | channel, pitch, vel])))
        ev.append((off, 0, bytes([0x80 | channel, pitch, 0])))
    return ev


def write_midi(path: str, tempo: float, tracks: List[Tuple[str, list]]) -> None:
    mpqn = round(60_000_000 / tempo)
    conductor = [_name("Conductor"),
                 (0, -2, b"\xFF\x51\x03" + mpqn.to_bytes(3, "big")),
                 (0, -2, b"\xFF\x58\x04\x04\x02\x18\x08")]
    chunks = [_chunk(conductor)]
    for name, ev in tracks:
        chunks.append(_chunk([_name(name)] + ev))
    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ))
        for c in chunks:
            f.write(c)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Walking bass generator (swing + humanize) -> MIDI")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="bags")
    ap.add_argument("--chords", help='custom changes, e.g. "Dm7 | G7 | Cmaj7 | Cmaj7" '
                                     "(bars split by |, up to 4 chords per bar, % repeats)")
    ap.add_argument("--tempo", type=float, default=140)
    ap.add_argument("--choruses", type=int, default=2)
    ap.add_argument("--swing", type=float, default=None,
                    help="long:short eighth ratio. 1=straight, 2=triplet feel (default: from tempo)")
    ap.add_argument("--humanize", type=float, default=1.0, help="0=exact, 1=default, 2=loose")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--root-bias", type=float, default=0.55)
    ap.add_argument("--enclosure", type=float, default=0.15)
    ap.add_argument("--eighths", type=float, default=0.10, help="probability of swung eighth skips")
    ap.add_argument("--motif", type=float, default=0.55, help="probability a bar reuses the chorus contour cell")
    ap.add_argument("--arc", type=float, default=6.0, help="registral arc height in semitones")
    ap.add_argument("--ride", action="store_true", help="add a swung ride/hi-hat track")
    ap.add_argument("--out", default="walking_bass.mid")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    bars = parse_progression(a.chords or PRESETS[a.preset])
    params = Params(tempo=a.tempo, choruses=a.choruses, seed=a.seed, swing=a.swing,
                    humanize=a.humanize, root_bias=a.root_bias, enclosure_prob=a.enclosure,
                    eighth_prob=a.eighths, motif_prob=a.motif, register_arc=a.arc)
    gen = WalkingBass(bars, params)
    notes = gen.compose()
    bass = gen.perform(notes)

    tracks = [("Walking Bass", note_events(bass, 0, program=32))]
    if a.ride:
        total = (len(gen.segments) and gen.segments[-1].beat + gen.segments[-1].length)
        tracks.append(("Ride", note_events(gen.ride(total), 9)))
    write_midi(a.out, a.tempo, tracks)

    if not a.quiet:
        print(gen.chart(notes))
    print(f"\nwrote {a.out}  (tempo {a.tempo:g}, swing {gen.ratio:.2f}:1, "
          f"humanize {a.humanize:g}, seed {gen.seed})")


if __name__ == "__main__":
    main()
