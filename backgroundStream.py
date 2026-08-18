from logData import log_data


def capture_stream(
    trimbleSerial,
    logFile,
    stopEvent,
    status,
    currentAngles,
    turnTotalStation
):
    streamBuffer = bytearray()

    streamHeader = b"\x02\x45\x00\x02\x01\x64"
    heartbeatFF = b"\xFF\xC0"
    heartbeatFE = b"\xFE\xC0"

    maximumBufferSize = 4096
    consecutiveErrors = 0
    streamWasEnabled = False

    def safe_log(data):
        """
        Prevent a logging failure from terminating the background thread.
        """
        try:
            log_data(data, logFile)
        except Exception as error:
            print(f"\nBackground stream logging failed: {error}")

    def convert_measurement(raw):
        haAdjustment = currentAngles["horizontalAngleAdjustment"]

        if haAdjustment is None:
            haAdjustment = 0.0

        return {
            "horizontalAngle": (
                raw["horizontalAngle"] * 360.0 / 400_000_000
                + haAdjustment
            ) % 360.0,

            "verticalAngle": (
                raw["verticalAngle"] * 360.0 / 400_000_000
            ) % 360.0,

            "sighting": (
                raw["sighting"] * 360.0 / 400_000_000
            ),

            "trunnion": (
                raw["trunnion"] * 360.0 / 400_000_000
            ),

            "slopeDistance": raw.get("slopeDistance")
        }

    def valid_measurement(raw):
        return not (
            raw["horizontalAngle"] == 0
            and raw["verticalAngle"] == 0
            and raw["sighting"] == 0
            and raw["trunnion"] == 0
        )

    def unescape_packet(rawPacket):
        unescapedPacket = bytearray()
        index = 0

        while index < len(rawPacket):
            if (
                index < len(rawPacket) - 1
                and rawPacket[index] == 0xDB
                and rawPacket[index + 1] == 0xDC
            ):
                unescapedPacket.append(0xC0)
                index += 2

            elif (
                index < len(rawPacket) - 1
                and rawPacket[index] == 0xDB
                and rawPacket[index + 1] == 0xDD
            ):
                unescapedPacket.append(0xDB)
                index += 2

            else:
                unescapedPacket.append(rawPacket[index])
                index += 1

        return bytes(unescapedPacket)

    def process_stream_packet(packet):
        # 0x04 = motor movement active
        # 0x02 = idle/stable
        turnTotalStation["inMovement"] = packet[13]

        # 0x08, 0x56 = searching
        # 0x02, 0x00 = idle or locked
        # 0x02, 0x57 = target not found
        searchState = packet[13:15]

        if searchState == b"\x08\x56":
            status["searchState"] = True
            status["prismLocked"] = False
            status["searchFailed"] = False

        elif searchState == b"\x02\x00":
            if status["searchState"] is True:
                status["prismLocked"] = True
                status["searchFailed"] = False

            status["searchState"] = False

        elif searchState == b"\x02\x57":
            status["searchState"] = False
            status["prismLocked"] = False
            status["searchFailed"] = True

        rawA = {
            "horizontalAngle": int.from_bytes(
                packet[22:26],
                byteorder="little",
                signed=True
            ),
            "verticalAngle": int.from_bytes(
                packet[26:30],
                byteorder="little",
                signed=True
            ),
            "sighting": int.from_bytes(
                packet[38:42],
                byteorder="little",
                signed=True
            ),
            "trunnion": int.from_bytes(
                packet[42:46],
                byteorder="little",
                signed=True
            )
        }

        rawB = {
            "horizontalAngle": int.from_bytes(
                packet[30:34],
                byteorder="little",
                signed=True
            ),
            "verticalAngle": int.from_bytes(
                packet[34:38],
                byteorder="little",
                signed=True
            ),
            "sighting": int.from_bytes(
                packet[46:50],
                byteorder="little",
                signed=True
            ),
            "trunnion": int.from_bytes(
                packet[50:54],
                byteorder="little",
                signed=True
            )
        }

        slopeDistanceRaw = int.from_bytes(
            packet[54:58],
            byteorder="little",
            signed=False
        )

        if slopeDistanceRaw == 0:
            slopeDistance = None
        else:
            slopeDistance = slopeDistanceRaw / 100_000.0

        rawA["slopeDistance"] = slopeDistance
        rawB["slopeDistance"] = slopeDistance

        measurementA = convert_measurement(rawA)
        measurementB = convert_measurement(rawB)

        if valid_measurement(rawB):
            selected = measurementB

            if turnTotalStation["inMovement"] == 0x02:
                if measurementB["verticalAngle"] >= 180.0:
                    currentAngles["face"] = "Face 2"
                else:
                    currentAngles["face"] = "Face 1"

        elif valid_measurement(rawA):
            selected = measurementA

        else:
            return

        currentAngles.update(selected)

    while not stopEvent.is_set():
        streamEnabled = (
            status.get("trimbleConnection", False)
            and status.get("backgroundStreamEnabled", False)
        )

        if not streamEnabled:
            # Do not combine an old partial packet with data received after
            # another function has temporarily taken control of the port.
            if streamWasEnabled:
                streamBuffer.clear()

            streamWasEnabled = False
            stopEvent.wait(0.01)
            continue

        streamWasEnabled = True

        try:
            waiting = trimbleSerial.in_waiting

            # Access to the port succeeded, so consider it recovered.
            if consecutiveErrors > 0:
                message = (
                    "Background stream serial access recovered after "
                    f"{consecutiveErrors} error(s)"
                )
                print(f"\n{message}")
                safe_log(message)
                consecutiveErrors = 0

            if waiting == 0:
                stopEvent.wait(0.005)
                continue

            # Check again in case a command disabled the stream after the
            # in_waiting check.
            if (
                not status.get("trimbleConnection", False)
                or not status.get("backgroundStreamEnabled", False)
            ):
                streamBuffer.clear()
                streamWasEnabled = False
                continue

            received = trimbleSerial.read(waiting)

            if not received:
                stopEvent.wait(0.005)
                continue

            streamBuffer.extend(received)

            # Prevent malformed or unterminated input from growing forever.
            if len(streamBuffer) > maximumBufferSize:
                safe_log(
                    "Background stream buffer exceeded maximum size; "
                    "discarding stale data"
                )

                streamBuffer.clear()
                continue

            while True:
                streamPosition = streamBuffer.find(streamHeader)

                heartbeatFFPosition = streamBuffer.find(heartbeatFF)
                heartbeatFEPosition = streamBuffer.find(heartbeatFE)

                heartbeatPositions = [
                    position
                    for position in (
                        heartbeatFFPosition,
                        heartbeatFEPosition
                    )
                    if position != -1
                ]

                if heartbeatPositions:
                    heartbeatPosition = min(heartbeatPositions)

                    if (
                        streamPosition == -1
                        or heartbeatPosition < streamPosition
                    ):
                        heartbeatPacket = bytes(
                            streamBuffer[
                                heartbeatPosition:
                                heartbeatPosition + 2
                            ]
                        )

                        del streamBuffer[:heartbeatPosition + 2]

                        if heartbeatPacket == heartbeatFF:
                            # Check that another operation has not taken
                            # control of the serial port.
                            if (
                                status.get("trimbleConnection", False)
                                and status.get("backgroundStreamEnabled", False)
                            ):
                                trimbleSerial.write(heartbeatFF)
                                trimbleSerial.flush()

                        continue

                if streamPosition == -1:
                    # Keep only enough trailing data to contain a partial
                    # stream header.
                    if len(streamBuffer) > len(streamHeader):
                        del streamBuffer[:-len(streamHeader)]

                    break

                if streamPosition > 0:
                    del streamBuffer[:streamPosition]

                packetEnd = streamBuffer.find(b"\xC0")

                if packetEnd == -1:
                    break

                rawPacket = bytes(
                    streamBuffer[:packetEnd + 1]
                )

                del streamBuffer[:packetEnd + 1]

                packet = unescape_packet(rawPacket)

                if len(packet) < 3:
                    continue

                packetLength = (
                    int.from_bytes(
                        packet[1:3],
                        byteorder="little"
                    )
                    + 1
                )

                if (
                    len(packet) != packetLength
                    or packet[:6] != streamHeader
                    or packet[-1] != 0xC0
                ):
                    continue

                safe_log("Background Stream")
                safe_log(packet)

                try:
                    process_stream_packet(packet)

                except Exception as error:
                    # A malformed packet must not terminate the reader.
                    safe_log(
                        "Background stream packet processing failed: "
                        f"{error}"
                    )
                    continue

        except Exception as error:
            consecutiveErrors += 1
            streamBuffer.clear()

            retryDelay = min(
                0.25 * (2 ** min(consecutiveErrors - 1, 5)),
                5.0
            )

            message = (
                "Background stream error "
                f"{consecutiveErrors}: {error}. "
                f"Retrying in {retryDelay:.2f} seconds"
            )

            print(f"\n{message}")
            safe_log(message)

            # Unlike time.sleep(), this wakes immediately when the program
            # requests that the thread stop.
            stopEvent.wait(retryDelay)