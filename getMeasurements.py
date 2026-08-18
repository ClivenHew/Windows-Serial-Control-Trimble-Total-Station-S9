import time
from logData import log_data

def get_measurements(status, logFile, trimbleSerial):
    try:
        commandTimeout = 10

        expectedResponse = (b"\x12\x08\x00\x02\x01\x69\x80\x00\xC0")
        failResponse = (b"\x12\x08\x00\x02\x01\x69\x80\x57\xC0")
        commandBytes = [0x13, 0x08, 0x00, 0x01, 0x02, 0x69, 0x40, 0x02, 0xC0]

        trimbleBuffer = bytearray()

        commandStartTime = time.monotonic()
        previousCountdown = None

        status["backgroundStreamEnabled"] = False

        print("Measuring Prism Angle and Distance.\n")

        #Send command to enable tilt compensator
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

            #Once expected response is found
            if expectedResponse in trimbleBuffer:
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                return True

            #Once fail response is found
            if failResponse in trimbleBuffer:
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                return False
            
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False
    
    finally:
        status["backgroundStreamEnabled"] = True