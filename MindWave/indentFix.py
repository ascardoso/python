import serial
import time

PORT = "/dev/cu.MindWaveMobile"
BAUD = 57600

BANDS = [
    "Delta",
    "Theta",
    "Low Alpha",
    "High Alpha",
    "Low Beta",
    "High Beta",
    "Low Gamma",
    "Mid Gamma"
]

def read_packet(ser):
    while True:
        if ser.read(1) != b'\xAA':
            continue
        if ser.read(1) == b'\xAA':
            break

    length_data = ser.read(1)
    if not length_data:
        return None

    length = length_data[0]

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


def decode_packet(payload):
    i = 0
    result = {}

    while i < len(payload):
        code = payload[i]
        i += 1

        if code >= 0x80:
            if i >= len(payload):
                break

            value_length = payload[i]
            i += 1

            if i + value_length > len(payload):
                break

            value = payload[i:i + value_length]
            i += value_length

        else:
            value_length = 1

            if i >= len(payload):
                break

            value = payload[i:i + 1]
            i += 1

        if code == 0x02:
            result["signal_quality"] = value[0]

        elif code == 0x80 and value_length == 2:
            result["raw_eeg"] = int.from_bytes(
                value, "big", signed=True
            )

        elif code == 0x83 and value_length == 24:
            powers = []

            for j in range(0, 24, 3):
                power = int.from_bytes(
                    value[j:j+3], "big"
                )
                powers.append(power)

            result["bands"] = dict(zip(BANDS, powers))

        elif code == 0x04:
            result["attention"] = value[0]

        elif code == 0x05:
            result["meditation"] = value[0]

    return result


print("Connecting to MindWave...")
print("Listening for EEG data...\n")

signal_quality = None

with serial.Serial(PORT, BAUD, timeout=2) as ser:

    try:
        while True:

            packet = read_packet(ser)

            if packet is None:
                continue

            data = decode_packet(packet)

            if not data:
                continue

            timestamp = time.strftime("%H:%M:%S")

#            print(f"\n[{timestamp}]")

            if "signal_quality" in data:
                signal_quality = data["signal_quality"]

                print(f"Signal quality: {signal_quality}")

                if signal_quality == 0:
                    print("CONTACT GOOD")
                elif signal_quality == 200:
                    print("NO USABLE SIGNAL")
                else:
                    print("CONTACT POOR")

            if "raw_eeg" in data:
#                print(f"Raw EEG: {data['raw_eeg']}")
                 pass

            if "bands" in data:

                if signal_quality == 0:
                    print("EEG Power:")

                    for band, value in data["bands"].items():
                        print(f"  {band:12}: {value}")

                else:
                    print("EEG data ignored: signal quality insufficient")

            if "attention" in data:
                print(f"Attention: {data['attention']}")

            if "meditation" in data:
                print(f"Meditation: {data['meditation']}")

    except KeyboardInterrupt:
        print("\nStopped.")

