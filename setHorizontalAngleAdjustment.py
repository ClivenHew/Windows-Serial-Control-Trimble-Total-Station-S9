import time
from logData import log_data
from unescapeBytes import escape_bytes

def set_ha_adjustment(trimbleSerial, logFile, desiredHA, currentAngles, status):
    try:
        status["backgroundStreamEnabled"] = False

        if not 0 <= desiredHA < 360.0:
            raise ValueError(
                "Desired HA must be from 0 to less than 360 degrees"
            )

        if not 0 <= currentAngles["horizontalAngle"] < 360.0:
            raise ValueError(
                "Current HA must be from 0 to less than 360 degrees"
            )

        if not 0 <= currentAngles["horizontalAngleAdjustment"] < 360.0:
            raise ValueError(
                "Current HA adjustment must be from 0 to less than 360 degrees"
            )

        # Calculate the new HA adjustment.
        # Formula:
        # New adjustment = desired HA - current displayed HA + current adjustment
        adjustmentDegrees = (desiredHA - currentAngles["horizontalAngle"] + currentAngles["horizontalAngleAdjustment"]) % 360.0

        adjustmentInteger = round(adjustmentDegrees * 400_000_000 / 360.0)

        adjustmentBytes = adjustmentInteger.to_bytes(4, byteorder="little", signed=True)

        commandBytes = (b"\x13\x0B\x00\x01\x02\xC7\x41" + adjustmentBytes + b"\xC0")

        expectedResponse = (b"\x12\x08\x00\x02\x01\xC7\x81\x00\xC0")

        trimbleBuffer = bytearray()

        commandBytes = escape_bytes(commandBytes)

        log_data(commandBytes, logFile)
        trimbleSerial.write(commandBytes)
        trimbleSerial.flush()

        commandStartTime = time.monotonic()
        commandTimeoutSeconds = 10
        previousCountdown = None

        while True:
            elapsedSeconds = time.monotonic() - commandStartTime
            remainingSeconds = max(
                0,
                commandTimeoutSeconds - int(elapsedSeconds)
            )

            if remainingSeconds != previousCountdown:
                print(f"\rCommand timeout in: {remainingSeconds:02d} seconds", end="", flush=True)
                previousCountdown = remainingSeconds

            if elapsedSeconds >= commandTimeoutSeconds:
                print("\nCommand timed out.")
                log_data("Timeout waiting for expected response", logFile)
                log_data(trimbleBuffer, logFile)
                return False

            if trimbleSerial.in_waiting == 0:
                time.sleep(0.005)
                continue

            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

            if expectedResponse in trimbleBuffer:
                currentAngles["horizontalAngleAdjustment"] = adjustmentDegrees
                log_data(trimbleBuffer, logFile)
                #Clear buffer
                trimbleBuffer.clear()
                return True

    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False

    finally:
        status["backgroundStreamEnabled"] = True