import time
from logData import log_data

def set_target_directReflex(trimbleSerial, logFile, status):
    try:
        status["backgroundStreamEnabled"] = False
        commandTimeout = 10
        
        expectedResponse = (b"\x12\x08\x00\x02\x01\x99\x80\x00\xC0")
        commandBytes = [0x13, 0x0B, 0x00, 0x01, 0x02, 0x99, 0x40, 0x01, 0x01, 0x01, 0x01, 0xC0]
        trimbleBuffer = bytearray()

        commandStartTime = time.monotonic()
        previousCountdown = None

        print("Setting target to Direct Reflex with Laser Pointer\n")

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
                status["targetType"] = "Direct Reflex"
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                # The SDK does not send the laser command immediately after 0x99.
                # Direct Reflex mode needs time to finish switching internally.
                time.sleep(3.0)
                return True
    
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False
    
    finally:
        status["backgroundStreamEnabled"] = True