# Walking Bass Generator

A rule-based walking bass generator with adjustable swing and humanization, in two forms:

| Release | What it is | Output |
|---|---|---|
| `walking_bass.py` | Command-line Python script, no dependencies | A `.mid` file, plus a bar-by-bar text chart |
| `walking_bass_live.html` | Browser page you can play with while it runs | Live audio, a piano roll, and MIDI export |

Live page: https://claude.ai/artifact/8TPSV9FHugfg5HpcJC76st

Both are inspired by Seow & Wang (2026), *Walking Bass as Melodic-Formal Accompaniment: Selected Paul Chambers Hard-Bop Blues Close Readings* (JOLLS 15(3)).

## How the paper became rules

The paper is a close-reading study, not an algorithm. It gives three analytical terms, and the generators turn each into a generation rule. That translation is my interpretation, not the authors' method.

| Paper term | What the generator does |
|---|---|
| **Target orientation** | The first beat of each chord is an "anchor": root, 3rd, 5th or 7th, not always the root. Chord tones shared with the previous chord get a bonus (the D-F-F-C over B-flat7 idea in "Bags' Groove"). Each chorus starts on the root most of the time. |
| **Chromatic continuity** | The last beat before each anchor is a chromatic approach (a half step above or below, sometimes a whole step), occasionally enclosure-like (approached from both sides). Middle beats are picked by a small search that prefers steps and chord tones on strong beats. |
| **Motivic scaling** | Each chorus picks a short contour cell, such as up-up-down, that recurs in adapted form across bars. A registral arc rises into the second half of the chorus and comes back down. |

## Swing and humanization

- **Swing** is a remap of the beat grid. The ratio is long:short for eighth notes: 1 is straight, 2 is triplet feel. Note lengths follow the swing.
- **Laid-back delay** pushes the bass slightly behind the beat, more on beats 1 and 3. This draws on the Nelias et al. (2022) finding the paper cites about downbeat delays and swing.
- **Humanization** adds timing jitter, slow rushing and dragging, velocity variation, and note-length variation with the occasional short note. Approach tones lean slightly forward.
- At humanize 0 and swing 1 the output is machine-exact, which is useful as a reference.

## `walking_bass.py`

Requires Python 3. It writes the MIDI file itself, so there is nothing to install.

```bash
python walking_bass.py --preset bags --tempo 130 --choruses 3 --seed 3 --ride --out bags.mid
python walking_bass.py --preset straight --tempo 220 --swing 1.5
python walking_bass.py --chords "Dm7 | G7 | Cmaj7 A7" --choruses 4 --seed 7
python walking_bass.py --preset bags --humanize 0 --swing 1
```

| Option | Meaning | Default |
|---|---|---|
| `--preset` | `bags`, `straight` or `bluetrain` | `bags` |
| `--chords` | Your own changes. Bars are split by `\|`, up to 4 chords per bar, `%` repeats the previous chord | |
| `--tempo` | Beats per minute | 140 |
| `--choruses` | Number of times through the form | 2 |
| `--swing` | Long:short eighth ratio | From tempo (about 2.3:1 at 140 bpm, flatter as tempo rises) |
| `--humanize` | 0 exact, 1 normal, 2 loose | 1 |
| `--seed` | Makes a run repeatable. The same seed gives the same notes at any humanize setting | Random |
| `--root-bias` | How often anchors are roots, 0 to 1 | 0.55 |
| `--enclosure` | Chance of an enclosure-like approach | 0.15 |
| `--eighths` | Chance of a swung eighth-note skip | 0.10 |
| `--motif` | Chance a bar reuses the chorus contour cell | 0.55 |
| `--arc` | Height of the registral arc, in semitones | 6 |
| `--ride` | Adds a swung ride and hi-hat track | off |
| `--out` | Output file | `walking_bass.mid` |
| `--quiet` | Skip the printed chart | off |

The MIDI file has a conductor track and a bass track (acoustic bass, program 32), plus a ride and hi-hat track with `--ride`. The printed chart shows the chords and note names per bar, with `&` marking eighth-note skips.

## `walking_bass_live.html`

A single page that runs in the browser and plays through Web Audio. Press **Play**.

**Controls above the roll**
- **Form** dropdown: Bags' Groove (the chart from the paper's Example 1), Straight No Chaser, an E-flat blues, and the A section of rhythm changes. You can also type your own changes in the box next to it.
- **New line**: picks a new random seed and restarts from the top of the form.
- **Seed**: type a number to get the same line again. A seed reproduces the line from the first bar when you press Play or change the seed.
- **Ride cymbal** and **Piano** checkboxes switch those parts on and off while playing.
- **Export MIDI**: saves the chorus currently on screen as `walking-bass.zip`, containing `walking-bass.mid`. It is a zip because the viewer's save list does not allow `.mid` files. The export applies your current swing, laid-back and humanize settings, and includes bass, piano and ride tracks. You get a confirmation prompt before it saves.

**Feel sliders (heard within a beat or two)**
- Tempo (60 to 280), Swing ratio (1 to 3), Humanize (0 to 2), Laid-back (0 to 40 ms), Slide into notes (0 to 1).

**Line sliders (applied when you release a slider, from the current position)**
- Root bias, Enclosures, Eighth skips, Motif recall, Register arc, Comp density.

**Piano roll**
- Each bass note is drawn where it will actually sound, swung and laid back. An outline marks its straight-grid position, so dragging swing or laid-back visibly moves the notes against the outlines.
- Colors: teal for chord-tone arrivals, dark for passing notes, amber for chromatic approaches. Small grey bars along the top are piano hits.

**Piano comping**
- Three-note shell voicings of the 3rd, 7th and 9th, kept close to the previous voicing for smooth voice leading.
- The rhythm is chosen bar by bar from five Charleston-style patterns. Chords that last two beats or less get one hit.
- Comp density sets how many hits are played. The piano follows the same swing as the bass and sits slightly ahead of it.

**Sound**
- Bass: a plucked tone with a short finger click, and optional slides from the previous note on close steps.
- Piano and ride are simple synthesized sounds, good enough for judging feel rather than for sounding like real instruments.

## Differences between the two releases

| | Python script | Browser page |
|---|---|---|
| Piano comping | No | Yes |
| Plays sound | No | Yes |
| Swing default | From tempo | 2.2:1 |
| Slide into notes | No | Yes |
| MIDI export | Direct `.mid` file | `.zip` containing `.mid`, current chorus only |
| Preset forms | Bags' Groove, Straight No Chaser, E-flat blues | Those three plus rhythm changes A |

## Limitations

- 4/4 only, one bass note per beat plus occasional swung eighth skips. No triplet skips, ghost notes or double stops.
- The generator does not hear the rest of the ensemble, which the paper stresses matters for how a line is heard.
- The `bluetrain` preset is a generic E-flat blues with a turnaround, not the paper's transcription.
- Straight No Chaser and the E-flat blues follow common blues forms rather than exact recordings.
- The browser page's synthesized sounds have not been checked by ear, so expect to adjust them.
- Both are tools for experimenting with the paper's ideas, not a claim about how Paul Chambers actually played.
