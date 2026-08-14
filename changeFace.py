import time
from logData import log_data

def change_face(status, logFile, trimbleSerial, turnTotalStation, currentAngles):
    try:
        status["backgroundStreamEnabled"] = False

        expectedResponse = b"\x12\x08\x00\x02\x01\x7C\x80\x00\xC0"
        commandBytes = [0x13, 0x07, 0x00, 0x01, 0x02, 0x7C, 0x40, 0xC0]
        responseBuffer = bytearray()

        state = 0

        while True:
            match state:
                case 0:
                    if currentAngles["face"] is None:
                        print("\nCurrent face has not been received yet.")
                        return False

                    print(f"Current face: {currentAngles['face']}")

                    if currentAngles["face"] == "Face 1":
                        turnTotalStation["newFace"] = "Face 2"

                    elif currentAngles["face"] == "Face 2":
                        turnTotalStation["newFace"] = "Face 1"

                    else:
                        print(f"\nUnknown current face: {currentAngles['face']}")
                        return False

                    print(f"Expected new face: {turnTotalStation['newFace']}")

                    log_data(commandBytes, logFile)
                    trimbleSerial.write(bytes(commandBytes))
                    trimbleSerial.flush()

                    commandStartTime = time.monotonic()
                    commandTimeoutSeconds = 10
                    previousCountdown = None

                    while True:
                        elapsedSeconds = time.monotonic() - commandStartTime
                        remainingSeconds = max(0, commandTimeoutSeconds - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rCommand timeout in: {remainingSeconds:02d} seconds", end="", flush=True)
                            previousCountdown = remainingSeconds

                        if elapsedSeconds >= commandTimeoutSeconds:
                            print("\nCommand timed out.")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(responseBuffer, logFile)
                            turnTotalStation["newFace"] = None
                            return False

                        waiting = trimbleSerial.in_waiting

                        if waiting == 0:
                            time.sleep(0.005)
                            continue

                        received = trimbleSerial.read(waiting)
                        responseBuffer.extend(received)

                        if expectedResponse in responseBuffer:
                            print("\nChange face command accepted.")
                            log_data(responseBuffer, logFile)
                            responseBuffer.clear()
                            state = 10
                            break

                case 10:
                    status["backgroundStreamEnabled"] = True

                    print("Checking if total station has finished changing face.\n")

                    commandStartTime = time.monotonic()
                    commandTimeoutSeconds = 15
                    previousCountdown = None
                    movementStarted = False

                    while True:
                        elapsedSeconds = time.monotonic() - commandStartTime
                        remainingSeconds = max(0,commandTimeoutSeconds - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rMovement timeout in: {remainingSeconds:02d} seconds", end="", flush=True)
                            previousCountdown = remainingSeconds

                        if elapsedSeconds >= commandTimeoutSeconds:
                            print("\nFace change movement timed out.")
                            turnTotalStation["newFace"] = None
                            return False

                        # 0x04 = moving
                        if turnTotalStation["inMovement"] == 0x04:
                            movementStarted = True

                        # 0x02 = idle/stable
                        if movementStarted and turnTotalStation["inMovement"] == 0x02:
                            currentAngles["face"] = turnTotalStation["newFace"]

                            print("\nFace change completed.\n")
                            print(f"Current face: {currentAngles['face']}")

                            turnTotalStation["newFace"] = None

                            return True

                        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped changing face.")
        turnTotalStation["newFace"] = None
        return False

    finally:
        status["backgroundStreamEnabled"] = True