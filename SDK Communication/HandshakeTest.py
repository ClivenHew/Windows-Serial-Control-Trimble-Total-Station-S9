import time
import serial


HANDSHAKE = bytes([
    0xFF, 0xC0,
    0x0B, 0x0C, 0x00, 0x00, 0x00,
    0x09, 0x00, 0x39, 0x30,
    0x00, 0x00, 0x00, 0xC0,
])


station = serial.Serial()

station.port = "COM6"
station.baudrate = 9600
station.bytesize = serial.EIGHTBITS
station.parity = serial.PARITY_NONE
station.stopbits = serial.STOPBITS_ONE
station.timeout = 0.05
station.write_timeout = 2

station.xonxoff = False
station.rtscts = False
station.dsrdtr = False

station.rts = True
station.dtr = True
station.break_condition = False

station.open()

try:
    print("Settings:", station.get_settings())
    print(
        "Lines:",
        f"RTS={station.rts}",
        f"DTR={station.dtr}",
        f"CTS={station.cts}",
        f"DSR={station.dsr}",
        f"DCD={station.cd}",
    )

    # Allow the PL2303 and total-station connection to settle.
    time.sleep(1.0)

    station.reset_input_buffer()

    written = station.write(HANDSHAKE)
    station.flush()

    print(f"Sent {written} bytes:")
    print(", ".join(f"0x{byte:02X}" for byte in HANDSHAKE))

    response = bytearray()
    deadline = time.monotonic() + 10.0
    last_byte_time = None

    while time.monotonic() < deadline:
        waiting = station.in_waiting

        if waiting > 0:
            response.extend(station.read(waiting))
            last_byte_time = time.monotonic()

        if (
            response
            and last_byte_time is not None
            and time.monotonic() - last_byte_time >= 0.010
        ):
            break

        time.sleep(0.0005)

    if response:
        print(f"Received {len(response)} bytes:")
        print(", ".join(f"0x{byte:02X}" for byte in response))
    else:
        print("No response received from COM6.")

finally:
    station.close()