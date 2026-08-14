import time
from logData import log_data

def get_correction_values(correctionValues, logFile, status, trimbleSerial):
    try:
        status["backgroundStreamEnabled"] = False

        commandBytes = [0x13, 0x07, 0x00, 0x01, 0x02, 0xAE, 0x40, 0xC0]
        responseHeader = (b"\x12\x1C\x00\x02\x01\xAE\x80\x00")
        trimbleBuffer = bytearray()

        commandStartTime = time.monotonic()
        commandTimeout = 10
        previousCountdown = None

        #Send data packet
        log_data(commandBytes, logFile)
        trimbleSerial.write(bytes(commandBytes))
        trimbleSerial.flush()

        while True:
            #Track the time taken
            elapsedTime = time.monotonic() - commandStartTime
            #Don't allow tracked time to go below 0 seconds
            remainingTime = max(0, commandTimeout - int(elapsedTime))

            #Print out the remaining time if it is a different value
            if remainingTime != previousCountdown:
                print(f"Command timeout in: " f"{remainingTime:02d} seconds", end = "", flush = True)
                previousCountdown = remainingTime

            #If elapsed time has exceeded 10 seconds
            if elapsedTime > commandTimeout:
                print("Command timed out.\n")
                log_data("Timeout waiting for expected response", logFile)
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                return False
            
            #If there is data in the serial buffer
            if trimbleSerial.in_waiting > 0:
                #Read and append incoming data in array
                trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

            start = trimbleBuffer.find(responseHeader)

            if start == -1:
                continue

            decodedPayload = bytearray()
            index = start + len(responseHeader)

            while index < len(trimbleBuffer):
                currentByte = trimbleBuffer[index]

                #Actual packet end.
                if currentByte == 0xC0:
                    break

                #Escaped byte.
                if currentByte == 0xDB:
                    if index + 1 >= len(trimbleBuffer):
                        break

                    nextByte = trimbleBuffer[index + 1]

                    if nextByte == 0xDC:
                        decodedPayload.append(0xC0)
                        index += 2
                        continue

                    if nextByte == 0xDD:
                        decodedPayload.append(0xDB)
                        index += 2
                        continue

                decodedPayload.append(currentByte)
                index += 1

            #Need exactly 20 payload bytes:
            #5 correction values × 4 bytes each.
            if len(decodedPayload) < 20:
                continue

            correctionPayload = decodedPayload[0:20]

            opticalCollimationHAInteger = int.from_bytes(correctionPayload[0:4], byteorder="little", signed=True)
            opticalCollimationVAInteger = int.from_bytes(correctionPayload[4:8], byteorder="little", signed=True)
            trackerCollimationHAInteger = int.from_bytes(correctionPayload[8:12], byteorder="little", signed=True)
            trackerCollimationVAInteger = int.from_bytes(correctionPayload[12:16], byteorder="little", signed=True)
            trunnionAxisInteger = int.from_bytes(correctionPayload[16:20], byteorder="little", signed=True)

            correctionValues["opticalCollimationHorizontalAngle"] = (opticalCollimationHAInteger * 360.0 / 4_000_000)
            correctionValues["opticalCollimationVerticalAngle"] = (opticalCollimationVAInteger * 360.0 / 4_000_000)
            correctionValues["trackerCollimationHorizontalAngle"] = (trackerCollimationHAInteger * 360.0 / 4_000_000)
            correctionValues["trackerCollimationVerticalAngle"] = (trackerCollimationVAInteger * 360.0 / 4_000_000)
            correctionValues["trunnionAxis"] = (trunnionAxisInteger * 360.0 / 4_000_000)

            print("Correction values received.\n")
            log_data(trimbleBuffer, logFile)
            #Clear buffer
            trimbleBuffer.clear()
            return True
        
    except KeyboardInterrupt:
        print("Retrieving correction values stopped.\n")
        return False
    
    finally:
        status["backgroundStreamEnabled"] = True