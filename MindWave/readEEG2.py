
import serial
import time
import struct

PORT = "/dev/tty.usbserial-A101249V"
BAUD = 57600

SYNC = b"\xA5\x5A"
PACKET_SIZE = 17

ser = serial.Serial(PORT, BAUD, timeout=0.1)

buffer = bytearray()
last_counter = None
frames = 0
start_time = time.monotonic()

print("OpenEEG P2 decoder")
print("Counter | Ch1  Ch2  Ch3  Ch4  Ch5  Ch6 | Status")

try:
    while True:
        chunk = ser.read(256)
        buffer.extend(chunk)

        while True:
            pos = buffer.find(SYNC)

            if pos < 0:
                # Preserve a possible partial sync byte
                if buffer[-1:] == b"\xA5":
                    buffer[:] = b"\xA5"
                else:
                    buffer.clear()
                break

            if pos > 0:
                del buffer[:pos]

            if len(buffer) < PACKET_SIZE:
                break

            packet = buffer[:PACKET_SIZE]

            if packet[2] != 0x02:
                del buffer[0]
                continue

            counter = packet[3]

            channels = struct.unpack(
                ">6H", packet[4:16]
            )

            status = packet[16]

            if last_counter is not None:
                expected = (last_counter + 1) & 0xFF
                if counter != expected:
                    print(
                        f"\nWARNING: frame gap "
                        f"{last_counter:02X} -> {counter:02X}"
                    )

            last_counter = counter
            frames += 1

            print(
                f"{counter:02X}      | "
                + " ".join(f"{v:4d}" for v in channels)
                + f" | {status:02X}"
            )

            del buffer[:PACKET_SIZE]

except KeyboardInterrupt:
    elapsed = time.monotonic() - start_time
    print(f"\nFrames: {frames}")
    print(f"Elapsed: {elapsed:.2f}s")
    if elapsed:
        print(f"Frame rate: {frames / elapsed:.2f} Hz")

finally:
    ser.close()

