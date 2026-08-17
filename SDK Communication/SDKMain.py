import serial
from datetime import datetime

with serial.Serial('COM9', baudrate=9600, timeout=1) as arduinoSerial, \
        serial.Serial('COM22', baudrate=9600, timeout=1) as trimbleSerial:

    status = "0"

    while True:
        match status:
            #Main Menu
            case "0":
                print("\n--- Menu ---")
                print("10: Read data from Arduino")
                print("30: Connect with Trimble device with SDK")
                print("1000: Exit program")

                status = input("Enter your choice: ")

            #Print the data received from the Arduino
            case "10":
                try:
                    while True:
                        #Check if there is data available to read from the Arduino
                        if arduinoSerial.in_waiting > 0:
                            arduinoData = arduinoSerial.readline()
                            print("Data received from Arduino:", arduinoData)

                        #Check if there is data available to read from the Trimble device
                        if trimbleSerial.in_waiting > 0:
                            trimbleData = trimbleSerial.readline()
                            print("Data received from Trimble:", trimbleData)

                #When serial connection is lost, break out of loop
                except serial.SerialException:
                    print("Serial connection lost.")
                    break

                #When Ctrl+C is pressed, exit the loop and return to the main menu
                except KeyboardInterrupt:
                    print("Stop Arduino Data Reading")
                    status = "0"

            #Connect with Trimble device with SDK
            #Read data from the Trimble device and send it to the Arduino.
            #Read data from the Arduino device and send it to the Trimble device.
            case "30":
                trimbleConnection = False
                log_filename = f"C:/Users/clive/OneDrive/Desktop/Serial Communication Data Packets/TrimbleLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                print(f"Logging to: {log_filename}")

                challengeHeader = b'\x12\x0C\x00\x02\x01\xA0\x80\x00'
                responseHeader = b'\x13\x0B\x00\x01\x02\xA1\x40'

                trimbleBuffer = bytearray()
                arduinoBuffer = bytearray()

                try:
                    with open(log_filename, "a") as log_file:
                        while True:
                            #Check if there is data available to read from the Trimble device
                            if trimbleSerial.in_waiting > 0:
                                #Raw Data
                                trimbleRawData = trimbleSerial.read(trimbleSerial.in_waiting)
                                trimbleBuffer.extend(trimbleRawData)

                                #Print Data. Convert each individual byte into a '0xXX' formatted string
                                trimblePrintData = [f"0x{b:02X}" for b in trimbleRawData]
                                #Join them together separated by a space
                                trimbleFormattedPrintData = ", ".join(trimblePrintData)
                                #Print in console
                                print("Data received from Trimble:", trimbleFormattedPrintData)

                                #Log to text file
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                line = f"[{timestamp}] [TRIMBLE] {trimbleFormattedPrintData}"
                                print(line)
                                log_file.write(line + "\n")
                                log_file.flush()

                                #Write the data received from the Trimble device back to the Arduino
                                arduinoSerial.write(trimbleRawData)

                            #Check if there is data available to read from the Arduino device
                            if arduinoSerial.in_waiting > 0:
                                #Raw Data
                                arduinoData = arduinoSerial.read(arduinoSerial.in_waiting)
                                arduinoBuffer.extend(arduinoData)

                                #Print Data. Convert each individual byte into a '0xXX' formatted string
                                arduinoPrintData = [f"0x{b:02X}" for b in arduinoData]
                                # Join them together separated by a space
                                arduinoFormattedPrintData = ", ".join(arduinoPrintData)
                                #Print in console
                                print("Data received from Arduino:", arduinoFormattedPrintData)

                                #Log to text file
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                line = f"[{timestamp}] [SDK] {arduinoFormattedPrintData}"
                                print(line)
                                log_file.write(line + "\n")
                                log_file.flush()

                                #Write the data received from the Arduino device back to the Trimble device
                                trimbleSerial.write(arduinoData)

                #When serial connection is lost, break out of loop
                except serial.SerialException:
                    print("Serial connection lost.")
                    break

                #When Ctrl+C is pressed, exit the loop and return to the main menu
                except KeyboardInterrupt:
                    print("Stop Trimble Data Reading")
                    status = "0"

            #Exit the program
            case "1000":
                print("Exiting program")
                status = "0"
                break