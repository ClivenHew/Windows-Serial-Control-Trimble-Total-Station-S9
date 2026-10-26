import os
import time
from datetime import datetime


measurementDirectory = r"C:\Users\clive\OneDrive\Desktop\Serial Communication Data Packets\Measurements"
measurementFilePath = os.path.join(measurementDirectory, "S9 HP Measurements.txt")


def log_measurements(
    currentAngles,
    correctionValues,
    searchWindow,
    status
):
    lines = []

    sighting = currentAngles["sighting"]
    trunnion = currentAngles["trunnion"]

    lines.append("--- Current Trimble Readings ---")
    lines.append("")
    lines.append(f"Horizontal Angle: {currentAngles['horizontalAngle']:.5f} degrees")
    lines.append("")
    lines.append(f"Horizontal Angle Adjustment: {currentAngles['horizontalAngleAdjustment']:.5f} degrees")
    lines.append("")
    lines.append(f"Vertical Angle: {currentAngles['verticalAngle']:.5f} degrees")
    lines.append("")
    lines.append(f"Sighting (Roll Axis): {sighting:.5f} degrees")
    lines.append("")
    lines.append(f"Trunnion (Pitch Axis): {trunnion:.5f} degrees")
    lines.append("")

    if sighting == 0.0 and trunnion == 0.0:
        lines.append("Tilt Status: Out of tilt. More than 0.5 degrees out.")

    elif abs(sighting) > 0.1 or abs(trunnion) > 0.1:
        lines.append("Tilt Status: Out of tilt.")

    else:
        lines.append("Tilt Status: Within tilt.")

    lines.append("")

    if currentAngles["slopeDistance"] is None:
        lines.append("Slope Distance: N.A")
    else:
        lines.append(f"Slope Distance: {currentAngles['slopeDistance']:.5f} meters")

    lines.append("")
    lines.append(f"Face: {currentAngles['face']}")
    lines.append("")
    lines.append(f"Tilt Compensator: {status['tiltCompensator']}")
    lines.append("")
    lines.append("--- Search Window ---")

    for label, key in (
        ("X Axis (Horizontal)", "xAxis"),
        ("Y Axis (Vertical)", "yAxis")
    ):
        value = searchWindow[key]

        if value is None:
            lines.append(f"{label}: N.A")
        else:
            lines.append(f"{label}: {value:.5f} degrees")

    lines.append("")
    lines.append("--- Correction Values ---")

    for label, key in (
        ("Optical Collimation HA", "opticalCollimationHorizontalAngle"),
        ("Optical Collimation VA", "opticalCollimationVerticalAngle"),
        ("Tracker Collimation HA", "trackerCollimationHorizontalAngle"),
        ("Tracker Collimation VA", "trackerCollimationVerticalAngle"),
        ("Trunnion Axis", "trunnionAxis")
    ):
        value = correctionValues[key]

        if value is None:
            lines.append(f"{label}: N.A")
        else:
            lines.append(f"{label}: {value:.5f} degrees")

    for line in lines:
        print(line)

    print()


#Save one indexed, timestamped measurement to S9 HP Measurements.txt
def save_measurement_to_file(currentAngles, status, timeout = 5.0):
    #Wait for the background stream to deliver the new slope distance
    startTime = time.monotonic()
    while currentAngles["slopeDistance"] is None:
        if time.monotonic() - startTime > timeout:
            print("No slope distance received. Measurement not saved.\n")
            return False
        time.sleep(0.05)

    time.sleep(0.2)
    measurement = dict(currentAngles)

    os.makedirs(measurementDirectory, exist_ok = True)

    #Continue numbering from the last index in the file
    index = 1
    if os.path.isfile(measurementFilePath):
        with open(measurementFilePath, "r", encoding = "utf-8") as measurementFile:
            for line in measurementFile:
                firstField = line.split(",", 1)[0].strip()
                if firstField.isdigit():
                    index = int(firstField) + 1

    newFile = (not os.path.isfile(measurementFilePath)
               or os.path.getsize(measurementFilePath) == 0)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    haAdjustment = measurement["horizontalAngleAdjustment"] or 0.0

    entry = (f"{index},{timestamp},"
             f"{measurement['horizontalAngle']:.5f},"
             f"{measurement['verticalAngle']:.5f},"
             f"{measurement['slopeDistance']:.5f},"
             f"{haAdjustment:.5f},"
             f"{measurement['face']},"
             f"{measurement['sighting']:.5f},"
             f"{measurement['trunnion']:.5f},"
             f"{status['targetType']},{status['targetID']}")

    with open(measurementFilePath, "a", encoding = "utf-8") as measurementFile:
        if newFile:
            measurementFile.write("Index,Timestamp,HA (deg),VA (deg),SD (m),"
                                  "HA Adjustment (deg),Face,Sighting (deg),"
                                  "Trunnion (deg),Target Type,Target ID\n")
        measurementFile.write(entry + "\n")

    print(f"Measurement #{index} saved: HA = {measurement['horizontalAngle']:.5f}, "
          f"VA = {measurement['verticalAngle']:.5f}, SD = {measurement['slopeDistance']:.5f} m")
    return True