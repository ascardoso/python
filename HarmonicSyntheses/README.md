# Harmonic Evolution Studio

A small, self-contained additive synthesizer built with HTML, CSS, JavaScript, Canvas, and the Web Audio API.

## Run it

1. Unzip the folder.
2. Open `index.html` in a modern desktop browser (Chrome, Edge, Firefox, or Safari).
3. Choose a harmonic (H1–H16).
4. Draw its amplitude curve in the large editor: left is note start, right is note end; bottom is silence and top is full amplitude.
5. Press **Play note**. Audio starts only after the button is clicked, as required by browser audio policies.

No server, packages, or audio samples are required.

## What it does

- Generates 16 sine oscillators at integer multiples of the fundamental frequency.
- Stores each harmonic's envelope as a small list of time/amplitude points.
- Interpolates the points into a smooth automation curve and schedules it with Web Audio.
- Displays the combined waveform and live FFT spectrum.
- Saves no audio files; the sound is calculated in real time.

## Current prototype limits

This is the first working editor: envelopes are piecewise-linear between drawn points, and each Play action renders one note of the selected duration. The waveform and FFT are live browser measurements. Curves are currently held in memory and reset when the page reloads; preset save/load, spectrogram, richer interpolation, and per-harmonic phase/frequency modulation are natural next additions.

Keep the master level modest, especially when many harmonics are near full amplitude.
