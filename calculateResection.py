import os
import math
from logMeasurements import measurementFilePath


#Read every entry in S9 HP Measurements.txt into a list of dictionaries
def read_measurement_file():
    measurements = []

    with open(measurementFilePath, "r", encoding = "utf-8") as measurementFile:
        for line in measurementFile:
            fields = line.strip().split(",")

            #Skip header and incomplete lines
            if len(fields) < 5 or not fields[0].strip().isdigit():
                continue

            try:
                measurements.append({
                    "index": int(fields[0]),
                    "timestamp": fields[1].strip(),
                    "date": fields[1].strip().split(" ")[0],
                    "horizontalAngle": float(fields[2]),
                    "verticalAngle": float(fields[3]),
                    "slopeDistance": float(fields[4]) * 1000.0     #metres to mm
                })
            except ValueError:
                continue

    return measurements


#Ask user to pick one date from the dates found in the file
def select_date(measurements):
    dates = sorted(set(measurement["date"] for measurement in measurements))

    print("\n--- Available Dates ---")
    for number, date in enumerate(dates, start = 1):
        count = sum(1 for measurement in measurements if measurement["date"] == date)
        print(f"{number}: {date} ({count} measurements)")

    while True:
        choice = input("Select date: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(dates):
            return dates[int(choice) - 1]

        print("Invalid choice.")


#Show measurements of the selected date and ask user to pick 3 indexes
def select_three_measurements(measurements, selectedDate):
    dayMeasurements = [measurement for measurement in measurements if measurement["date"] == selectedDate]

    print(f"\n--- Measurements on {selectedDate} ---")
    print(f"{'Index':>6}  {'Time':<12}  {'HA (deg)':>11}  {'VA (deg)':>10}  {'SD (mm)':>10}")
    for measurement in dayMeasurements:
        print(f"{measurement['index']:>6}  "
              f"{measurement['timestamp'].split(' ')[1]:<12}  "
              f"{measurement['horizontalAngle']:>11.5f}  "
              f"{measurement['verticalAngle']:>10.5f}  "
              f"{measurement['slopeDistance']:>10.1f}")

    byIndex = {measurement["index"]: measurement for measurement in dayMeasurements}
    prompts = ("Index of Prism A (origin, 0,0,0): ",
               "Index of Prism B (defines +X axis): ",
               "Index of Prism C (third prism): ")
    selected = []

    for prompt in prompts:
        while True:
            choice = input(prompt).strip()

            if not choice.isdigit() or int(choice) not in byIndex:
                print("Index not found on this date.")
                continue

            if int(choice) in [measurement["index"] for measurement in selected]:
                print("Index already selected.")
                continue

            selected.append(byIndex[int(choice)])
            break

    return selected


#Split slope distance into horizontal and vertical distance
#VD is positive when the prism is below the total station (VA > 90)
def split_slope_distance(measurement):
    angleFromHorizontal = math.radians(measurement["verticalAngle"] - 90.0)

    horizontalDistance = measurement["slopeDistance"] * math.cos(angleFromHorizontal)
    verticalDistance = measurement["slopeDistance"] * math.sin(angleFromHorizontal)

    return horizontalDistance, verticalDistance


#Inner angle at the total station between two prisms (always 0 to 180 degrees)
def angle_at_total_station(haFirst, haSecond):
    difference = abs(haSecond - haFirst) % 360.0

    if difference > 180.0:
        difference = 360.0 - difference

    return difference


#Cosine rule: side opposite the angle
def cosine_rule_side(sideB, sideC, angleDegrees):
    return math.sqrt(sideB ** 2 + sideC ** 2
                     - 2 * sideB * sideC * math.cos(math.radians(angleDegrees)))


#Cosine rule: angle between sideB and sideC, opposite sideA
def cosine_rule_angle(sideA, sideB, sideC):
    cosineValue = (sideB ** 2 + sideC ** 2 - sideA ** 2) / (2 * sideB * sideC)
    cosineValue = max(-1.0, min(1.0, cosineValue))
    return math.degrees(math.acos(cosineValue))


#Calculate prism and total station coordinates
def calculate_resection(prismA, prismB, prismC):
    hdA, vdA = split_slope_distance(prismA)
    hdB, vdB = split_slope_distance(prismB)
    hdC, vdC = split_slope_distance(prismC)

    #Distance A to B (triangle A, TS, B)
    angleAB = angle_at_total_station(prismA["horizontalAngle"], prismB["horizontalAngle"])
    distanceAB = cosine_rule_side(hdA, hdB, angleAB)

    #Distance A to C (triangle A, TS, C)
    angleAC = angle_at_total_station(prismA["horizontalAngle"], prismC["horizontalAngle"])
    distanceAC = cosine_rule_side(hdA, hdC, angleAC)

    #Distance B to C (triangle B, TS, C)
    angleBC = angle_at_total_station(prismB["horizontalAngle"], prismC["horizontalAngle"])
    distanceBC = cosine_rule_side(hdB, hdC, angleBC)

    #Prism B lies on the +X axis
    coordinatesB = [distanceAB, 0.0]

    #Angle at A between A-B and A-C (triangle A, B, C)
    theta = cosine_rule_angle(distanceBC, distanceAB, distanceAC)

    #Angle at A between A-B and A-TS (triangle A, TS, B)
    alpha = cosine_rule_angle(hdB, distanceAB, hdA)

    #Side of total station: if B is less than 180 deg clockwise from A (seen from TS),
    #the total station is on the right of A->B, so Y is negative (+Y points left)
    clockwiseAToB = (prismB["horizontalAngle"] - prismA["horizontalAngle"]) % 360.0
    sideTS = -1.0 if clockwiseAToB < 180.0 else 1.0

    coordinatesTS = [hdA * math.cos(math.radians(alpha)),
                     sideTS * hdA * math.sin(math.radians(alpha))]

    #Prism C: two possible sides, keep the one that is HD_C away from the total station
    candidates = []
    for side in (1.0, -1.0):
        candidate = [distanceAC * math.cos(math.radians(theta)),
                     side * distanceAC * math.sin(math.radians(theta))]
        distanceToTS = math.hypot(candidate[0] - coordinatesTS[0], candidate[1] - coordinatesTS[1])
        candidates.append((abs(distanceToTS - hdC), candidate))
    coordinatesC = min(candidates)[1]

    #Heights: A is 0, total station is VD_A above A
    heightTS = vdA
    heightB = heightTS - vdB
    heightC = heightTS - vdC

    #Check: back calculate total station from prism coordinates (circle subtraction)
    #A and B both have Y = 0, so subtracting their circles gives TS_x directly
    checkX = (hdA ** 2 - hdB ** 2 + distanceAB ** 2) / (2 * distanceAB)
    #Subtracting circles A and C gives a linear equation in TS_x and TS_y
    cx, cy = coordinatesC
    checkY = (hdA ** 2 - hdC ** 2 + cx ** 2 + cy ** 2 - 2 * cx * checkX) / (2 * cy)

    return {
        "horizontalDistance": (hdA, hdB, hdC),
        "verticalDistance": (vdA, vdB, vdC),
        "angleAtTS": (angleAB, angleAC, angleBC),
        "distances": (distanceAB, distanceAC, distanceBC),
        "theta": theta,
        "alpha": alpha,
        "prismA": (0.0, 0.0, 0.0),
        "prismB": (coordinatesB[0], coordinatesB[1], heightB),
        "prismC": (coordinatesC[0], coordinatesC[1], heightC),
        "totalStation": (coordinatesTS[0], coordinatesTS[1], heightTS),
        "checkTotalStation": (checkX, checkY, heightTS)
    }


#Print all results to console
def print_resection(result, prismA, prismB, prismC):
    hdA, hdB, hdC = result["horizontalDistance"]
    vdA, vdB, vdC = result["verticalDistance"]
    angleAB, angleAC, angleBC = result["angleAtTS"]
    distanceAB, distanceAC, distanceBC = result["distances"]

    print("\n--- Split Slope Distance ---")
    for name, prism, hd, vd in (("A", prismA, hdA, vdA), ("B", prismB, hdB, vdB), ("C", prismC, hdC, vdC)):
        print(f"Prism {name} (#{prism['index']}): HD = {hd:.3f} mm, VD = {vd:.3f} mm")

    print("\n--- Distances Between Prisms (Cosine Rule) ---")
    print(f"A-B: angle at TS = {angleAB:.4f} deg, distance = {distanceAB:.3f} mm")
    print(f"A-C: angle at TS = {angleAC:.4f} deg, distance = {distanceAC:.3f} mm")
    print(f"B-C: angle at TS = {angleBC:.4f} deg, distance = {distanceBC:.3f} mm")

    print("\n--- Angles at Prism A ---")
    print(f"Theta (A-B to A-C)  = {result['theta']:.4f} deg")
    print(f"Alpha (A-B to A-TS) = {result['alpha']:.4f} deg")

    print("\n--- Coordinates (mm) ---")
    print("Origin = Prism A, +X = Prism A to Prism B, +Y = left, +Z = up")
    print(f"{'Point':<16}{'X':>12}{'Y':>12}{'Z':>12}")
    for label, coordinates in (("Prism A", result["prismA"]),
                               ("Prism B", result["prismB"]),
                               ("Prism C", result["prismC"]),
                               ("Total Station", result["totalStation"])):
        print(f"{label:<16}{coordinates[0]:>12.3f}{coordinates[1]:>12.3f}{coordinates[2]:>12.3f}")

    checkX, checkY, _ = result["checkTotalStation"]
    tsX, tsY, _ = result["totalStation"]
    print("\n--- Check: Back Calculation by Circle Subtraction ---")
    print(f"Total Station = ({checkX:.3f}, {checkY:.3f})")
    print(f"Difference    = ({checkX - tsX:.3f}, {checkY - tsY:.3f}) mm\n")


#Main function called from main.py case 400
def calculate_total_station_coordinates():
    #1. Check that file exists
    if not os.path.isfile(measurementFilePath):
        print(f"Measurement file not found: {measurementFilePath}\n")
        return False

    measurements = read_measurement_file()

    if len(measurements) < 3:
        print("At least 3 measurements are required.\n")
        return False

    #2. Select date
    selectedDate = select_date(measurements)

    if sum(1 for measurement in measurements if measurement["date"] == selectedDate) < 3:
        print("At least 3 measurements are required on the selected date.\n")
        return False

    #3 and 4. Show measurements and select 3
    prismA, prismB, prismC = select_three_measurements(measurements, selectedDate)

    #5 to 7. Calculate
    result = calculate_resection(prismA, prismB, prismC)

    #8. Print
    print_resection(result, prismA, prismB, prismC)

    return True
