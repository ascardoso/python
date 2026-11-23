# FM Lab

A single-file browser synthesizer for learning and playing with frequency modulation (FM) sound. It has four sine-wave operators that you can wire together with five algorithms, presets, a clickable algorithm diagram, velocity-sensitive MIDI input, and live displays that show the sound as audio, as a spectrum, and as the math behind it.

There is nothing to install or build. Open `FM_Math.html` in Chrome (recommended for MIDI) or another current browser.

> **Volume warning:** high modulation indexes make bright, loud attacks. Start with the master volume low.

## Quick start

1. Open the page and press a key (`A S D F G H J K`) or click a key on screen. The first interaction starts the audio.
2. The page loads the **DX7-style E.Piano** preset. Play a few notes.
3. Pick another preset, or click an operator in the diagram and move its sliders while holding a key.

## The idea in one minute

In FM synthesis, one oscillator (a **modulator**) wobbles the pitch of another (a **carrier**). The carrier is the one you hear. This produces extra frequencies called sidebands, and the amount of wobble, the **modulation index (β)**, controls how many there are and how bright the sound is. A modulator with its own envelope makes the tone change over the length of a note, which is what gives FM its bell and electric-piano sounds.

Here each operator is a sine oscillator with its own envelope and level. An **algorithm** defines who modulates whom and which operators are heard.

## Patch panel

### Presets and algorithms

- **Preset:** DX7-style E.Piano (default), Electric piano, Bell, Brass, Organ, FM bass.
- **Algorithm:** the routing of the four operators. The diagram shows modulators in orange, carriers in green, and arrows from each modulator to the operator it modulates. Click an operator box to edit it.

| Algorithm | Routing | Typical use |
|---|---|---|
| 1 · Stack | 4 → 3 → 2 → 1 | Aggressive, complex tones (brass, bass) |
| 2 · Pairs | 2 → 1 and 4 → 3 | Electric pianos, bells |
| 3 · Y | 3 → 2 → 1 and 4 → 1 | Two modulation paths into one carrier |
| 4 · Fork | 4 → 1, 2 and 3 | One modulator shared by three carriers |
| 5 · Parallel | none | Additive, organ-like sounds |

Changing the algorithm or preset stops any held notes, so old and new routings are never mixed.

### My patches

- **Save:** type a name and press Save. Saving under an existing name overwrites it.
- **Load:** choose a patch from the list (it loads immediately), or press Load.
- **Delete:** removes the selected patch.
- **Backup / share:** Export puts all your saved patches in the text box as JSON. Copy it somewhere safe. To restore or share, paste the text and press Import.

Saved patches live in this browser's local storage, so they stay on this device and browser. Clearing site data removes them, so use Export as a backup. If storage is blocked, the page says so and the patch lasts only for the session.

## Operator controls

Select operator 1 to 4 with the tabs or by clicking it in the diagram. Which operators are carriers depends on the algorithm.

| Control | Range | Meaning |
|---|---|---|
| **Frequency ratio** | 0.25 to 14 | Operator frequency as a multiple of the played note. Whole numbers give harmonic tones, while values like 3.5 or 5.19 give bell-like, inharmonic ones. |
| **Level** | 0 to 1 (carrier) or 0 to 10 (modulator) | For a carrier, output volume. For a modulator, the modulation index β. |
| **Attack** | 1 to 2000 ms | Time to rise to full level. |
| **Decay** | 1 to 4000 ms | Time to fall toward the sustain level. |
| **Sustain** | 0 to 100% | Level held while the key stays down. |
| **Release** | 10 to 3000 ms | Fade-out time after the key is released. |
| **Velocity sensitivity** | 0 to 100% | How much key velocity scales the operator's level. |

A modulator's envelope scales its β over time, so a high attack and a low sustain give a bright strike that mellows quickly. The **master volume** and the **octave** selector (for the computer keys) are below the operator controls.

## Playing

- **Computer keys:** `A S D F G H J K` play C D E F G A B C. The octave selector shifts the range, and the keys play at a fixed velocity.
- **On-screen keys:** click or tap. Pressing lower on a key plays harder.
- **MIDI keyboard:** see below.
- **Stop** silences everything.
- The synth is polyphonic. Typing in the patch name or backup boxes does not trigger notes.

## MIDI

The page uses Web MIDI, which Chrome supports. A status line under the keys reports whether a device was found.

- **Notes and velocity:** every key on your controller plays, at the correct pitch, and velocity (1 to 127) scales each operator's level according to its velocity-sensitivity setting. For modulators this means harder playing brings out more bite.
- **Velocity formula:** level × (1 − sensitivity + sensitivity × velocity).
- **Sustain pedal (CC 64):** holds notes after you release the keys.
- **All notes off (CC 123 and CC 120)** silences everything.
- **Not handled:** pitch bend, mod wheel and aftertouch.

Browsers ask permission for MIDI access the first time. Click the page once so the browser allows audio to start, because MIDI messages alone cannot start it. If the page is embedded inside another page, MIDI permission may be blocked. Open it in its own browser tab in that case. If you hear no dynamics, your keyboard may send a fixed velocity.

## The displays

- **Output waveform:** the live audio signal.
- **Frequency spectrum:** a live FFT from 0 to 10 kHz. In FM you will see the sidebands appear and change as the modulation index moves.
- **FM sidebands:** the predicted component strengths from Bessel functions at fc ± n·fm, for the first modulation route only (labeled with which operators). This model is exact for one modulator into one carrier. With stacked or multiple modulators, trust the live spectrum instead. The Parallel algorithm shows "no modulation".
- **Envelopes:** one curve per operator, carriers in green and modulators in orange, for the notes currently held.
- **Mathematical model:** the equation for the current patch, built from the routing as nested sines, plus the carrier and modulator frequencies, the deviation in Hz, and the peak index.

## Getting more bite from the electric piano

Bite is a strong, brief burst of high harmonics at the start of a note.

- Raise the body modulator's β (try 3.5 or more) and shorten its decay (400 to 600 ms) with a low sustain.
- Strengthen the tine: raise the tine modulator's β and the tine carrier's level, and give the tine a slightly longer decay.
- Keep the carrier attack very short (1 to 2 ms).
- Increase the modulators' velocity sensitivity so that harder playing opens up the sound further.

The "DX7-style E.Piano" preset is a four-operator approximation of that sound. It does not use real DX7 patch data. The real instrument uses six operators and features this page does not have (see limitations).

## How it works

Each held note creates a voice. For every operator, the page builds a Web Audio chain: a sine oscillator, then an envelope gain, then a level gain. The algorithm decides the connections:

- A **route** connects a modulator's level gain to the target operator's frequency parameter. The modulator's level is set to β × velocity scaling × the modulator's own frequency, which converts the index into a frequency deviation in Hz. Because it is tied to the modulator's frequency, the brightness stays consistent across notes.
- An **output** connects a carrier's level gain to the master gain, then an analyser, then the speakers.

Envelopes are an attack ramp followed by an exponential decay to the sustain level, with a linear release. Operators, algorithms and presets are plain data, so the voice builder, the live parameter updates, the diagram, the equation and the envelope plot all read from the same tables.

## Patch format

Patches are stored as JSON. Each patch has a name, an algorithm index (0 to 4) and four operators, each as `[ratio, level, attack, decay, sustain, release, velocitySensitivity]`. Times are in seconds, and sustain and velocity sensitivity are 0 to 1.

```json
{"n":"My patch","alg":1,"ops":[[1,1,0.002,2.8,0.2,0.5,0.35],[1,2.4,0.001,1.2,0.08,0.5,0.9],[1,0.35,0.001,0.9,0,0.3,0.35],[14,1.6,0.001,0.07,0,0.2,0.8]]}
```

Imported values are clamped to valid ranges, and entries that don't match this shape are skipped.

## Known limitations

- **Four operators, five algorithms.** A DX7 has six operators and 32 algorithms.
- **No operator feedback,** which adds edge on a real DX7.
- **Sine waves only,** with no fine detune between operators.
- **No key scaling,** so modulation is the same across the keyboard. Velocity is the only dynamic control.
- **Sideband model covers one route.** See the displays section.
- **No pitch bend, mod wheel or aftertouch.**
- **Patches are per browser,** not synced between devices.

## Customizing

These live in the single script block of the file.

| To change | Look for |
|---|---|
| Add or edit algorithms | the `ALGS` list: `routes` are `[source, target]` pairs and `out` lists the heard operators (operators are numbered from 0 in code) |
| Add or edit presets | the `PRESETS` list, using the tuple format above |
| Computer key layout and pitches | `keyCodes` and `keyFreqs` |
| Slider limits and patch clamping | the `LIM` table and the slider `min` and `max` values in the HTML |
| MIDI behavior | the `midiMsg` function |

## Browser support

Any current browser with the Web Audio API will play sound. MIDI input needs Web MIDI, which is reliable in Chrome and Edge and limited or absent in Safari and Firefox. Everything else, including the computer and on-screen keys, works without it.