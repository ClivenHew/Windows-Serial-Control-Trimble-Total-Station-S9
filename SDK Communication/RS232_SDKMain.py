import time
from datetime import datetime
from pathlib import Path

import serial


ARDUINO2_PORT = "COM14"
TOTAL_STATION_PORT = "COM6"

BAUD_RATE = 9600

# At 9600 baud, one 8-N-1 byte takes approximately 1.04 ms.
# Ten milliseconds without another byte marks the end of the buffer.
BUFFER_GAP = 0.010

POLL_INTERVAL = 0.0005

LOG_DIRECTORY = Path(
    r"C:\Users\clive\OneDrive\Desktop\Serial Communication Data Packets"
)


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def format_bytes(data):
    return ", ".join(f"0x{byte:02X}" for byte in data)


def log_data(log_file, direction, data):
    formatted_data = format_bytes(data)

    line = (
        f"[{timestamp()}] [{direction}] "
        f"{len(data)} byte(s): {formatted_data}"
    )

    print(line, flush=True)
    log_file.write(line + "\n")
    log_file.flush()


def open_serial_port(port_name):
    return serial.Serial(
        port=port_name,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0,
        write_timeout=2,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )


def forward_complete_buffer(
    buffer,
    destination,
    direction,
    log_file,
):
    if not buffer:
        return

    # Convert the complete bytearray into one immutable bytes object.
    complete_data = bytes(buffer)

    # One write() call containing the complete buffer.
    bytes_written = destination.write(complete_data)
    destination.flush()

    log_data(log_file, direction, complete_data)

    print(
        f"  -> Wrote complete {bytes_written}-byte buffer",
        flush=True,
    )

    if bytes_written != len(complete_data):
        raise serial.SerialTimeoutException(
            f"Short write: expected {len(complete_data)} bytes, "
            f"but wrote {bytes_written} bytes"
        )

    buffer.clear()


def run_bridge():
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    log_filename = (
        LOG_DIRECTORY
        / f"BridgeLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    print(f"Logging to: {log_filename}")

    try:
        with open(
            log_filename,
            "a",
            encoding="utf-8",
            buffering=1,
        ) as log_file:
            with open_serial_port(ARDUINO2_PORT) as arduino2_serial, \
                    open_serial_port(TOTAL_STATION_PORT) as station_serial:

                print(
                    f"Arduino 2 opened on {ARDUINO2_PORT}, "
                    f"{BAUD_RATE} baud, 8-N-1"
                )

                print(
                    f"Total station opened on {TOTAL_STATION_PORT}, "
                    f"{BAUD_RATE} baud, 8-N-1"
                )

                print("Bridge started. Press Ctrl+C to stop.")

                arduino_buffer = bytearray()
                station_buffer = bytearray()

                arduino_last_byte_time = None
                station_last_byte_time = None

                while True:
                    now = time.monotonic()

                    # -------------------------------------------------------
                    # Arduino 2 -> Total station
                    # -------------------------------------------------------

                    arduino_waiting = arduino2_serial.in_waiting

                    if arduino_waiting > 0:
                        received = arduino2_serial.read(arduino_waiting)

                        if received:
                            arduino_buffer.extend(received)
                            arduino_last_byte_time = time.monotonic()

                    if (
                        arduino_buffer
                        and arduino_last_byte_time is not None
                        and now - arduino_last_byte_time >= BUFFER_GAP
                    ):
                        forward_complete_buffer(
                            arduino_buffer,
                            station_serial,
                            "ARDUINO2->TS",
                            log_file,
                        )

                        arduino_last_byte_time = None

                    # -------------------------------------------------------
                    # Total station -> Arduino 2
                    # -------------------------------------------------------

                    station_waiting = station_serial.in_waiting

                    if station_waiting > 0:
                        received = station_serial.read(station_waiting)

                        if received:
                            station_buffer.extend(received)
                            station_last_byte_time = time.monotonic()

                    if (
                        station_buffer
                        and station_last_byte_time is not None
                        and now - station_last_byte_time >= BUFFER_GAP
                    ):
                        forward_complete_buffer(
                            station_buffer,
                            arduino2_serial,
                            "TS->ARDUINO2",
                            log_file,
                        )

                        station_last_byte_time = None

                    time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopped Arduino2 <-> Total Station bridge")

    except serial.SerialException as error:
        print(f"\nSerial error: {error}")

    except OSError as error:
        print(f"\nOperating-system error: {error}")


def main():
    while True:
        print("\n--- Menu ---")
        print("30: Start Arduino2 <-> Total Station bridge")
        print("1000: Exit program")

        choice = input("Enter your choice: ").strip()

        if choice == "30":
            run_bridge()

        elif choice == "1000":
            print("Exiting program")
            break

        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()