import serial
import time
from datetime import datetime

# --- Port configuration ---
ARDUINO2_PORT = 'COM14'      # Arduino 2 (relay from Arduino 1 / SDK chain)
TOTAL_STATION_PORT = 'COM6'  # Leica total station
ARDUINO2_BAUD_RATE = 9600    # Must match the Arduino2 sketch
TOTAL_STATION_BAUD_RATE = 115200

with serial.Serial(ARDUINO2_PORT, baudrate=ARDUINO2_BAUD_RATE, timeout=1) as arduinoSerial, \
     serial.Serial(TOTAL_STATION_PORT, baudrate=TOTAL_STATION_BAUD_RATE, timeout=1) as totalStationSerial:

    status = "0"

    while True:
        match status:
            # Main Menu
            case "0":
                print("\n--- Menu ---")
                print("30: Start Arduino2 <-> Total Station bridge")
                print("1000: Exit program")

                status = input("Enter your choice: ")

            # Bridge Arduino 2 (COM14) <-> Total Station (COM6)
            # Read data from Arduino 2 and forward it to the Total Station.
            # Read data from the Total Station and forward it back to Arduino 2.
            case "30":
                log_filename = f"C:/Users/clive/OneDrive/Desktop/Serial Communication Data Packets/BridgeLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                print(f"Logging to: {log_filename}")

                try:
                    with open(log_filename, "a") as log_file:
                        while True:
                            # Data coming from Arduino 2 -> forward to Total Station
                            if arduinoSerial.in_waiting > 0:
                                data = arduinoSerial.read(arduinoSerial.in_waiting)

                                formattedData = ", ".join(f"0x{b:02X}" for b in data)
                                print("Data received from Arduino2:", formattedData)

                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                line = f"[{timestamp}] [ARDUINO2->TS] {formattedData}"
                                log_file.write(line + "\n")
                                log_file.flush()

                                totalStationSerial.write(data)

                            # Data coming from Total Station -> forward to Arduino 2
                            if totalStationSerial.in_waiting > 0:
                                data = totalStationSerial.read(totalStationSerial.in_waiting)

                                formattedData = ", ".join(f"0x{b:02X}" for b in data)
                                print("Data received from Total Station:", formattedData)

                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                line = f"[{timestamp}] [TS->ARDUINO2] {formattedData}"
                                log_file.write(line + "\n")
                                log_file.flush()

                                arduinoSerial.write(data)

                # When either serial connection is lost, break out of loop
                except serial.SerialException:
                    print("Serial connection lost.")
                    break

                # When Ctrl+C is pressed, return to the main menu
                except KeyboardInterrupt:
                    print("Stopped Arduino2 <-> Total Station bridge")
                    status = "0"

            # Exit the program
            case "1000":
                print("Exiting program")
                break