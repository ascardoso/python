
import serial
import time

PORT = "/dev/cu.MindWaveMobile"

with serial.Serial(PORT, 57600, timeout=1) as ser:
    print("Listening...")

    start = time.time()
    count = 0

    while time.time() - start < 10:
        data = ser.read(64)

        if data:
            count += len(data)
            print(data.hex(" "))

    print(f"\nReceived {count} bytes in 10 seconds.")

