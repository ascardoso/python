# Fourier Lab – Audio Generation & STFT Analysis

**fourier_lab.py** is a lightweight Python script that:

1. Synthesises an instrument‑like tone with harmonics, vibrato and a realistic envelope.  
2. Performs a complex Short‑Time Fourier Transform (STFT) with **librosa**.  
3. Re‑renders the audio from the STFT, compares it to the original, and saves a residual.  
4. Prints key metrics (RMSE, relative error) and the 12 strongest spectral bins.  
5. Generates a PNG visualisation of waveform, averaged spectrum and the full STFT spectrogram.

The script is fully self‑contained – no external data files are required.

---

## 📥 Installation

1. **Clone or download** the repository (or copy `fourier_lab.py` into any folder).

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows:  venv\Scripts\activate
   ```

3. **Install the dependencies**:

   ```bash
   pip install --upgrade pip
   pip install numpy matplotlib librosa soundfile
   ```

> **Note**  
> `soundfile` (PySoundFile) requires the `libsndfile` library.  
> On Debian/Ubuntu: `sudo apt-get install libsndfile1`.  
> On macOS: `brew install libsndfile`.

---

## 🚀 Usage

Run the script from a terminal:

```bash
python fourier_lab.py
```

The script will create the following files in the current directory:

| File | Purpose |
|------|---------|
| `source.wav` | The original synthetic tone (≈3.5 s). |
| `reconstructed.wav` | STFT‑based reconstruction (should be indistinguishable from the source). |
| `residual.wav` | Difference between source and reconstruction (ideally silence). |
| `analysis.png` | Plot containing: waveform, average spectrum, and STFT spectrogram. |

During execution you’ll see console output similar to:

```
Reconstruction RMSE: 0.00000001
Relative error: -200.00 dB (lower is better)

Strongest spectral bins (approximate):
   220.0 Hz   magnitude 1.0000
   440.0 Hz   magnitude 0.5800
   ...
Created: source.wav, reconstructed.wav, residual.wav, analysis.png
```

---

## 📊 What the script does in detail

| Step | Code section | Description |
|------|--------------|-------------|
| 1. **Generate tone** | `make_test_sound()` | Combines a base frequency (220 Hz) with harmonics, a vibrato effect and an ADSR‑style envelope. |
| 2. **Write source** | `sf.write("source.wav", source, SR)` | Saves the raw waveform. |
| 3. **STFT** | `librosa.stft()` | Computes a complex STFT (`n_fft=4096`, `hop_length=512`). |
| 4. **Reconstruction** | `librosa.istft()` | Inverse transform to time domain; saved as `reconstructed.wav`. |
| 5. **Error metrics** | RMSE & relative error in dB | Quantifies reconstruction fidelity. |
| 6. **Spectral analysis** | `np.mean(np.abs(stft), axis=1)` | Averages magnitude over time; prints the 12 highest bins. |
| 7. **Plotting** | `matplotlib` + `librosa.display.specshow()` | Creates a three‑panel figure (`analysis.png`). |

---

## 🎛️ Tweaking the script

| Parameter | Default | How to change |
|-----------|---------|---------------|
| `SR` | 44100 Hz | Modify the global constant. |
| `DURATION` | 3.5 s | Change in the constants section or via command‑line argument (future extension). |
| `N_FFT` | 4096 | Alters frequency resolution. |
| `HOP` | 512 | Controls time resolution of the STFT. |

Feel free to experiment – e.g., try a different base frequency, add more harmonics, or adjust the envelope.

---

## 🧪 Why this is useful

* **Educational** – see how a complex signal can be fully described by its Fourier coefficients and perfectly reconstructed.  
* **Debugging** – residual wav file allows you to verify that no data was lost during the STFT/ISTFT pipeline.  
* **Visualization** – the spectrogram and averaged spectrum help you understand the frequency content of your synthetic tone.

---

## 📄 License

This script is released under the MIT license. Feel free to adapt, extend or redistribute it.

---

## 🙏 Acknowledgements

* **librosa** – for a convenient STFT implementation.  
* **soundfile** – cross‑platform audio I/O.  
* **matplotlib & librosa.display** – for quick plotting.

Happy listening!