import time
from logData import log_data
from unescapeBytes import escape_bytes

def set_search_window(trimbleSerial, logFile, currentAngles, searchWindow, status):
    try:
        status["backgroundStreamEnabled"] = False

        if not 2.0 < searchWindow["xAxis"] <= 360.0:
            raise ValueError(
                "HA window must be greater than 2 and at most 360 degrees"
            )

        if not 2.0 < searchWindow["yAxis"] <= 360.0:
            raise ValueError(
                "VA window must be greater than 2 and at most 360 degrees"
            )

        # Calculate half-window sizes.
        haHalfWindow = searchWindow["xAxis"] / 2.0
        vaHalfWindow = searchWindow["yAxis"] / 2.0

        # Calculate lower and upper boundaries.
        haLower = (currentAngles["horizontalAngle"] - haHalfWindow) % 360.0
        haUpper = (currentAngles["horizontalAngle"] + haHalfWindow) % 360.0

        vaLower = (currentAngles["verticalAngle"] - vaHalfWindow) % 360.0
        vaUpper = (currentAngles["verticalAngle"] + vaHalfWindow) % 360.0

        # Convert degrees to 4,000,000-unit circle values.
        haLowerInteger = int(haLower * 4_000_000 / 360.0)
        haUpperInteger = int(haUpper * 4_000_000 / 360.0)
        vaLowerInteger = int(vaLower * 4_000_000 / 360.0)
        vaUpperInteger = int(vaUpper * 4_000_000 / 360.0)

        # Convert each integer to four little-endian bytes.
        haLowerBytes = haLowerInteger.to_bytes(4, byteorder="little", signed=False)
        haUpperBytes = haUpperInteger.to_bytes(4, byteorder="little", signed=False)
        vaLowerBytes = vaLowerInteger.to_bytes(4, byteorder="little", signed=False)
        vaUpperBytes = vaUpperInteger.to_bytes( 4, byteorder="little", signed=False)

        # Packet order: VA lower, VA upper, HA lower, HA upper.
        packet = (
            bytes([
                0x13, 0x18, 0x00,
                0x01, 0x02, 0x6D,
                0x40
            ])
            + vaLowerBytes
            + vaUpperBytes
            + haLowerBytes
            + haUpperBytes
            + bytes([
                0x00,
                0xC0
            ])
        )

        expectedResponse = (b"\x12\x08\x00\x02\x01\x6D\x80\x00\xC0")

        print("\n--- Set Search Window ---")
        print(f"Current HA: {currentAngles["horizontalAngle"]:.6f} degrees")
        print(f"Current VA: {currentAngles["verticalAngle"]:.6f} degrees")
        print(f"HA window:  {searchWindow["xAxis"]:.6f} degrees")
        print(f"VA window:  {searchWindow["yAxis"]:.6f} degrees")
        print(f"HA lower:   {haLower:.6f} degrees")
        print(f"HA upper:   {haUpper:.6f} degrees")
        print(f"VA lower:   {vaLower:.6f} degrees")
        print(f"VA upper:   {vaUpper:.6f} degrees")

        packet = escape_bytes(packet)

        log_data(packet, logFile)
        trimbleSerial.write(packet)
        trimbleSerial.flush()

        responseBuffer = bytearray()

        commandStartTime = time.monotonic()
        commandTimeoutSeconds = 10
        previousCountdown = None

        while True:
            elapsedSeconds = time.monotonic() - commandStartTime
            remainingSeconds = max(0,commandTimeoutSeconds - int(elapsedSeconds))
            if remainingSeconds != previousCountdown:
                print(f"\rCommand timeout in: " f"{remainingSeconds:02d} seconds", end="", flush=True)
                previousCountdown = remainingSeconds

            if elapsedSeconds >= commandTimeoutSeconds:
                print("\nCommand timed out.")
                log_data("Timeout waiting for expected response", logFile)
                log_data(responseBuffer, logFile)
                return False

            if trimbleSerial.in_waiting == 0:
                time.sleep(0.005)
                continue

            received = trimbleSerial.read(trimbleSerial.in_waiting)
            responseBuffer.extend(received)

            if expectedResponse in responseBuffer:
                log_data(responseBuffer, logFile)
                responseBuffer.clear()
                time.sleep(1)
                return True
    
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        responseBuffer.clear()
        return False

    #finally:
        #status["backgroundStreamEnabled"] = True