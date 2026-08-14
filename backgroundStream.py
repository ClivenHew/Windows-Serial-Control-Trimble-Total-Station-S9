import time
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

    while not stopEvent.is_set():

        if (
            not status["trimbleConnection"]
            or not status["backgroundStreamEnabled"]
        ):
            time.sleep(0.01)
            continue

        try:
            waiting = trimbleSerial.in_waiting

        except Exception as error:
            print(
                f"\nBackground stream stopped: "
                f"serial port unavailable: {error}"
            )
            log_data(
                f"Background stream stopped: "
                f"serial port unavailable: {error}",
                logFile
            )

            status["trimbleConnection"] = False
            status["backgroundStreamEnabled"] = False
            return

        if waiting == 0:
            time.sleep(0.005)
            continue

        if (
            not status["trimbleConnection"]
            or not status["backgroundStreamEnabled"]
        ):
            continue

        try:
            streamBuffer.extend(
                trimbleSerial.read(waiting)
            )

        except Exception as error:
            print(f"\nBackground stream read failed: {error}")
            log_data(
                f"Background stream read failed: {error}",
                logFile
            )

            status["trimbleConnection"] = False
            status["backgroundStreamEnabled"] = False
            return

        while True:
            streamPosition = streamBuffer.find(streamHeader)

            heartbeatFFPosition = streamBuffer.find(heartbeatFF)
            heartbeatFEPosition = streamBuffer.find(heartbeatFE)

            heartbeatPositions = [
                position
                for position in [
                    heartbeatFFPosition,
                    heartbeatFEPosition
                ]
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
                        try:
                            trimbleSerial.write(heartbeatFF)
                            trimbleSerial.flush()

                        except Exception as error:
                            print(
                                f"\nBackground stream heartbeat failed: "
                                f"{error}"
                            )
                            log_data(
                                f"Background stream heartbeat failed: "
                                f"{error}",
                                logFile
                            )

                            status["trimbleConnection"] = False
                            status["backgroundStreamEnabled"] = False
                            return

                    continue

            if streamPosition == -1:
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

            packet = bytes(unescapedPacket)

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

            log_data("Background Stream", logFile)
            log_data(packet, logFile)

            # 0x04 = motor movement active
            # 0x02 = idle/stable
            turnTotalStation["inMovement"] = packet[13]

            # 0x08, 0x56 = searching
            # 0x02, 0x00 = locked after searching
            # 0x02, 0x57 = target not found
            searchState = packet[13:15]

            if searchState == b"\x08\x56":
                # Searching
                status["searchState"] = True
                status["prismLocked"] = False
                status["searchFailed"] = False

            elif searchState == b"\x02\x00":
                # Locked only when transitioning from searching
                if status["searchState"] == True:
                    status["prismLocked"] = True
                    status["searchFailed"] = False

                status["searchState"] = False

            elif searchState == b"\x02\x57":
                # Search completed without finding the target
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
                continue

            currentAngles.update(selected)