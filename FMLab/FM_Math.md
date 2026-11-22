FM Lab — Understanding the Mathematics Behind the Sound
What's new?
FM Lab has evolved beyond a visual synthesizer. It now connects the sound being generated to the mathematical model responsible for it.
Every parameter has a mathematical meaning, and changes to those parameters are reflected in the audio, equations, and visualizations.
The goal is simple:
Don't just make a sound. Understand why it sounds the way it does.

1. One source of truth
FM Lab uses a shared sound state to keep its different parts synchronized.
This state contains the parameters that define the current sound:
	•	Note frequency
	•	Carrier frequency ratio
	•	Modulator frequency ratio
	•	Modulation depth
	•	Attack and release
	•	Master volume
	•	Playback state
The audio engine, mathematical calculations, and visualizations all use this same information.
This avoids having separate parts of the application make independent assumptions about what the sound should be.
For example, changing the modulator ratio updates the generated sound and the displayed mathematical equation together.

2. The FM equation
The current synthesizer uses two operators:
	•	Carrier (C): produces the sound we hear.
	•	Modulator (B): continuously changes the carrier's instantaneous frequency.
The resulting signal can be represented by:
[ x(t)=A\sin\left(2\pi f_c t+ \beta\sin(2\pi f_m t)\right) ]
Where:
Symbol
Meaning
(x(t))
Output signal
(A)
Signal amplitude
(f_c)
Carrier frequency
(f_m)
Modulator frequency
(\beta)
Modulation index
(t)
Time
This equation describes sinusoidal frequency modulation.
The important detail is that the modulator doesn't simply add another audible tone. It changes the carrier's frequency over time.

3. Frequency ratios
The carrier and modulator frequencies are calculated from the played note.
For a note with frequency (f_0):
[ f_c=f_0\times R_c ]
[ f_m=f_0\times R_m ]
Where:
	•	(R_c) is the carrier ratio.
	•	(R_m) is the modulator ratio.
For example, playing A4 (440 Hz) with:
	•	Carrier ratio = 1
	•	Modulator ratio = 2
Produces:
[ f_c=440\text{ Hz} ]
[ f_m=880\text{ Hz} ]
Changing these ratios changes the relationship between the two oscillators and therefore the resulting timbre.

4. Modulation depth and modulation index
Modulation depth determines how far the carrier frequency is pushed away from its center frequency.
The instantaneous frequency is:
[ f_{\text{inst}}(t)= f_c+\Delta f\sin(2\pi f_m t) ]
Where (\Delta f) is the peak frequency deviation, measured in Hz.
The modulation index is:
[ \beta=\frac{\Delta f}{f_m} ]
This is an important distinction:
	•	Modulation depth is measured in Hz.
	•	Modulation index is dimensionless.
The modulation index describes the amount of modulation relative to the modulator frequency.
Example
For A4:
	•	Carrier = 440 Hz
	•	Modulator = 880 Hz
	•	Frequency deviation = 300 Hz
Then:
[ \beta=\frac{300}{880}\approx0.341 ]
The resulting equation becomes:
[ x(t)=A\sin\left( 2\pi(440)t+ 0.341\sin(2\pi(880)t) \right) ]
The application recalculates these values when the relevant controls change.

5. Where do all the extra frequencies come from?
One of the most interesting properties of FM synthesis is that a signal containing just two oscillators can produce a much richer spectrum.
The mathematical expansion of sinusoidal FM produces frequency components at:
[ f_c\pm nf_m ]
where (n) is a non-negative integer.
In other words:
	•	Carrier frequency: (f_c)
	•	First sidebands: (f_c-f_m) and (f_c+f_m)
	•	Second sidebands: (f_c-2f_m) and (f_c+2f_m)
	•	Third sidebands: (f_c-3f_m) and (f_c+3f_m)
	•	And so on.
Their amplitudes are determined by Bessel functions of the first kind:
[ J_n(\beta) ]
These functions determine how energy is distributed among the carrier and sidebands as the modulation index changes.
This explains why increasing modulation depth can dramatically change the character of a sound.
It also explains why some sidebands become stronger while others become weaker or disappear.

6. Measured data versus calculated data
FM Lab distinguishes between actual measurements and mathematical predictions.
This distinction matters because a scientific-looking graph should represent something real.
Live measurements
These are obtained from the actual generated audio:
	•	Waveform: displays samples from the audio signal.
	•	Frequency spectrum: uses an FFT (Fast Fourier Transform) to estimate the frequency content.
	•	Spectrogram: displays how measured frequency content changes over time.
Mathematical predictions
These are calculated from the synthesis parameters:
	•	Carrier and modulator frequencies.
	•	Modulation index.
	•	Theoretical sideband frequencies.
	•	Theoretical sideband amplitudes using Bessel functions.
Envelope model
The attack and release describe how a note's amplitude changes over time.
The envelope visualization follows the voice's modeled envelope behavior.
The theoretical sideband distribution describes the ideal sinusoidal FM signal. Actual FFT measurements can differ because of finite analysis windows, frequency resolution, amplitude envelopes, and other implementation details.

7. Why this matters
The mathematical display is not intended to turn FM Lab into a mathematics textbook.
It is there to answer practical questions:
	•	Why did this sound become brighter?
	•	Why did new frequencies appear?
	•	Why does changing the modulator ratio alter the character of the sound?
	•	Why does increasing modulation depth create more complex timbres?
	•	Why can two different frequency ratios produce very different results?
Instead of memorizing synthesis recipes, users can experiment and see the underlying relationships.

8. The idea behind FM Lab
FM synthesis is a beautiful example of how relatively simple mathematical relationships can produce complex results.
A sine wave modulating another sine wave can create bells, metallic tones, electric-piano-like sounds, basses, and entirely unfamiliar textures.
FM Lab aims to make those relationships visible and understandable.
Listen to the sound. Look at the waveform. Explore the spectrum. Follow the equation.
The mathematics is not separate from the instrument.
It is the instrument.
