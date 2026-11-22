# FM Lab — Understanding the Mathematics Behind the Sound

## What's new?

FM Lab connects the sound being generated to the mathematical model responsible for it.

Every parameter has a mathematical meaning, and changes to those parameters are reflected in the audio, equations, and visualizations.

The goal is simple:

**Don't just make a sound. Understand why it sounds the way it does.**

---

## 1. One source of truth

FM Lab uses a shared sound state to keep its different parts synchronized.

This state contains the parameters that define the current sound:

- Note frequency
- Carrier frequency ratio
- Modulator frequency ratio
- Modulation depth
- Attack and release
- Master volume
- Playback state

The audio engine, mathematical calculations, and visualizations all use this same information.

This avoids having separate parts of the application make independent assumptions about what the sound should be.

For example, changing the modulator ratio updates the generated sound and the displayed mathematical values together.

---

## 2. How FM synthesis works

The current synthesizer uses two operators:

- **Carrier (C):** produces the main audible signal.
- **Modulator (B):** continuously changes the carrier's instantaneous frequency.

The instantaneous frequency can be described as:

$$
f_{\text{inst}}(t) =
f_c + \Delta f \sin(2\pi f_m t)
$$

Where:

| Symbol | Meaning |
|---|---|
| $f_c$ | Carrier frequency |
| $f_m$ | Modulator frequency |
| $\Delta f$ | Peak frequency deviation, in Hz |
| $t$ | Time |

The carrier's frequency is no longer constant. It moves above and below its center frequency according to the modulator.

To obtain the output waveform, we integrate this instantaneous frequency over time.

For sinusoidal modulation, one corresponding expression is:

$$
x(t) =
A\sin\left(
2\pi f_c t -
\beta\cos(2\pi f_m t)
\right)
$$

This expression uses a particular starting phase for the modulator. Other phase conventions produce equivalent FM spectra.

The important idea is that the modulator changes the carrier's phase continuously by changing its frequency.

---

## 3. Frequency ratios

The carrier and modulator frequencies are calculated from the played note.

For a note with frequency $f_0$:

$$
f_c = f_0 \times R_c
$$

$$
f_m = f_0 \times R_m
$$

Where:

- $R_c$ is the carrier frequency ratio.
- $R_m$ is the modulator frequency ratio.

### Example: A4

A4 has a frequency of 440 Hz.

With:

- Carrier ratio = 1
- Modulator ratio = 2

We get:

$$
f_c = 440 \times 1 = 440\text{ Hz}
$$

$$
f_m = 440 \times 2 = 880\text{ Hz}
$$

Changing these ratios changes the relationship between the two oscillators and therefore the resulting timbre.

---

## 4. Modulation depth and modulation index

Modulation depth determines how far the carrier frequency moves away from its center frequency.

The modulation index is calculated as:

$$
\beta = \frac{\Delta f}{f_m}
$$

This is an important distinction:

- Modulation depth ($\Delta f$) is measured in Hz.
- Modulation index ($\beta$) is dimensionless.

The modulation index describes the amount of frequency modulation relative to the modulator frequency.

### Example

For A4:

- Carrier frequency = 440 Hz
- Modulator frequency = 880 Hz
- Frequency deviation = 300 Hz

Then:

$$
\beta = \frac{300}{880}
\approx 0.341
$$

The resulting equation, using the phase convention described above, is:

$$
x(t) =
A\sin\left(
2\pi(440)t -
0.341\cos(2\pi(880)t)
\right)
$$

The application recalculates these values when the relevant controls change.

---

## 5. Where do the extra frequencies come from?

One of the most interesting properties of FM synthesis is that two oscillators can produce a much richer frequency spectrum.

The theoretical expansion of sinusoidal FM produces frequency components at:

$$
f_c \pm n f_m
$$

where $n$ is a non-negative integer.

For example:

| Component | Frequency |
|---|---|
| Carrier | $f_c$ |
| First sidebands | $f_c \pm f_m$ |
| Second sidebands | $f_c \pm 2f_m$ |
| Third sidebands | $f_c \pm 3f_m$ |
| Fourth sidebands | $f_c \pm 4f_m$ |

There can be many more sidebands, extending in both directions.

Some lower sideband frequencies can even become negative in the mathematical expansion. These correspond to components with a phase inversion when represented as positive frequencies.

### Bessel functions

The amplitudes of the theoretical FM components are determined by Bessel functions of the first kind:

$$
J_n(\beta)
$$

The carrier component is associated with $J_0(\beta)$, while the sidebands are associated with higher-order Bessel functions.

For a sinusoidal FM signal, the expansion is:

$$
\begin{aligned}
x(t) = A \bigg[&
J_0(\beta)\sin(\omega_c t) \\
&+ \sum_{n=1}^{\infty} J_n(\beta)
\left(
\sin((\omega_c+n\omega_m)t) \right.\\
&\qquad\qquad\left.
+(-1)^n\sin((\omega_c-n\omega_m)t)
\right)
\bigg]
\end{aligned}
$$

Here:

- $\omega_c = 2\pi f_c$
- $\omega_m = 2\pi f_m$
- $\beta$ is the modulation index.

These functions determine how energy is distributed among the carrier and sidebands.

This explains why increasing modulation depth can dramatically change the character of a sound.

It also explains why some sidebands become stronger while others become weaker or disappear.

---

## 6. Measured data versus calculated data

FM Lab distinguishes between actual measurements and mathematical predictions.

This distinction matters because a scientific-looking graph should represent something real.

### Live measurements

These are obtained from the actual generated audio:

- **Waveform:** displays samples from the audio signal.
- **Frequency spectrum:** uses an FFT (Fast Fourier Transform) to estimate the frequency content.
- **Spectrogram:** displays how measured frequency content changes over time.

### Mathematical predictions

These are calculated from the synthesis parameters:

- Carrier and modulator frequencies.
- Modulation index.
- Theoretical sideband frequencies.
- Theoretical sideband amplitudes using Bessel functions.

### Envelope model

The attack and release describe how a note's amplitude changes over time.

The envelope visualization follows the modeled voice envelope.

### Why measured and predicted spectra may differ

The theoretical sideband distribution describes an ideal sinusoidal FM signal.

The actual spectrum can differ because of:

- Finite FFT window size.
- Frequency resolution.
- The note's attack and release.
- Audio sampling rate.
- The duration of the measurement.
- Other implementation details.

The theoretical prediction and the measured spectrum complement each other. One explains what the mathematical model predicts; the other shows what the audio engine actually produces.

---

## 7. Why this matters

The mathematical display is not intended to turn FM Lab into a mathematics textbook.

It is there to answer practical questions:

- Why did this sound become brighter?
- Why did new frequencies appear?
- Why does changing the modulator ratio alter the character of the sound?
- Why does increasing modulation depth create more complex timbres?
- Why can two different frequency ratios produce very different results?

Instead of memorizing synthesis recipes, users can experiment and see the underlying relationships.

---

## 8. The idea behind FM Lab

FM synthesis is a beautiful example of how relatively simple mathematical relationships can produce complex results.

A sine wave modulating another sine wave can create bells, metallic tones, electric-piano-like sounds, basses, and entirely unfamiliar textures.

FM Lab aims to make those relationships visible and understandable.

**Listen to the sound. Look at the waveform. Explore the spectrum. Follow the equation.**

The mathematics is not separate from the instrument.

It is the instrument.