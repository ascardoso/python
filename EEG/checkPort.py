import serial, numpy as np
from scipy.signal import iirnotch, butter, tf2sos, sosfilt

FS = 256
MAINS = 60.0

last_phase = None

# Filter: 60 Hz notch followed by a 1-40 Hz band-pass
b, a = iirnotch(MAINS, Q=30, fs=FS)
sos = np.vstack([tf2sos(b, a),
                 butter(4, [1, 40], btype='bandpass', fs=FS, output='sos')])
zi = [np.zeros((sos.shape[0], 2)) for _ in range(2)]   # filter memory, one per channel

ser = serial.Serial('/dev/cu.usbserial-A101249V', 57600, timeout=1)
buf, win, seconds = bytearray(), [], 0
f = np.fft.rfftfreq(FS, 1/FS)

while True:
    buf += ser.read(64)
    while len(buf) >= 17:
        if buf[0] == 0xA5 and buf[1] == 0x5A:
            p = bytes(buf[:17]); del buf[:17]
            win.append([p[4+2*i]*256 + p[5+2*i] for i in range(2)])
            if len(win) == FS:                          # one second of data
                x = np.array(win, float); win = []
                seconds += 1
                phase = ("settle" if seconds < 30 else "OPEN  " if seconds < 50
            else "CLOSED" if seconds < 70 else "OPEN  " if seconds < 90 else "done  ")
                if phase != last_phase:
                    print("\a", end="")      # terminal bell at each change, if your terminal allows it
                    last_phase = phase
                for c in range(2):
                    raw = x[:, c]
                    rail = np.mean((raw <= 2) | (raw >= 1021)) * 100

                    # filter (keeps its state from one second to the next)
                    y, zi[c] = sosfilt(sos, raw - 512, zi=zi[c])

                    if seconds < 5:                      # let the filter settle
                        continue

                    r = raw - raw.mean()
                    Pr = np.abs(np.fft.rfft(r * np.hanning(FS)))**2
                    Py = np.abs(np.fft.rfft(y * np.hanning(FS)))**2
                    band = (f >= 45) & (f <= 65)
                    line = f[band][Pr[band].argmax()]
                    h = (f >= MAINS-1) & (f <= MAINS+1)
                    alpha = Py[(f >= 8) & (f < 13)].sum()
                    flag = "  BAD (clipping)" if rail > 5 else ""
                    print(f"t={seconds:3d} {phase} ch{c+1} std {y.std():6.1f} rails {rail:3.0f}% "
                          f"alpha {alpha:.1e} hum {Pr[h].sum():.1e} -> {Py[h].sum():.1e} "
                          f"line {line:.0f} Hz{flag}")
                if seconds >= 5:
                    print()
        else:
            del buf[0]

