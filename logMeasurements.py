from logData import log_data


def log_measurements(
    currentAngles,
    correctionValues,
    searchWindow,
    status,
    logFile
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
        log_data(line, logFile)

    print()
