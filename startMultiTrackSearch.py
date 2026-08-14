import time
from logData import log_data

def start_multitrack_search(trimbleSerial, logFile, status):
    state = 0

    try:
        while True:
            match state:

                # Send SearchLock command and wait for acknowledgement.
                case 0:
                    commandBytes = [0x13, 0x0A, 0x00, 0x01, 0x02, 0x6B, 0x40, 0x02, 0x02, 0x01, 0xC0]

                    expectedResponse = b"\x12\x08\x00\x02\x01\x6B\x80\x00\xC0"

                    status["prismLocked"] = False
                    status["searchState"] = False
                    status["searchFailed"] = False

                    status["backgroundStreamEnabled"] = False

                    print("Start search operation.\n")

                    log_data(commandBytes, logFile)
                    trimbleSerial.write(bytes(commandBytes))
                    trimbleSerial.flush()

                    responseBuffer = bytearray()

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
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(responseBuffer, logFile)
                            print("Command timed out.\n")
                            return False

                        waiting = trimbleSerial.in_waiting

                        if waiting == 0:
                            time.sleep(0.005)
                            continue

                        received = trimbleSerial.read(waiting)
                        responseBuffer.extend(received)

                        if expectedResponse in responseBuffer:
                            status["backgroundStreamEnabled"] = True
                            log_data(responseBuffer, logFile)
                            print("SearchLock operation started: Searching for target.\n")
                            #Clear buffer
                            responseBuffer.clear()
                            state = 10
                            break

                #Let backgroundStream detect searching and lock result.
                case 10:
                    status["backgroundStreamEnabled"] = True

                    searchStartTime = time.monotonic()
                    searchTimeoutSeconds = 120
                    previousCountdown = None

                    while True:
                        elapsedSeconds = time.monotonic() - searchStartTime
                        remainingSeconds = max(0, searchTimeoutSeconds - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rSearch timeout in: {remainingSeconds:02d} seconds", end="", flush=True)
                            previousCountdown = remainingSeconds

                        if status["searchFailed"] == True:
                            return False

                        if status["prismLocked"] == True:
                            return True

                        if elapsedSeconds >= searchTimeoutSeconds:
                            return False

                        time.sleep(0.05)

    except KeyboardInterrupt:
        print("SearchLock monitoring stopped.\n")
        return False

    finally:
        status["backgroundStreamEnabled"] = True