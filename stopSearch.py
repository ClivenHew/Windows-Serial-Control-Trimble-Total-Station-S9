import time
from logData import log_data

def stop_search(trimbleSerial, logFile, status):
    try:
        state = 0
        commandTimeout = 10

        while True:
            match state:
                case 0:
                    status["backgroundStreamEnabled"] = False
                    expectedResponse = (b"\x12\x08\x00\x02\x01\x5B\x80\x00\xC0")
                    commandBytes = [0x13, 0x07, 0x00, 0x01, 0x02, 0x5B, 0x40, 0xC0]
                    trimbleBuffer = bytearray()

                    commandStartTime = time.monotonic()
                    previousCountdown = None

                    print("Stop Search Operation.\n")

                    log_data(commandBytes, logFile)
                    trimbleSerial.write(bytes(commandBytes))
                    trimbleSerial.flush()

                    while True:
                        elapsedTime = time.monotonic() - commandStartTime
                        remainingTime = max(0,commandTimeout - int(elapsedTime))
                        if remainingTime != previousCountdown:
                            print(f"\rCommand timeout in: " f"{remainingTime:02d} seconds", end="", flush=True)
                            previousCountdown = remainingTime

                        if elapsedTime >= commandTimeout:
                            print("\nCommand timed out.")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            return False
                        
                        #If there is nothing in buffer, loop again
                        if trimbleSerial.in_waiting == 0:
                            continue

                        #Append new data packets into buffer
                        trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                        if expectedResponse in trimbleBuffer:
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            #Monitor if the total station has stopped moving
                            state = 10
                            break

                case 10:
                    status["backgroundStreamEnabled"] = True

                    searchStartTime = time.monotonic()
                    searchTimeoutSeconds = 60
                    previousCountdown = None

                    while True:
                        elapsedSeconds = time.monotonic() - searchStartTime
                        remainingSeconds = max(0, searchTimeoutSeconds - int(elapsedSeconds))

                        if remainingSeconds != previousCountdown:
                            print(f"\rTimeout in: {remainingSeconds:02d} seconds", end="", flush=True)
                            previousCountdown = remainingSeconds

                        if status["searchState"] == False:
                            return True

                        if elapsedSeconds >= searchTimeoutSeconds:
                            return False

                        time.sleep(0.05)
    
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False
    
    finally:
        status["backgroundStreamEnabled"] = True