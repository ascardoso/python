
import serial

PORT = "/dev/cu.MindWaveMobile"
BAUD = 57600

def read_packet(ser):
    # Find packet synchronization
    while True:
        if ser.read(1) != b'\xAA':
            continue
        if ser.read(1) == b'\xAA':
            break

    length = ser.read(1)
    if not length:
        return None

    length = length[0]

    if length > 169:
        return None

    payload = ser.read(length)
    checksum = ser.read(1)

    if len(payload) != length or len(checksum) != 1:
        return None

    expected = (~sum(payload)) & 0xFF

    if checksum[0] != expected:
        return None

    return payload

print("Listening to MindWave...")

with serial.Serial(PORT, BAUD, timeout=2) as ser:
    try:
        while True:
            packet = read_packet(ser)

            if packet is not None:
                print("VALID PACKET:", packet.hex(" "))
    except KeyboardInterrupt:
        print("\nStopped.")

