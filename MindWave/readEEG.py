
import serial
import time

PORT = "/dev/tty.usbserial-A101249V"

ser = serial.Serial(
    PORT,
    baudrate=57600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

print("Listening for OpenEEG P2...")
print("Press Ctrl+C to stop.")

try:
    while True:
        data = ser.read(17)

        if data:
            print(data.hex(" "))
except KeyboardInterrupt:
    pass
finally:
    ser.close()


