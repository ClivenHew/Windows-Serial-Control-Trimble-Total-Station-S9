import time
from logData import log_data

def set_target_multiTrack_searchLock(trimbleSerial, logFile, status):
    try:
        status["backgroundStreamEnabled"] = False
        commandTimeout = 10
        
        expectedResponse = (b"\x12\x08\x00\x02\x01\x99\x80\x00\xC0")
        trimbleBuffer = bytearray()

        commandStartTime = time.monotonic()
        previousCountdown = None

        while True:
            try:
                status["targetID"] = int(input("Enter active prism target ID: "))

                if 1 <= status["targetID"] <= 8:
                    break

                print("Invalid target ID. Enter a value from 1 to 8.\n")

            except ValueError:
                print("Invalid input. Enter a number.\n")

        commandBytes = [0x13, 0x0B, 0x00, 0x01, 0x02, 0x99, 0x40, 0x01, 0x01, 0x02, status["targetID"], 0xC0]
        commandBytes2 = [0x13, 0x0B, 0x00, 0x01, 0x02, 0x99, 0x40, 0x02, 0x01, 0x08, status["targetID"], 0xC0]

        print(f"Setting target to MultiTrack with SearchLock, " f"Active ID {status["targetID"]}.\n")

        if status["targetType"] is None:
            log_data(commandBytes, logFile)
            trimbleSerial.write(bytes(commandBytes))
            trimbleSerial.flush()

            commandStartTime = time.monotonic()
            previousCountdown = None

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
                    status["targetType"] = "Active Prism"
                    log_data(trimbleBuffer, logFile)
                    #Clear buffer
                    trimbleBuffer.clear()
                    time.sleep(1.0)
                    break

        log_data(commandBytes2, logFile)
        trimbleSerial.write(bytes(commandBytes2))
        trimbleSerial.flush()

        commandStartTime = time.monotonic()
        previousCountdown = None

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
                status["targetType"] = "Active Prism"
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                time.sleep(1.0)
                return True
    
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False
    
    #finally:
        #status["backgroundStreamEnabled"] = True