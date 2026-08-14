from datetime import datetime
import threading


_logLock = threading.Lock()


def log_data(data, logFile):
    if data is None:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    if isinstance(data, str):
        line = f"[{timestamp}] {data}"

    else:
        if isinstance(data, int):
            data = bytes([data])
        else:
            data = bytes(data)

        if len(data) == 0:
            return

        formattedData = ", ".join(
            f"0x{byte:02X}"
            for byte in data
        )

        line = f"[{timestamp}] {formattedData}"

    with _logLock:
        logFile.write(line + "\n")
        logFile.flush()