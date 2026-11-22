
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

"""

"""Fourier Lab: generate, analyze, and reconstruct audio using librosa."""

import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import soundfile as sf

SR = 44100
DURATION = 3.5
N_FFT = 4096
HOP = 512


def make_test_sound(sr=SR, duration=DURATION):
    """Create a synthetic instrument-like tone with harmonics, vibrato, and envelope."""
    t = np.arange(int(sr * duration)) / sr
    f0 = 220.0
    vibrato_rate = 5.2
    vibrato_depth_hz = 2.0
    # Integrate frequency modulation into phase (so vibrato depth is in Hz).
    phase = 2 * np.pi * f0 * t + (vibrato_depth_hz / vibrato_rate) * np.sin(2 * np.pi * vibrato_rate * t)

    # Harmonic amplitudes: brighter at the attack, then gradually darker.
    harmonic_weights = np.array([1.0, 0.58, 0.36, 0.24, 0.15, 0.10, 0.07])
    tone = np.zeros_like(t)
    for h, weight in enumerate(harmonic_weights, start=1):
        tone += weight * np.sin(h * phase + 0.13 * h)

    # Simple attack / decay / sustain envelope.
    attack = np.clip(t / 0.025, 0, 1)
    decay = 0.78 + 0.22 * np.exp(-t / 0.45)
    release_start = duration - 0.35
    release = np.ones_like(t)
    mask = t >= release_start
    release[mask] = np.clip((duration - t[mask]) / 0.35, 0, 1)
    envelope = attack * decay * release

    tone *= envelope
    tone /= max(np.max(np.abs(tone)), 1e-12)
    tone *= 0.8
    return tone


def main():
    source = make_test_sound()
    sf.write("source.wav", source, SR)



    # Fourier analysis: complex STFT preserves magnitude AND phase information.
    stft = librosa.stft(source, n_fft=N_FFT, hop_length=HOP)
    magnitude_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)



    # Resynthesize from the complex Fourier representation.
    reconstructed = librosa.istft(stft, hop_length=HOP, length=len(source))
    sf.write("reconstructed.wav", reconstructed, SR)



    # Residual and objective comparison.
    residual = source - reconstructed
    sf.write("residual.wav", residual, SR)
    rmse = np.sqrt(np.mean(residual**2))
    peak = np.max(np.abs(source))
    relative_error_db = 20 * np.log10(max(np.sqrt(np.mean(residual**2)), 1e-15) / max(np.sqrt(np.mean(source**2)), 1e-15))
    print(f"Reconstruction RMSE: {rmse:.8f}")
    print(f"Relative error: {relative_error_db:.2f} dB (lower is better)")

    # Spectrum averaged over the whole recording.
    spectrum = np.mean(np.abs(stft), axis=1)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=N_FFT)
    top = np.argsort(spectrum)[-12:][::-1]
    print("\nStrongest spectral bins (approximate): ")
    for idx in top:
        print(f"{freqs[idx]:8.1f} Hz   magnitude {spectrum[idx]:.4f}")

    # Plot waveform, spectrum, and spectrogram.
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    time = np.arange(len(source)) / SR
    axes[0].plot(time[:1500], source[:1500], lw=0.8)
    axes[0].set_title("Generated source waveform (first ~34 ms)")
    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(True)

    axes[1].plot(freqs, 20 * np.log10(spectrum + 1e-12))
    axes[1].set_xlim(0, 4000)
    axes[1].set_title("Average Fourier spectrum")
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Magnitude (dB)")
    axes[1].grid(True)

    img = librosa.display.specshow(
        magnitude_db, sr=SR, hop_length=HOP, x_axis="time", y_axis="log",
        cmap="magma", ax=axes[2]
    )
    axes[2].set_title("Librosa STFT spectrogram")
    fig.colorbar(img, ax=axes[2], format="%+2.0f dB")
    fig.tight_layout()
    plt.savefig("analysis.png", dpi=150)
    plt.show()
    print("\nCreated: source.wav, reconstructed.wav, residual.wav, analysis.png")


if __name__ == "__main__":
    main()
