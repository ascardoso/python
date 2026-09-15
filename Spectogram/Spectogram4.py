"""
HARMONIC ANALYZER
=================

Features
--------
- WAV file loading
- Large high-contrast spectrogram
- FFT spectrum
- Fundamental frequency (F0)
- Numbered harmonics
- Harmonic table
- Time/frequency zoom
- Mouse wheel zoom
- Mouse drag/pan
- Preset frequency buttons

Install:
    pip install numpy scipy matplotlib

Run:
    python harmonic_analyzer.py
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class HarmonicAnalyzer:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Harmonic Analyzer"
        )

        self.root.geometry(
            "1400x1000"
        )

        self.root.minsize(
            1100,
            750
        )

        # =====================================================
        # Use a ttk theme that permits custom colors.
        # This fixes white buttons on macOS/Aqua.
        # =====================================================

        self.style = ttk.Style()

        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # =====================================================
        # Data
        # =====================================================

        self.audio = None
        self.sample_rate = None
        self.filename = None

        self.f0 = None
        self.harmonics = []

        self.fft_frequencies = None
        self.fft_magnitude = None

        # =====================================================
        # Mouse state
        # =====================================================

        self.dragging = False
        self.drag_start = None

        # =====================================================
        # Build UI
        # =====================================================

        self.create_ui()

    # =========================================================
    # UI
    # =========================================================

    def create_ui(self):

        # -----------------------------------------------------
        # Button styles
        # -----------------------------------------------------

        self.style.configure(
            "Blue.TButton",
            font=("Arial", 10, "bold"),
            foreground="white",
            background="#1565c0",
            padding=(12, 6)
        )

        self.style.map(
            "Blue.TButton",
            foreground=[
                ("pressed", "white"),
                ("active", "white")
            ],
            background=[
                ("pressed", "#0d47a1"),
                ("active", "#1976d2")
            ]
        )

        self.style.configure(
            "Gray.TButton",
            font=("Arial", 10, "bold"),
            foreground="white",
            background="#546e7a",
            padding=(12, 6)
        )

        self.style.map(
            "Gray.TButton",
            foreground=[
                ("pressed", "white"),
                ("active", "white")
            ],
            background=[
                ("pressed", "#37474f"),
                ("active", "#607d8b")
            ]
        )

        self.style.configure(
            "Preset.TButton",
            font=("Arial", 9),
            foreground="#263238",
            background="#cfd8dc",
            padding=(8, 5)
        )

        self.style.map(
            "Preset.TButton",
            foreground=[
                ("pressed", "white"),
                ("active", "white")
            ],
            background=[
                ("pressed", "#455a64"),
                ("active", "#607d68")
            ]
        )

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        header = tk.Frame(
            self.root,
            bg="#263238"
        )

        header.pack(
            fill="x"
        )

        tk.Label(
            header,
            text="HARMONIC ANALYZER",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#263238"
        ).pack(
            side="left",
            padx=18,
            pady=10
        )

        self.file_label = tk.Label(
            header,
            text="No WAV file loaded",
            font=("Arial", 10),
            fg="#cfd8dc",
            bg="#263238"
        )

        self.file_label.pack(
            side="left",
            padx=20
        )

        ttk.Button(
            header,
            text="Open WAV",
            command=self.open_file,
            style="Blue.TButton"
        ).pack(
            side="right",
            padx=15,
            pady=7
        )

        # -----------------------------------------------------
        # Information bar
        # -----------------------------------------------------

        info = tk.Frame(
            self.root,
            bg="#eceff1"
        )

        info.pack(
            fill="x"
        )

        self.f0_label = tk.Label(
            info,
            text="F₀: --- Hz",
            font=("Arial", 16, "bold"),
            fg="#0d47a1",
            bg="#eceff1"
        )

        self.f0_label.pack(
            side="left",
            padx=15,
            pady=9
        )

        self.duration_label = tk.Label(
            info,
            text="Duration: ---",
            font=("Arial", 11, "bold"),
            fg="#263238",
            bg="#eceff1"
        )

        self.duration_label.pack(
            side="left",
            padx=20
        )

        self.sample_label = tk.Label(
            info,
            text="Sample rate: ---",
            font=("Arial", 11, "bold"),
            fg="#263238",
            bg="#eceff1"
        )

        self.sample_label.pack(
            side="left",
            padx=20
        )

        self.harmonic_count_label = tk.Label(
            info,
            text="Harmonics: ---",
            font=("Arial", 11, "bold"),
            fg="#263238",
            bg="#eceff1"
        )

        self.harmonic_count_label.pack(
            side="left",
            padx=20
        )

        # -----------------------------------------------------
        # Controls
        # -----------------------------------------------------

        controls = tk.LabelFrame(
            self.root,
            text="View Controls",
            font=("Arial", 10, "bold"),
            padx=8,
            pady=5
        )

        controls.pack(
            fill="x",
            padx=10,
            pady=8
        )

        # Time start
        tk.Label(
            controls,
            text="Time start:",
            fg="#263238"
        ).grid(
            row=0,
            column=0,
            padx=(5, 3),
            pady=7
        )

        self.time_start_var = tk.StringVar(
            value="0"
        )

        tk.Entry(
            controls,
            textvariable=self.time_start_var,
            width=9
        ).grid(
            row=0,
            column=1
        )

        # Time end
        tk.Label(
            controls,
            text="Time end:",
            fg="#263238"
        ).grid(
            row=0,
            column=2,
            padx=(12, 3)
        )

        self.time_end_var = tk.StringVar(
            value="30"
        )

        tk.Entry(
            controls,
            textvariable=self.time_end_var,
            width=9
        ).grid(
            row=0,
            column=3
        )

        # Frequency minimum
        tk.Label(
            controls,
            text="Frequency min:",
            fg="#263238"
        ).grid(
            row=0,
            column=4,
            padx=(15, 3)
        )

        self.freq_min_var = tk.StringVar(
            value="0"
        )

        tk.Entry(
            controls,
            textvariable=self.freq_min_var,
            width=9
        ).grid(
            row=0,
            column=5
        )

        # Frequency maximum
        tk.Label(
            controls,
            text="Frequency max:",
            fg="#263238"
        ).grid(
            row=0,
            column=6,
            padx=(12, 3)
        )

        self.freq_max_var = tk.StringVar(
            value="5000"
        )

        tk.Entry(
            controls,
            textvariable=self.freq_max_var,
            width=9
        ).grid(
            row=0,
            column=7
        )

        # -----------------------------------------------------
        # Apply / Reset
        # -----------------------------------------------------

        ttk.Button(
            controls,
            text="Apply Zoom",
            command=self.apply_zoom,
            style="Blue.TButton"
        ).grid(
            row=0,
            column=8,
            padx=12
        )

        ttk.Button(
            controls,
            text="Reset",
            command=self.reset_view,
            style="Gray.TButton"
        ).grid(
            row=0,
            column=9,
            padx=4
        )

        # -----------------------------------------------------
        # Frequency presets
        # -----------------------------------------------------

        presets = [
            ("0–1 kHz", 1000),
            ("0–2 kHz", 2000),
            ("0–5 kHz", 5000),
            ("0–10 kHz", 10000)
        ]

        for i, (label, maximum) in enumerate(
            presets,
            start=10
        ):

            ttk.Button(
                controls,
                text=label,
                command=lambda m=maximum:
                    self.set_frequency(0, m),
                style="Preset.TButton"
            ).grid(
                row=0,
                column=i,
                padx=2
            )

        # -----------------------------------------------------
        # Plot frame
        # -----------------------------------------------------

        plot_frame = tk.Frame(
            self.root,
            bg="white"
        )

        plot_frame.pack(
            fill="both",
            expand=True,
            padx=10
        )

        # -----------------------------------------------------
        # Figure
        # -----------------------------------------------------

        self.figure = Figure(
            figsize=(13, 9),
            dpi=100,
            facecolor="white"
        )

        # Spectrogram gets ~65% of vertical space.
        self.ax_spec = self.figure.add_subplot(
            2,
            1,
            1
        )

        self.ax_fft = self.figure.add_subplot(
            2,
            1,
            2
        )

        self.figure.subplots_adjust(
            left=0.075,
            right=0.985,
            top=0.965,
            bottom=0.075,
            hspace=0.32
        )

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=plot_frame
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        # -----------------------------------------------------
        # Harmonic table
        # -----------------------------------------------------

        table_frame = tk.LabelFrame(
            self.root,
            text="Detected Harmonics",
            font=("Arial", 10, "bold")
        )

        table_frame.pack(
            fill="x",
            padx=10,
            pady=(5, 10)
        )

        columns = (
            "number",
            "frequency",
            "amplitude",
            "relative"
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=6
        )

        self.table.heading(
            "number",
            text="Harmonic"
        )

        self.table.heading(
            "frequency",
            text="Frequency (Hz)"
        )

        self.table.heading(
            "amplitude",
            text="Amplitude"
        )

        self.table.heading(
            "relative",
            text="Relative (dB)"
        )

        self.table.column(
            "number",
            width=100,
            anchor="center"
        )

        self.table.column(
            "frequency",
            width=160,
            anchor="center"
        )

        self.table.column(
            "amplitude",
            width=160,
            anchor="center"
        )

        self.table.column(
            "relative",
            width=160,
            anchor="center"
        )

        self.table.pack(
            fill="x",
            padx=5,
            pady=5
        )

        # -----------------------------------------------------
        # Mouse events
        # -----------------------------------------------------

        self.canvas.mpl_connect(
            "scroll_event",
            self.on_scroll
        )

        self.canvas.mpl_connect(
            "button_press_event",
            self.on_mouse_press
        )

        self.canvas.mpl_connect(
            "button_release_event",
            self.on_mouse_release
        )

        self.canvas.mpl_connect(
            "motion_notify_event",
            self.on_mouse_move
        )

    # =========================================================
    # OPEN FILE
    # =========================================================

    def open_file(self):

        filename = filedialog.askopenfilename(
            title="Open WAV File",
            filetypes=[
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:

            self.load_wav(filename)

            self.analyze()

        except Exception as exc:

            messagebox.showerror(
                "Error",
                f"Could not analyze WAV file:\n\n{exc}"
            )

    # =========================================================
    # LOAD WAV
    # =========================================================

    def load_wav(self, filename):

        sample_rate, raw = wavfile.read(
            filename
        )

        self.sample_rate = int(
            sample_rate
        )

        # Convert to float.
        if np.issubdtype(
            raw.dtype,
            np.integer
        ):

            info = np.iinfo(
                raw.dtype
            )

            scale = max(
                abs(info.min),
                info.max
            )

            audio = (
                raw.astype(np.float64)
                / scale
            )

        else:

            audio = raw.astype(
                np.float64
            )

        # Stereo -> mono.
        if audio.ndim > 1:

            audio = np.mean(
                audio,
                axis=1
            )

        # Remove DC.
        audio -= np.mean(
            audio
        )

        self.audio = audio
        self.filename = filename

        duration = (
            len(audio)
            / self.sample_rate
        )

        self.file_label.config(
            text=os.path.basename(
                filename
            )
        )

        self.duration_label.config(
            text=f"Duration: {duration:.2f} sec"
        )

        self.sample_label.config(
            text=(
                f"Sample rate: "
                f"{self.sample_rate:,} Hz"
            )
        )

        # Initial view.
        self.time_start_var.set(
            "0"
        )

        self.time_end_var.set(
            f"{min(duration, 30):.2f}"
        )

        default_max = min(
            5000,
            self.sample_rate / 2
        )

        self.freq_min_var.set(
            "0"
        )

        self.freq_max_var.set(
            f"{default_max:.0f}"
        )

        self.default_frequency_max = (
            default_max
        )

    # =========================================================
    # ANALYZE
    # =========================================================

    def analyze(self):

        fs = self.sample_rate

        if self.audio is None:
            return

        # Use approximately one second.
        analysis_length = min(
            len(self.audio),
            int(fs)
        )

        if analysis_length < 2048:

            raise ValueError(
                "Recording is too short."
            )

        # Find loudest section.
        if len(self.audio) > analysis_length:

            best_start = 0
            best_energy = -np.inf

            step = max(
                1,
                analysis_length // 4
            )

            for start in range(
                0,
                len(self.audio)
                - analysis_length
                + 1,
                step
            ):

                block = self.audio[
                    start:
                    start + analysis_length
                ]

                energy = np.mean(
                    block ** 2
                )

                if energy > best_energy:

                    best_energy = energy
                    best_start = start

            segment = self.audio[
                best_start:
                best_start + analysis_length
            ]

        else:

            segment = self.audio

        # -----------------------------------------------------
        # FFT
        # -----------------------------------------------------

        n = len(segment)

        window = np.hanning(
            n
        )

        spectrum = np.fft.rfft(
            segment * window
        )

        frequencies = np.fft.rfftfreq(
            n,
            1 / fs
        )

        magnitude = np.abs(
            spectrum
        )

        magnitude *= (
            2
            / np.sum(window)
        )

        magnitude[0] = 0

        self.fft_frequencies = frequencies
        self.fft_magnitude = magnitude

        # -----------------------------------------------------
        # F0
        # -----------------------------------------------------

        self.f0 = self.find_fundamental(
            frequencies,
            magnitude
        )

        if self.f0 is None:

            self.f0_label.config(
                text="F₀: Not detected"
            )

            return

        # -----------------------------------------------------
        # Harmonics
        # -----------------------------------------------------

        self.harmonics = (
            self.find_harmonics(
                self.f0,
                frequencies,
                magnitude
            )
        )

        self.f0_label.config(
            text=f"F₀: {self.f0:.2f} Hz"
        )

        self.harmonic_count_label.config(
            text=(
                f"Harmonics: "
                f"{len(self.harmonics)}"
            )
        )

        self.update_table()

        self.draw_plots()

    # =========================================================
    # FUNDAMENTAL DETECTION
    # =========================================================

    def find_fundamental(
        self,
        frequencies,
        magnitude
    ):

        fs = self.sample_rate

        min_f0 = 50
        max_f0 = min(
            2000,
            fs / 2
        )

        mask = (
            (frequencies >= min_f0)
            &
            (frequencies <= max_f0)
        )

        f = frequencies[mask]
        mag = magnitude[mask]

        if len(f) == 0:
            return None

        prominence = max(
            np.max(mag) * 0.01,
            1e-12
        )

        peaks, _ = find_peaks(
            mag,
            prominence=prominence
        )

        if len(peaks) == 0:

            return f[
                np.argmax(mag)
            ]

        candidates = f[peaks]

        best = None
        best_score = -np.inf

        for candidate in candidates:

            score = 0

            for harmonic in range(
                1,
                12
            ):

                target = (
                    candidate
                    * harmonic
                )

                if target >= fs / 2:
                    break

                tolerance = max(
                    candidate * 0.025,
                    fs
                    / len(magnitude)
                    * 2
                )

                nearby = (
                    np.abs(
                        frequencies
                        - target
                    )
                    <= tolerance
                )

                if np.any(nearby):

                    strength = np.max(
                        magnitude[nearby]
                    )

                    score += (
                        strength
                        / np.sqrt(
                            harmonic
                        )
                    )

            index = np.argmin(
                np.abs(
                    frequencies
                    - candidate
                )
            )

            score += (
                magnitude[index]
                * 0.2
            )

            if score > best_score:

                best_score = score
                best = candidate

        return best

    # =========================================================
    # HARMONICS
    # =========================================================

    def find_harmonics(
        self,
        f0,
        frequencies,
        magnitude
    ):

        result = []

        fundamental_index = np.argmin(
            np.abs(
                frequencies
                - f0
            )
        )

        reference = magnitude[
            fundamental_index
        ]

        if reference <= 0:
            reference = 1e-12

        for number in range(
            1,
            41
        ):

            target = (
                f0 * number
            )

            if target >= frequencies[-1]:
                break

            tolerance = max(
                f0 * 0.035,
                frequencies[1] * 2
            )

            indices = np.where(
                np.abs(
                    frequencies
                    - target
                )
                <= tolerance
            )[0]

            if len(indices) == 0:
                continue

            best_index = indices[
                np.argmax(
                    magnitude[indices]
                )
            ]

            amplitude = magnitude[
                best_index
            ]

            if amplitude < (
                reference * 0.002
            ):
                continue

            frequency = frequencies[
                best_index
            ]

            db = (
                20
                * np.log10(
                    max(
                        amplitude
                        / reference,
                        1e-12
                    )
                )
            )

            result.append(
                (
                    number,
                    frequency,
                    amplitude,
                    db
                )
            )

        return result

    # =========================================================
    # DRAW
    # =========================================================

    def draw_plots(self):

        if self.audio is None:
            return

        self.ax_spec.clear()
        self.ax_fft.clear()

        fs = self.sample_rate

        # -----------------------------------------------------
        # Current view
        # -----------------------------------------------------

        time_start = float(
            self.time_start_var.get()
        )

        time_end = float(
            self.time_end_var.get()
        )

        freq_min = float(
            self.freq_min_var.get()
        )

        freq_max = float(
            self.freq_max_var.get()
        )

        duration = (
            len(self.audio)
            / fs
        )

        nyquist = fs / 2

        time_start = max(
            0,
            min(
                time_start,
                duration
            )
        )

        time_end = max(
            time_start + 0.01,
            min(
                time_end,
                duration
            )
        )

        freq_min = max(
            0,
            freq_min
        )

        freq_max = min(
            nyquist,
            max(
                freq_min + 1,
                freq_max
            )
        )

        # -----------------------------------------------------
        # Spectrogram
        # -----------------------------------------------------

        start_sample = int(
            time_start * fs
        )

        end_sample = int(
            time_end * fs
        )

        audio_view = self.audio[
            start_sample:end_sample
        ]

        if len(audio_view) < 256:

            audio_view = self.audio

            time_start = 0
            time_end = duration

        # Choose FFT size.
        nfft = min(
            4096,
            len(audio_view)
        )

        nfft = 2 ** int(
            np.floor(
                np.log2(nfft)
            )
        )

        nfft = max(
            256,
            nfft
        )

        nfft = min(
            nfft,
            len(audio_view)
        )

        noverlap = int(
            nfft * 0.80
        )

        # -----------------------------------------------------
        # Important:
        #
        # specgram draws an image covering the exact time and
        # frequency coordinates. Therefore set_xlim/set_ylim
        # below actually zoom into the image.
        # -----------------------------------------------------

        self.ax_spec.specgram(
            audio_view,
            NFFT=nfft,
            Fs=fs,
            noverlap=noverlap,
            cmap="magma",
            scale="dB"
        )

        self.ax_spec.set_xlim(
            time_start,
            time_end
        )

        self.ax_spec.set_ylim(
            freq_min,
            freq_max
        )

        self.ax_spec.set_title(
            "SPECTROGRAM — dB",
            fontsize=15,
            fontweight="bold"
        )

        self.ax_spec.set_xlabel(
            "Time (seconds)"
        )

        self.ax_spec.set_ylabel(
            "Frequency (Hz)"
        )

        self.ax_spec.grid(
            True,
            color="white",
            alpha=0.12
        )

        # -----------------------------------------------------
        # F0 + harmonics on spectrogram
        # -----------------------------------------------------

        if self.f0 is not None:

            if (
                freq_min
                <= self.f0
                <= freq_max
            ):

                self.ax_spec.axhline(
                    self.f0,
                    color="#00e5ff",
                    linestyle="--",
                    linewidth=2,
                    label=(
                        f"F₀ = "
                        f"{self.f0:.2f} Hz"
                    )
                )

            for (
                number,
                frequency,
                amplitude,
                db
            ) in self.harmonics:

                if (
                    freq_min
                    <= frequency
                    <= freq_max
                ):

                    self.ax_spec.axhline(
                        frequency,
                        color="white",
                        linestyle=":",
                        linewidth=0.8,
                        alpha=0.75
                    )

                    self.ax_spec.text(
                        time_start,
                        frequency,
                        f" {number} ",
                        color="white",
                        fontsize=9,
                        fontweight="bold",
                        va="center",
                        ha="left",
                        bbox={
                            "facecolor": "black",
                            "alpha": 0.6,
                            "edgecolor": "none",
                            "pad": 2
                        }
                    )

            self.ax_spec.legend(
                loc="upper right"
            )

        # -----------------------------------------------------
        # FFT
        # -----------------------------------------------------

        frequencies = (
            self.fft_frequencies
        )

        magnitude = (
            self.fft_magnitude
        )

        mask = (
            (frequencies >= freq_min)
            &
            (frequencies <= freq_max)
        )

        self.ax_fft.plot(
            frequencies[mask],
            magnitude[mask],
            color="#1565c0",
            linewidth=1.2
        )

        self.ax_fft.set_xlim(
            freq_min,
            freq_max
        )

        self.ax_fft.set_title(
            "FFT SPECTRUM",
            fontsize=14,
            fontweight="bold"
        )

        self.ax_fft.set_xlabel(
            "Frequency (Hz)"
        )

        self.ax_fft.set_ylabel(
            "Amplitude"
        )

        self.ax_fft.grid(
            True,
            alpha=0.25
        )

        # -----------------------------------------------------
        # FFT markers
        # -----------------------------------------------------

        if self.f0 is not None:

            if (
                freq_min
                <= self.f0
                <= freq_max
            ):

                self.ax_fft.axvline(
                    self.f0,
                    color="#e53935",
                    linestyle="--",
                    linewidth=2,
                    label=(
                        f"F₀ = "
                        f"{self.f0:.2f} Hz"
                    )
                )

            for (
                number,
                frequency,
                amplitude,
                db
            ) in self.harmonics:

                if (
                    freq_min
                    <= frequency
                    <= freq_max
                ):

                    self.ax_fft.axvline(
                        frequency,
                        color="#ff9800",
                        linestyle=":",
                        linewidth=1,
                        alpha=0.8
                    )

                    self.ax_fft.text(
                        frequency,
                        amplitude,
                        str(number),
                        color="#e65100",
                        fontsize=9,
                        fontweight="bold",
                        rotation=90,
                        ha="center",
                        va="bottom"
                    )

            self.ax_fft.legend()

        self.canvas.draw_idle()

    # =========================================================
    # APPLY ZOOM
    # =========================================================

    def apply_zoom(self):

        if self.audio is None:
            return

        try:

            start = float(
                self.time_start_var.get()
            )

            end = float(
                self.time_end_var.get()
            )

            fmin = float(
                self.freq_min_var.get()
            )

            fmax = float(
                self.freq_max_var.get()
            )

        except ValueError:

            messagebox.showwarning(
                "Invalid values",
                "Please enter numbers for "
                "the time and frequency ranges."
            )

            return

        duration = (
            len(self.audio)
            / self.sample_rate
        )

        nyquist = (
            self.sample_rate
            / 2
        )

        # -----------------------------------------------------
        # Validate time.
        # -----------------------------------------------------

        if start < 0:
            start = 0

        if end > duration:
            end = duration

        if end <= start:

            messagebox.showwarning(
                "Invalid time range",
                "Time end must be greater "
                "than time start."
            )

            return

        # -----------------------------------------------------
        # Validate frequency.
        # -----------------------------------------------------

        if fmin < 0:
            fmin = 0

        if fmax > nyquist:
            fmax = nyquist

        if fmax <= fmin:

            messagebox.showwarning(
                "Invalid frequency range",
                f"Frequency must be between "
                f"0 and {nyquist:.0f} Hz."
            )

            return

        # -----------------------------------------------------
        # Save cleaned values.
        # -----------------------------------------------------

        self.time_start_var.set(
            f"{start:.3f}"
        )

        self.time_end_var.set(
            f"{end:.3f}"
        )

        self.freq_min_var.set(
            f"{fmin:.1f}"
        )

        self.freq_max_var.set(
            f"{fmax:.1f}"
        )

        # -----------------------------------------------------
        # Redraw display.
        #
        # F0 and harmonic analysis are NOT changed.
        # -----------------------------------------------------

        self.draw_plots()

    # =========================================================
    # FREQUENCY PRESET
    # =========================================================

    def set_frequency(
        self,
        minimum,
        maximum
    ):

        if self.audio is None:
            return

        maximum = min(
            maximum,
            self.sample_rate / 2
        )

        self.freq_min_var.set(
            str(minimum)
        )

        self.freq_max_var.set(
            str(int(maximum))
        )

        # Actually redraw.
        self.draw_plots()

    # =========================================================
    # RESET
    # =========================================================

    def reset_view(self):

        if self.audio is None:
            return

        duration = (
            len(self.audio)
            / self.sample_rate
        )

        end = min(
            duration,
            30
        )

        maximum = min(
            self.default_frequency_max,
            self.sample_rate / 2
        )

        self.time_start_var.set(
            "0"
        )

        self.time_end_var.set(
            f"{end:.2f}"
        )

        self.freq_min_var.set(
            "0"
        )

        self.freq_max_var.set(
            f"{maximum:.0f}"
        )

        self.draw_plots()

    # =========================================================
    # MOUSE WHEEL
    # =========================================================

    def on_scroll(
        self,
        event
    ):

        if event.inaxes not in (
            self.ax_spec,
            self.ax_fft
        ):
            return

        if (
            event.xdata is None
            or event.ydata is None
        ):
            return

        # Zoom in/out.
        if event.button == "up":
            factor = 0.75
        else:
            factor = 1.33

        ax = event.inaxes

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        x = event.xdata
        y = event.ydata

        new_x_half = (
            (xlim[1] - xlim[0])
            * factor
            / 2
        )

        new_y_half = (
            (ylim[1] - ylim[0])
            * factor
            / 2
        )

        ax.set_xlim(
            x - new_x_half,
            x + new_x_half
        )

        ax.set_ylim(
            y - new_y_half,
            y + new_y_half
        )

        self.canvas.draw_idle()

    # =========================================================
    # MOUSE PRESS
    # =========================================================

    def on_mouse_press(
        self,
        event
    ):

        if event.button != 1:
            return

        if event.inaxes not in (
            self.ax_spec,
            self.ax_fft
        ):
            return

        if (
            event.xdata is None
            or event.ydata is None
        ):
            return

        self.dragging = True

        self.drag_start = (
            event.inaxes,
            event.xdata,
            event.ydata,
            event.inaxes.get_xlim(),
            event.inaxes.get_ylim()
        )

    # =========================================================
    # MOUSE RELEASE
    # =========================================================

    def on_mouse_release(
        self,
        event
    ):

        if event.button == 1:

            self.dragging = False
            self.drag_start = None

    # =========================================================
    # MOUSE DRAG
    # =========================================================

    def on_mouse_move(
        self,
        event
    ):

        if not self.dragging:
            return

        if event.inaxes is None:
            return

        if (
            event.xdata is None
            or event.ydata is None
        ):
            return

        (
            ax,
            xstart,
            ystart,
            xlim,
            ylim
        ) = self.drag_start

        dx = (
            event.xdata
            - xstart
        )

        dy = (
            event.ydata
            - ystart
        )

        ax.set_xlim(
            xlim[0] - dx,
            xlim[1] - dx
        )

        ax.set_ylim(
            ylim[0] - dy,
            ylim[1] - dy
        )

        self.canvas.draw_idle()

    # =========================================================
    # TABLE
    # =========================================================

    def update_table(self):

        for item in self.table.get_children():

            self.table.delete(
                item
            )

        for (
            number,
            frequency,
            amplitude,
            db
        ) in self.harmonics:

            self.table.insert(
                "",
                "end",
                values=(
                    number,
                    f"{frequency:.2f}",
                    f"{amplitude:.6f}",
                    f"{db:.2f}"
                )
            )


# =============================================================
# MAIN
# =============================================================

def main():

    root = tk.Tk()

    HarmonicAnalyzer(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()

