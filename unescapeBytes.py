def escape_bytes(packet):
    escapedPacket = bytearray()

    # Escape everything except the final 0xC0 terminator.
    for byte in packet[:-1]:
        if byte == 0xC0:
            escapedPacket.extend([0xDB, 0xDC])

        elif byte == 0xDB:
            escapedPacket.extend([0xDB, 0xDD])

        else:
            escapedPacket.append(byte)

    # Keep the real final packet terminator.
    escapedPacket.append(0xC0)

    return bytes(escapedPacket)