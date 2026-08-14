import serial
import time

HANDSHAKE = bytes([
    0xFF, 0xC0,
    0x0B, 0x0C, 0x00, 0x00, 0x00, 0x09,
    0x00, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
])

with serial.Serial(
    port="/dev/rfcomm0",
    baudrate=9600,
    timeout=0.1,
    write_timeout=2
) as trimbleSerial:

    print("Port opened.")
    print("Sending:", HANDSHAKE.hex(" "))

    written = trimbleSerial.write(HANDSHAKE)
    trimbleSerial.flush()

    print(f"Bytes written: {written}")

    received = bytearray()
    start_time = time.monotonic()

    while time.monotonic() - start_time < 10:
        waiting = trimbleSerial.in_waiting

        if waiting > 0:
            data = trimbleSerial.read(waiting)
            received.extend(data)
            print("Received:", data.hex(" "))

        time.sleep(0.005)

    print("Complete response:", received.hex(" "))

    if b"\x2B\x3E\x00\x00\x00\x0A\x00" in received:
        print("Handshake acknowledgement found.")
    else:
        print("Handshake acknowledgement not found.")