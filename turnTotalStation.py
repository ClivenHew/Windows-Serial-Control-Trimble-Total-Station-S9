import time
from logData import log_data
from unescapeBytes import escape_bytes

def turn_total_station(trimbleSerial, logFile, turnTotalStation ,currentAngles, status):
    state = 0

    try:
        while True:
            match state:
                #Calculate the angles to turn to
                case 0:
                    status["backgroundStreamEnabled"] = True

                    if (turnTotalStation["newHorizontalAngle"] is None or turnTotalStation["newVerticalAngle"] is None):
                        #Ask for user to input desired angles
                        turnTotalStation["newHorizontalAngle"] = float(input("Enter target horizontal angle: "))
                        turnTotalStation["newVerticalAngle"] = float(input("Enter target vertical angle: "))

                    turnTotalStation["newHorizontalAngle"] %= 360.0
                    turnTotalStation["newVerticalAngle"] %= 360.0
                    currentAngles["horizontalAngleAdjustment"] %= 360.0

                    # Convert the requested displayed HA to the internal encoder HA.
                    encodedHA = (turnTotalStation["newHorizontalAngle"] - currentAngles["horizontalAngleAdjustment"]) % 360.0

                    # Servo command uses 4,000,000 units per revolution.
                    haInteger = int(encodedHA * 4_000_000 / 360.0)

                    vaInteger = int(turnTotalStation["newVerticalAngle"] * 4_000_000 / 360.0)

                    haBytes = haInteger.to_bytes(4, byteorder="little", signed=False)

                    vaBytes = vaInteger.to_bytes(4, byteorder="little", signed=False)

                    speedBytes = bytes([0x64, 0x00, 0x00, 0x00])

                    commandBytes = (bytes([0x13, 0x14, 0x00, 0x01, 0x02, 0x6E, 0x40, 0x03])
                            + haBytes
                            + vaBytes
                            + speedBytes
                            + bytes([0xC0])
                            )

                    print("\n--- Turn Total Station ---")
                    print(f"Requested HA:   {turnTotalStation["newHorizontalAngle"]:.5f} degrees")
                    print(f"Requested VA:   {turnTotalStation["newVerticalAngle"]:.5f} degrees")
                    print(f"HA adjustment:  {currentAngles["horizontalAngleAdjustment"]:.5f} degrees")
                    print(f"Internal HA:    {encodedHA:.5f} degrees")

                    state = 10

                #Move the total station to the calculated angles
                case 10:
                    #Disable background stream when sending commands
                    status["backgroundStreamEnabled"] = False

                    print("Sending turn angle command.\n")

                    commandBytes = escape_bytes(commandBytes)

                    log_data(commandBytes, logFile)
                    trimbleSerial.write(commandBytes)
                    trimbleSerial.flush()

                    expectedResponse = (b"\x12\x08\x00\x02\x01\x6E\x80\x00\xC0")

                    responseBuffer = bytearray()

                    commandStartTime = time.monotonic()
                    commandTimeoutSeconds = 10
                    previousCountdown = None

                    while True:
                        elapsedSeconds = time.monotonic() - commandStartTime
                        remainingSeconds = max(0, int(commandTimeoutSeconds) - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rCommand timeout in: "f"{remainingSeconds:02d} seconds", end="", flush=True)
                            previousCountdown = remainingSeconds

                        if elapsedSeconds >= commandTimeoutSeconds:
                            print("\nTurn command acknowledgement timed out.")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(responseBuffer, logFile)
                            return False

                        waiting = trimbleSerial.in_waiting

                        if waiting == 0:
                            time.sleep(0.005)
                            continue

                        received = trimbleSerial.read(waiting)
                        responseBuffer.extend(received)

                        if expectedResponse in responseBuffer:
                            print("\nTurn command acknowledged.")
                            log_data(responseBuffer, logFile)
                            #Clear buffer
                            responseBuffer.clear()
                            #Go to next state which is to check if total station has finished turning
                            state = 20
                            break

                #Check if total station has finished turning
                case 20:
                    status["backgroundStreamEnabled"] = True

                    print("Checking if total station has moved to desired angles.\n")

                    commandStartTime = time.monotonic()
                    commandTimeoutSeconds = 15
                    previousCountdown = None

                    while True:
                        elapsedSeconds = time.monotonic() - commandStartTime
                        remainingSeconds = max(0, int(commandTimeoutSeconds) - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rCommand timeout in: "f"{remainingSeconds:02d} seconds",end="",flush=True)
                            previousCountdown = remainingSeconds

                        if elapsedSeconds >= commandTimeoutSeconds:
                            print("Total Station took too long to turn\n.")
                            #Reset variables
                            turnTotalStation["newHorizontalAngle"] = None
                            turnTotalStation["newVerticalAngle"] = None
                            return False

                        #Allow background stream to update variables
                        if currentAngles["horizontalAngle"] is None or currentAngles["verticalAngle"] is None:
                            time.sleep(0.1)
                            continue

                        #Check if total station has reached desired angles
                        haError = abs((currentAngles["horizontalAngle"] - turnTotalStation["newHorizontalAngle"] + 180.0) % 360.0 - 180.0)

                        vaError = abs((currentAngles["verticalAngle"] - turnTotalStation["newVerticalAngle"] + 180.0) % 360.0 - 180.0)

                        haReached = haError <= 1.0
                        vaReached = vaError <= 1.0

                        if haReached and vaReached:
                            print("Desired angles reached.\n")
                            #Reset variables
                            turnTotalStation["newHorizontalAngle"] = None
                            turnTotalStation["newVerticalAngle"] = None
                            return True
                            
    except KeyboardInterrupt:
        print("Total Station turning stopped.\n")
        return False
    
    finally:
        status["backgroundStreamEnabled"] = True