Virtual Analog Lab
A single-file browser demo of a classic analog synth voice: a sawtooth oscillator feeding a four-stage ladder filter, calculated sample by sample in JavaScript. Play a note, flip the switches, and watch the spectrum and waveform change in real time.
There is nothing to install or build. Open Virtual Analog Lab.html in a modern desktop or mobile browser.
Volume warning: at high resonance and drive the filter can get loud and will self-oscillate. Turn your volume down before pressing Start audio.
Quick start
	1	Open the HTML file in your browser.
	2	Press Start audio (browsers require a click or key press before they allow sound). Pressing a key on the on-screen or computer keyboard also starts it.
	3	Hold a note, then move the sliders and switches.
Controls
Sliders
Control
Range
What it does
Cutoff
40 Hz to 8 kHz (logarithmic)
Base frequency of the filter. Default is about 630 Hz.
Resonance
0 to 4.2
Feedback around the filter. At 4 and above the Ladder model oscillates by itself.
Drive
1× to 10×
Gain into the filter. Only affects the Ladder model, where more drive means more saturation.
Envelope to cutoff
0 to 100%
How far the note envelope opens the filter. At 100% the cutoff can rise to 7× its base value at the start of a note, then settle back.
Switches
Switch
Options
Difference
Oscillator
Naive saw / PolyBLEP saw
The naive saw is the textbook formula. Its harmonics above the Nyquist limit fold back as inharmonic noise (aliasing). PolyBLEP corrects the sharp edge of the wave and removes most of it.
Filter model
Ideal (linear) / Ladder (saturating)
Ideal is a plain linear filter, with resonance limited to 3.9 to stay stable and drive ignored. Ladder bends each stage with tanh, like transistors, so it saturates, thickens with drive and can self-oscillate.
Playing
	•	Keyboard: one octave from C to C, starting at C3 (about 130.8 Hz). Click or tap the keys.
	•	Computer keys: A W S E D F T G Y H U J K map to C, C♯, D, D♯, E, F, F♯, G, G♯, A, A♯, B, C.
	•	Hold note: keeps the gate open after you release a key, which is handy for tweaking.
	•	The voice is monophonic. It plays the most recently pressed pitch, and the gate stays open while any key is held.
The displays
	•	Spectrum: 40 Hz to 20 kHz on a log scale, from -100 dB to 0 dB. The comb of peaks is the harmonics. The low-level "grass" between them is aliasing, so compare naive and PolyBLEP to see it.
	•	Waveform: a scope view triggered at a rising zero crossing. Flat tops on the wave mean the filter stages are saturating.
What to try
	1	Hold a low note and switch between Naive saw and PolyBLEP saw. The noise floor between harmonics drops.
	2	Set Resonance to 4.2 with Ladder on and pull the cutoff down. The filter rings at its own pitch with nothing feeding it.
	3	Switch to Ideal. Resonance stops at 3.9, drive no longer matters and the waveform never flattens.
	4	Raise Envelope to cutoff and play short notes to hear the filter sweep open and close on each key press.
How it works
Everything is in one file, with no dependencies. The core is one function, makeDSP(sampleRate), which returns an object with set(params) and run(buffer). For every output sample it does the following:
	1	Oscillator: generates a rising sawtooth from a phase counter, with the PolyBLEP correction applied near the wrap point when enabled.
	2	Envelope: a simple attack and a decay of about 0.35 seconds, driving the cutoff modulation. A separate smoothed amplitude follows the gate to avoid clicks.
	3	Cutoff: base × (1 + amount × 6 × envelope), capped at 45% of the sample rate, then converted to a one-pole coefficient.
	4	Ladder filter: four cascaded one-pole stages with the output fed back to the input, scaled by the resonance amount. In Ladder mode each stage and the input are passed through tanh.
	5	Output: scaled and hard-limited to the range -1 to 1. If the filter state ever becomes invalid it is reset, so a bad setting can't leave it stuck silent.
Audio setup
	•	The DSP runs in an AudioWorklet, which is built at runtime from the makeDSP source and loaded through a Blob URL. Slider changes are sent to it as messages.
	•	If AudioWorklet isn't available, the page falls back to a ScriptProcessorNode, which runs the same DSP on the main thread. It is deprecated and more likely to glitch.
	•	The output goes through an AnalyserNode (4096-point FFT) for the spectrum and scope, then a master gain of 0.6.
Appearance
The page follows the system light or dark mode. To force one, set data-theme="light" or data-theme="dark" on the <html> element.
Known limitations
	•	Feedback delay: the filter reads its feedback from the previous sample and updates twice per sample to soften the resulting error. Production-quality models solve this feedback loop exactly, so this filter will not match a real ladder's resonance or tuning precisely.
	•	One oscillator waveform: only a sawtooth. There is no pulse width, sub-oscillator or noise.
	•	Monophonic, no MIDI: there is no polyphony, MIDI input, velocity or pitch bend.
	•	Fixed envelope: the envelope has no adjustable attack, decay or release, and it only affects the filter cutoff. Amplitude follows the gate.
	•	Aliasing in the filter: the saturation stages can also create harmonics that alias. Only the oscillator is band-limited.
Customizing
All the settings below live in the single script block.
To change
Look for
Lowest note
130.81 in the keyboard section (the C3 frequency)
Computer key layout
the keyMap string
Cutoff range
cutHz, currently 40 × 200^(v/1000)
Resonance limit for Ideal mode
Math.min(p.res, 3.9) in makeDSP
Envelope speed
the .004 attack and .35 decay values in makeDSP
Master volume
out.gain.value in start()
Browser support
Any current Chrome, Edge, Safari or Firefox that supports the Web Audio API. AudioWorklet needs a secure context in some setups. If it isn't available the page uses the fallback described above.
