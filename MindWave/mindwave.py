import serial
import time

PORT = "/dev/cu.MindWaveMobile"
BAUD = 57600

print("Connecting to MindWave...")

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=1
)

print("Connected. Waiting for EEG packets...")

try:
    while True:
        data = ser.read(1)

        if data:
            print(f"{data[0]:02X}", end=" ", flush=True)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    ser.close()

