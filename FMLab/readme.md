# FM Lab 🎛️
### A visual playground for discovering FM synthesis

FM Lab is an interactive synthesizer designed to make **frequency modulation (FM) synthesis understandable through experimentation, listening, and visualization**.

You don't need previous experience with synthesizers, sound design, music theory, or FM programming to use it.

Instead of learning complicated synthesizer algorithms first, FM Lab lets you change a few parameters, hear what happens, and see how the sound changes.

The idea is simple:

> Change something. Listen. Observe. Discover why it happened.

---

## What is FM synthesis?

Every sound is made of vibrations. Even a simple tone can be thought of as a vibration repeating many times per second.

A sine wave is one of the simplest possible sounds. It sounds clean, smooth, and almost pure.

FM synthesis starts with this simple sound and uses one oscillator to continuously change the frequency of another oscillator.

This process can produce an enormous range of sounds, from:

- Pure, gentle tones
- Bell-like sounds
- Metallic sounds
- Electric piano tones
- Bass sounds
- Glass-like textures
- Strange, evolving, and experimental sounds

FM Lab lets you explore this process without having to understand the mathematics in advance.

---

## Getting started

Open FM Lab in your browser.

1. Select a note using the on-screen keyboard.
2. Hold the note.
3. Move the **Modulation Depth** slider.
4. Listen to the sound change.
5. Watch the frequency spectrum react.

Start with small changes. You may be surprised how dramatically a sound can change from just one adjustment.

---

## Understanding the controls

### Modulator Ratio

The modulator is the oscillator that influences the frequency of the audible oscillator.

The ratio determines how quickly the modulator oscillates relative to the note you play.

For example:

- `1.00` — the modulator oscillates at the same frequency as the played note.
- `2.00` — the modulator oscillates twice as fast.
- `3.00` — three times as fast.
- `0.50` — half the frequency.

Changing the ratio can dramatically change the character of the resulting sound.

Certain ratios produce harmonic relationships that sound musical and familiar. Other ratios can produce inharmonic, metallic, or unusual tones.

Experiment with different ratios rather than trying to memorize them.

---

### Modulation Depth

This is one of the most important controls in FM Lab.

Modulation depth determines how strongly the modulator influences the carrier's frequency.

At low values, the sound may remain close to a simple sine wave.

As modulation depth increases, additional frequency components appear. The sound can become richer, brighter, sharper, metallic, or more complex.

Try increasing modulation depth slowly while holding a note.

Notice that the sound isn't simply becoming louder. Its actual character is changing.

---

### Carrier Ratio

The carrier is the oscillator whose output you hear.

The carrier ratio determines its frequency relative to the note played on the keyboard.

Changing this ratio changes the pitch foundation of the sound.

Think of the carrier as the starting point and the modulator as the force that transforms it.

---

### Attack

Attack determines how quickly the sound reaches its initial level after a key is pressed.

- Short attack: sound starts immediately.
- Longer attack: sound gradually fades in.

This can change the perceived character of a sound from sharp and immediate to soft and gradual.

---

### Release

Release determines how quickly the sound fades after you release the key.

- Short release: sound stops quickly.
- Long release: sound continues fading naturally.

Longer release times can make sounds feel spacious or lingering.

---

### Master Volume

Controls the overall output level.

When experimenting with modulation depth, remember that a more complex sound can sometimes feel louder or more aggressive even when the actual output level hasn't changed much.

---

## What you're looking at

FM Lab doesn't only generate sound. It also gives you visual representations of what that sound is doing.

### Frequency Spectrum

The spectrum shows the frequency components present in the sound.

A simple sine wave produces a single dominant frequency.

FM synthesis introduces additional frequency components, often appearing as groups of frequencies around the original tone.

As you increase modulation depth, watch the spectrum change.

Those additional peaks are a visual representation of the complexity you're introducing into the sound.

---

### Waveform

The waveform shows the sound as it changes over time.

A pure sine wave looks smooth and regular.

As modulation changes the sound, the waveform can become more complex.

The waveform helps you understand that sounds which seem dramatically different to your ears can still be generated using relatively simple oscillators.

---

### FM Sidebands

FM synthesis produces additional frequencies called sidebands.

These frequencies appear above and below the carrier frequency, spaced according to the modulator frequency.

Sidebands are an important part of what makes FM synthesis capable of producing such a wide range of timbres.

This visualization helps connect the modulation controls with the frequency components they generate.

---

### Spectrogram

The spectrogram displays frequency content over time.

Instead of looking at a single moment, it allows you to see how the sound develops.

You can observe how the sound changes when you:

- Press a key
- Hold a note
- Change modulation depth
- Release a key

It provides a visual representation of the evolving sound.

---

## Experiments to try

You don't need to follow these in order. Think of them as small experiments.

### Experiment 1 — The pure tone

1. Set Modulation Depth to `0`.
2. Set Carrier Ratio to `1.00`.
3. Play a note.

Listen to the simplicity of the sound.

Look at the spectrum. Notice how little frequency content is present.

Now you have a reference point.

---

### Experiment 2 — Add complexity

1. Keep holding the same note.
2. Slowly increase Modulation Depth.
3. Observe the spectrum.

Listen for the sound becoming brighter, harsher, richer, or more metallic.

You are adding complexity to the sound by modulating its frequency.

---

### Experiment 3 — Change the relationship

1. Keep Modulation Depth somewhere in the middle.
2. Change Modulator Ratio from `1.00` to `2.00`.
3. Then try `3.00`.
4. Try some values in between.

Notice that the same amount of modulation can produce completely different sounds depending on the relationship between the two oscillators.

---

### Experiment 4 — Find a bell

1. Set Carrier Ratio to `1.00`.
2. Try Modulator Ratio around `2.00` or `3.00`.
3. Increase Modulation Depth.
4. Try a relatively short Attack.
5. Experiment with Release.

Listen for metallic or bell-like qualities.

Don't worry if you don't immediately find a sound you like. The interesting part is understanding how changing the parameters affects the result.

---

### Experiment 5 — Make it softer

1. Reduce Modulation Depth.
2. Increase Attack.
3. Increase Release.
4. Try lower notes on the keyboard.

Listen for the transition from an aggressive tone to something softer and more rounded.

---

### Experiment 6 — Explore the unexpected

Try settings that might not seem musically obvious.

Use ratios such as:

- `1.41`
- `2.37`
- `3.14`
- `0.73`

Combine them with different modulation depths.

FM synthesis is not limited to traditional musical sounds. It can produce drones, textures, noises, strange resonances, and sounds that don't resemble conventional instruments at all.

Sometimes the most interesting discoveries happen when you stop trying to make a piano, bell, or bass.

---

## The philosophy behind FM Lab

Traditional FM synthesizers often present users with algorithms, operators, envelopes, frequency ratios, and modulation indices.

These are powerful tools, but they can make FM synthesis feel unnecessarily intimidating.

FM Lab takes a different approach.

Rather than requiring you to memorize what a particular algorithm does, it encourages you to observe the relationships between:

- Frequency
- Modulation
- Harmonics
- Waveforms
- Time
- Perception

The goal isn't to hide the mathematics.

The goal is to make the mathematics visible, understandable, and approachable.

You can start by making sounds you enjoy. Along the way, you may begin to recognize why those sounds happen.

And eventually, the mathematics stops being something you have to learn before you can experiment.

It becomes something you discover through sound.

---

## Who is FM Lab for?

FM Lab is for anyone curious about sound.

You might be:

- A musician looking for new sounds.
- A synthesizer enthusiast.
- Someone interested in sound design.
- A curious beginner who has never touched a synthesizer.
- Someone interested in the physics and mathematics of sound.
- Someone who simply enjoys experimenting.

No keyboard skills are required.

No FM programming experience is required.

Curiosity is enough.

---

## Technology

FM Lab is built using:

- HTML
- CSS
- JavaScript
- Web Audio API

Audio is generated directly in the browser.

No installation, external synthesizer, or additional software is required.

---

## Project vision

FM Lab is an exploration of a simple question:

**What if understanding a synthesizer were as intuitive as watching and listening to what it does?**

The long-term idea is to make synthesis more visual, interactive, and exploratory.

Not just a synthesizer with controls.

A laboratory for sound.

🎛️