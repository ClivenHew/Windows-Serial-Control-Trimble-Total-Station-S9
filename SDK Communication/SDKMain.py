import serial
from datetime import datetime


print("\n--- Choose SDK Communication Method ---")
print("1: SDK RS232")
print("2: SDK Bluetooth")
sdkMethod = input("Enter your choice: ")


# RS232
if sdkMethod == "1":
    with serial.Serial('COM20', baudrate=9600, timeout=1) as arduinoSerial2, \
         serial.Serial('COM7', baudrate=9600, timeout=1) as trimbleSerial:

        status = "0"

        while True:
            match status:
                # Main Menu
                case "0":
                    print("\n--- RS232 Menu ---")
                    print("10: Send data through Arduino 1 and read Arduino 2")
                    print("30: Connect with Trimble device with SDK")
                    print("1000: Exit program")

                    status = input("Enter your choice: ")

                # Send a data string to Arduino 1 on COM19.
                # Read it from Arduino 2, then test the reverse direction.
                case "10":
                    try:
                        # The separate SDK must be closed before case 10 because
                        # this test temporarily opens its COM19 port.
                        with serial.Serial(
                            'COM19', baudrate=9600, timeout=1
                        ) as arduinoSerial1:
                            dataString = input("Enter the data string to send: ")
                            dataToSend = dataString.encode()

                            # Arduino 1 -> Arduino 2
                            arduinoSerial2.reset_input_buffer()
                            arduinoSerial1.write(dataToSend)
                            arduinoSerial1.flush()
                            print("Data sent to Arduino 1:", dataString)

                            arduino2Data = arduinoSerial2.read(len(dataToSend))
                            print(
                                "Data received from Arduino 2:",
                                arduino2Data.decode()
                            )

                            # Arduino 2 -> Arduino 1
                            arduinoSerial1.reset_input_buffer()
                            arduinoSerial2.write(dataToSend)
                            arduinoSerial2.flush()
                            print("Data sent to Arduino 2:", dataString)

                            arduino1Data = arduinoSerial1.read(len(dataToSend))
                            print(
                                "Data received from Arduino 1:",
                                arduino1Data.decode()
                            )

                            status = "0"

                    # When serial connection is lost, break out of loop
                    except serial.SerialException:
                        print("Serial connection lost.")
                        break

                    # When Ctrl+C is pressed, return to the main menu
                    except KeyboardInterrupt:
                        print("Stop Arduino Data Reading")
                        status = "0"

                # Connect with Trimble device with SDK.
                # Read SDK data received from Arduino 2 and send it to Trimble.
                # Read the Trimble response back on COM7 and log it.
                # Write the response to Arduino 2 so it passes back to Arduino 1.
                case "30":
                    log_filename = f"C:/Users/clive/OneDrive/Desktop/Serial Communication Data Packets/TrimbleLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    print(f"Logging to: {log_filename}")

                    arduino2Buffer = bytearray()
                    trimbleBuffer = bytearray()

                    try:
                        with open(log_filename, "a") as log_file:
                            while True:
                                # Read SDK data after Arduino 1 passes it to
                                # Arduino 2. The separate SDK owns COM19.
                                if arduinoSerial2.in_waiting > 0:
                                    # Raw Data
                                    arduino2Data = arduinoSerial2.read(
                                        arduinoSerial2.in_waiting
                                    )

                                    # Forward immediately before printing or logging
                                    trimbleSerial.write(arduino2Data)

                                    arduino2Buffer.extend(arduino2Data)

                                    # Print Data
                                    arduino2PrintData = [
                                        f"0x{b:02X}" for b in arduino2Data
                                    ]
                                    arduino2FormattedPrintData = ", ".join(
                                        arduino2PrintData
                                    )
                                    print(
                                        "Data received from Arduino 2:",
                                        arduino2FormattedPrintData
                                    )

                                    # Log to text file
                                    timestamp = datetime.now().strftime(
                                        '%Y-%m-%d %H:%M:%S.%f'
                                    )[:-3]
                                    line = f"[{timestamp}] [ARDUINO 2 - FROM SDK] {arduino2FormattedPrintData}"
                                    print(line)
                                    log_file.write(line + "\n")

                                # Check if there is a response from the Trimble
                                if trimbleSerial.in_waiting > 0:
                                    # Raw Data
                                    trimbleRawData = trimbleSerial.read(
                                        trimbleSerial.in_waiting
                                    )

                                    # Forward immediately before printing or logging
                                    arduinoSerial2.write(trimbleRawData)

                                    trimbleBuffer.extend(trimbleRawData)

                                    # Print Data
                                    trimblePrintData = [
                                        f"0x{b:02X}" for b in trimbleRawData
                                    ]
                                    trimbleFormattedPrintData = ", ".join(
                                        trimblePrintData
                                    )
                                    print(
                                        "Data received from Trimble:",
                                        trimbleFormattedPrintData
                                    )

                                    # Log to text file
                                    timestamp = datetime.now().strftime(
                                        '%Y-%m-%d %H:%M:%S.%f'
                                    )[:-3]
                                    line = f"[{timestamp}] [TRIMBLE] {trimbleFormattedPrintData}"
                                    print(line)
                                    log_file.write(line + "\n")

                                    # Log the return handoff to Arduino 2
                                    timestamp = datetime.now().strftime(
                                        '%Y-%m-%d %H:%M:%S.%f'
                                    )[:-3]
                                    line = f"[{timestamp}] [ARDUINO 2 - TO SDK] {trimbleFormattedPrintData}"
                                    print(line)
                                    log_file.write(line + "\n")

                    # When serial connection is lost, break out of loop
                    except serial.SerialException:
                        print("Serial connection lost.")
                        break

                    # When Ctrl+C is pressed, return to the main menu
                    except KeyboardInterrupt:
                        print("Stop Trimble Data Reading")
                        status = "0"

                # Exit the program
                case "1000":
                    print("Exiting program")
                    status = "0"
                    break


# Bluetooth
elif sdkMethod == "2":
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


else:
    print("Invalid SDK communication method.")
