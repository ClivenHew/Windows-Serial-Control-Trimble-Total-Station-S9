import serial
import time
import threading
from datetime import datetime
from BluetoothInit import bluetooth_init_trimble
from RS232Init import rs232_init_trimble
from backgroundStream import capture_stream
from turnTotalStation import turn_total_station
from setSearchWindow import set_search_window
from setHorizontalAngleAdjustment import set_ha_adjustment
from enableTiltCompensator import enable_tilt_compensator
from disableTiltCompensator import disable_tilt_compensator
from setTargetPrismAdvancedSearchLock import set_target_prismAdvanced_searchLock
from setTargetMultiTrackSearchLock import set_target_multiTrack_searchLock
from setTargetDirectReflex import set_target_directReflex
from enableSearchLock import enable_search_lock
from startSearch import start_search
from stopSearch import stop_search
from getMeasurements import get_measurements
from changeFace import change_face
from getCorrectionValues import get_correction_values
from enableLaserPointer import enable_laser_pointer
from disableLaserPointer import disable_laser_pointer
from logData import log_data
from logMeasurements import log_measurements

logFileName = f"C:/Users/clive/OneDrive/Desktop/Serial Communication Data Packets/TrimbleLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"


#Disconnect from the Trimble device
deviceLogout1 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0x5B, 0x40, 0xC0
]

deviceLogout2 = [
    0x0B, 0x0C, 0x00, 0x00, 0xC9, 0x03, 0xC9, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
]

deviceLogout3 = [
    0x0B, 0x0C, 0x00, 0x00, 0x02, 0x03, 0x02, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
]

status = {
    "trimbleConnection": False,
    "tiltCompensator": False,
    "prismLocked": False,
    "searchState": False,
    "searchFailed": False,
    "laserPointer" : False,
    "backgroundStreamEnabled" : False,
    "targetType" : None,
    "targetID" : None
}

#Store the current angles received from the Trimble device.
currentAngles = {
    "horizontalAngle": None,
    "verticalAngle" : None,
    "horizontalAngleAdjustment": None,
    "sighting": None,
    "trunnion": None,
    "slopeDistance": None,
    "face": "Face 1"
}

#Turn the Trimble device
turnTotalStation = {
    "newHorizontalAngle" : None,
    "newVerticalAngle" : None,
    "newFace" : None,
    "inMovement" : None
}

#Search window
searchWindow = {
    "xAxis" : 0,
    "yAxis" : 0
}

#Store the correction values received from the Trimble device.
correctionValues = {
    "opticalCollimationHorizontalAngle": None,
    "opticalCollimationVerticalAngle": None,
    "trackerCollimationHorizontalAngle": None,
    "trackerCollimationVerticalAngle": None,
    "trunnionAxis": None
}

#Select communication type once before starting the main loop
while True:
    print("\n--- Connection Type ---")
    print("1: Bluetooth")
    print("2: RS232")

    connectionChoice = input("Select connection type: ").strip()

    if connectionChoice == "1":
        connectionType = "Bluetooth"
        connectionBaudRate = 115200
        break

    elif connectionChoice == "2":
        connectionType = "RS232"
        connectionBaudRate = 115200
        break

    else:
        print("Invalid choice. Enter 1 or 2.")


print(
    f"\nSelected connection: {connectionType}, "
    f"{connectionBaudRate} baud"
)

#Start Main Loop
while True:
    #Ask user to open com port
    try:
        while True:
            print("\nCOM Port Format: COM#")
            comPort = input("Enter COM Port: ").strip().upper()

            if not comPort.startswith("COM"):
                print("Invalid COM port. Example format: COM4")
                continue

            if not comPort[3:].isdigit():
                print("Invalid COM port. Example format: COM4")
                continue

            trimbleSerial = None

            try:
                #Bluetooth Serial Port Profile (SPP) settings
                trimbleSerial = serial.Serial()
                trimbleSerial.port = comPort
                trimbleSerial.baudrate = connectionBaudRate
                trimbleSerial.timeout = 1
                trimbleSerial.write_timeout = 2

                print("Opening COM port...")
                trimbleSerial.open()

                print(f"{comPort} opened successfully.")
                break

            except Exception as error:
                print(f"Invalid COM port or port unavailable: {comPort}")
                print(f"Reason: {error}")
                print("Trimble may still be booting. Waiting before retrying.\n")

                try:
                    if trimbleSerial is not None and trimbleSerial.is_open:
                        trimbleSerial.close()
                except Exception:
                    pass

                #Wait 5 seconds
                time.sleep(5)
                continue

    except KeyboardInterrupt:
        print("\nProgram stopped before opening COM port.")
        raise SystemExit
    

    #Once serial communication is established
    try:
        streamStopEvent = None
        streamThread = None

        with trimbleSerial, open(logFileName, "a", encoding="utf-8") as logFile:
            print(f"Logging to: {logFileName}")
            state = "0"

            #Create a parallel thread to monitor background stream
            streamStopEvent = threading.Event()
            streamThread = threading.Thread(
                target = capture_stream,
                args = (
                    trimbleSerial,
                    logFile,
                    streamStopEvent,
                    status,
                    currentAngles,
                    turnTotalStation
                ),
                daemon = True
            )

            #Start background stream
            streamThread.start()

            #Start control loop
            while True:
                match state:
                    #Check if serial communication is established
                    case "0":
                        #If no serial communication
                        if status["trimbleConnection"] == False:
                            #Check bluetooth or RS232 connection type
                            if connectionType == "Bluetooth":
                                #Perform initialization
                                outcome = bluetooth_init_trimble(status = status,
                                                    logFile = logFile,
                                                    currentAngles = currentAngles,
                                                    turnTotalStation = turnTotalStation,
                                                    searchWindow = searchWindow,
                                                    correctionValues = correctionValues,
                                                    trimbleSerial = trimbleSerial)
                            elif connectionType == "RS232":
                                outcome = rs232_init_trimble(status = status,
                                                                logFile = logFile,
                                                                currentAngles = currentAngles,
                                                                turnTotalStation = turnTotalStation,
                                                                searchWindow = searchWindow,
                                                                correctionValues = correctionValues,
                                                                trimbleSerial = trimbleSerial)
                            
                            #If successful initialization
                            if (outcome == True and status["trimbleConnection"] == True):
                                print("Initialization successful.\n")
                                log_data("Initialization successful", logFile)
                                #Go to main menu
                                state = "10"

                            #If failed initialization
                            else:
                                print("Initialization failed.\n")
                                log_data("Initialization failed", logFile)
                                state = "999"
                                time.sleep(5)
                                continue
                        
                        #If serial communication is already established
                        else:
                            print("Connection already established.\n")
                            log_data("Connection already established", logFile)
                            #Go to main menu
                            state = "10"

                    #Main Menu
                    case "10":
                        status["backgroundStreamEnabled"] = True

                        #Select an option from the menu
                        print("\n--- Menu ---")
                        print("100: Enable Tilt Compensator")
                        print("110: Disable Tilt Compensator")
                        print("120: Set Target: Direct Reflex")
                        print("130: Enable Laser Pointer")
                        print("140: Disable Laser Pointer")
                        print("150: Set Search Window")
                        print("160: Set Target: PrismAdvanced")
                        print("170: Set Target: MultiTrack with Prism ID")
                        print("180: Begin Search Operation")
                        print("190: Get Measurements")
                        print("200: Set desired Horizontal Angle")
                        print("300: Turn Total Station (Angles)")
                        print("310: Change Face")
                        print("900: Print HA, VA, Sighting, Trunnion, adjustment HA")
                        print("999: Restart connection with Trimble device")
                        print("1000: Exit program")

                        state = input("Enter your choice: ")
                    

                    #Enable Tilt Compensator
                    case "100":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            state = "0"
                            continue

                        #Enable Tilt Compensator
                        outcome = enable_tilt_compensator(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)
                        
                        #If successfully enabled tilt compensator
                        if outcome == True:
                            print("Tilt compensator enabled.\n")
                            log_data("Tilt compensator enabled", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                        
                        #If not successfully enabled tilt compensator
                        elif outcome == False:
                            print("Failed to enable tilt compensator.\n")
                            log_data("Failed to enable tilt compensator", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                    
                    #Disable Tilt Compensator
                    case "110":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue

                        outcome = disable_tilt_compensator(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)
                        
                        #If successfully disabled tilt compensator
                        if outcome == True:
                            print("Tilt compensator disabled.\n")
                            log_data("Tilt compensator disabled", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                        
                        #If not successfully disabled tilt compensator
                        elif outcome == False:
                            print("Failed to disabled tilt compensator.\n")
                            log_data("Failed to disabled tilt compensator", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"


                    #Set Target: Direct Reflex
                    case "120":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue
                        
                        outcome = set_target_directReflex(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)

                        #If successfully set target
                        if outcome == True:
                            print("Target successfully set to Direct Reflex.\n")
                            log_data("Target successfully set to Direct Reflex", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                        
                        #If failed to set target
                        elif outcome == False:
                            print("Target failed to set to Direct Reflex.\n")
                            log_data("Target failed to set to Direct Reflex", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"


                    #Enable Laser Pointer
                    case "130":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue

                        #Check if target is set to Direct Reflex before enabling laser pointer
                        if status["targetType"] != "Direct Reflex":
                            print("Laser pointer can only be enabled when target is set to Direct Reflex.\n")
                            log_data("Laser pointer can only be enabled when target is set to Direct Reflex", logFile)
                            state = "10"
                            continue

                        outcome = enable_laser_pointer(trimbleSerial = trimbleSerial,
                                                    logFile = logFile,
                                                    status = status)
                        
                        #If successfully set target
                        if outcome == True:
                            print("Successfuly enabled laser pointer.\n")
                            log_data("Successfuly enabled laser pointer", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                        
                        #If failed to set target
                        elif outcome == False:
                            print("Failed to enable laser pointer.\n")
                            log_data("Failed to enable laser pointer", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"


                    #Disable Laser Pointer
                    case "140":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue

                        outcome = disable_laser_pointer(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)

                        if outcome == True:
                            print("Laser pointer disabled.\n")
                            log_data("Laser pointer disabled", logFile)
                            time.sleep(1.5)
                            state = "10"
                        else:
                            print("Failed to disable laser pointer.\n")
                            log_data("Failed to disable laser pointer", logFile)
                            time.sleep(1.5)
                            state = "10"


                    #Set Search Window
                    case "150":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            if (currentAngles["horizontalAngle"] is None or currentAngles["verticalAngle"] is None):
                                print("Background Stream not received yet.\n")
                                log_data("Background Stream not received yet", logFile)
                                state = "10"
                                continue

                            searchWindow["xAxis"] = float(input("Enter horizontal angle window in degrees: "))
                            searchWindow["yAxis"] = float(input("Enter vertical angle window in degrees: "))

                            outcome = set_search_window(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        currentAngles = currentAngles,
                                                        searchWindow = searchWindow,
                                                        status = status)
                            
                            #If successfully set search window
                            if outcome == True:
                                print("Search window successfully configured.\n")
                                log_data("Search window successfully configured", logFile)
                                time.sleep(1.5)
                                state = "10"
                            
                            #If fail to set search window
                            elif outcome == False:
                                print("Search window failed to be configured.\n")
                                log_data("Search window failed to be configured", logFile)
                                time.sleep(1.5)
                                #Go to main menu
                                state = "10"
                        
                        except ValueError as error:
                            print(f"\nInvalid input: {error}")
                            state = "10"
                        
                        except KeyboardInterrupt:
                            print("\nStopped setting search window.")
                            state = "10"


                    #Set Target: PrismAdvanced
                    case "160":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue
                        
                        outcome = set_target_prismAdvanced_searchLock(trimbleSerial = trimbleSerial,
                                                                    logFile = logFile,
                                                                    status = status)

                        #If successfully set target
                        if outcome == True:
                            print("Target successfully set to PrismAdvanced with SearchLock.\n")
                            log_data("Target successfully set to PrismAdvanced with SearchLock", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"
                        
                        #If failed to set target
                        elif outcome == False:
                            print("Target failed to set to PrismAdvanced with SearchLock.\n")
                            log_data("Target failed to set to PrismAdvanced with SearchLock", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"


                    #Set Target: MultiTrack with Prism ID
                    case "170":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue
                        
                        outcome = set_target_multiTrack_searchLock(trimbleSerial = trimbleSerial,
                                                                    logFile = logFile,
                                                                    status = status)

                        #If successfully set target
                        if outcome == True:
                            print("Target successfully set to MultiTrack with SearchLock.\n")
                            log_data("Target successfully set to MultiTrack with SearchLock", logFile)
                            time.sleep(1.5)
                            state = "10"
                        
                        #If failed to set target
                        elif outcome == False:
                            print("Target failed to set to PrismAdvanced with SearchLock.\n")
                            log_data("Target failed to set to PrismAdvanced with SearchLock", logFile)
                            time.sleep(1.5)
                            #Go to main menu
                            state = "10"


                    #Stop any search operation first
                    case "180":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue

                        outcome = stop_search(trimbleSerial=trimbleSerial, logFile=logFile, status=status)

                        if outcome == True:
                            status["prismLocked"] = False
                            status["searchState"] = False
                            time.sleep(1.5)
                            state = "183"
                        else:
                            print("Failed to stop current active prism lock.\n")
                            log_data("Failed to stop current active prism lock", logFile)
                            time.sleep(1.5)
                            state = "10"

                    case "183":
                        #Enable target search and search lock operation
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            outcome = enable_search_lock(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)
                            
                            #If successfully enabled target search
                            if outcome == True:
                                print("Target search and search lock successfully enabled.\n")
                                log_data("Target search and search lock successfully enabled", logFile)
                                time.sleep(1.5)
                                #Go to next step
                                state = "185"
                            
                            #If failed to enable target search
                            elif outcome == False:
                                print("Target search and search lock failed.\n")
                                log_data("Target search and search lock failed", logFile)
                                time.sleep(1.5)
                                #Go back to main menu
                                state = "10"
                        
                        except KeyboardInterrupt:
                            print("\nStopped enabling target search.")
                            log_data("Stopped enabling target search", logFile)
                            state = "10"

                    #Start search operation
                    case "185":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            #Check that search window has been set beyond 2 degrees HA and VA
                            if (searchWindow["xAxis"] < 2 or searchWindow["yAxis"] < 2):
                                print("Search window must be set to at least 2 degrees for both HA and VA.\n")
                                log_data("Search window must be set to at least 2 degrees for both HA and VA", logFile)
                                time.sleep(1.5)
                                state = "10"
                                continue
                            
                            outcome = start_search(trimbleSerial = trimbleSerial,
                                                logFile = logFile,
                                                status = status)
                            
                            if outcome == True:
                                print("Prism locked on.\n")
                                log_data("Prism locked on", logFile)
                                time.sleep(1.5)
                                state = "10"
                            
                            elif outcome == False:
                                print("Prism failed to be found. Cancelling search.\n")
                                log_data("Prism failed to be found. Cancelling search", logFile)

                                #Stop the search operation if total station is still in movement
                                if status["searchState"] == True or status["searchFailed"] == True:
                                    outcome2 = stop_search(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)
                                    if outcome2 == True:
                                        print("Search operation cancelled.\n")
                                        log_data("Search operation cancelled", logFile)
                                        status["prismLocked"] = False
                                        status["searchState"] = False
                                        status["backgroundStreamEnabled"] = True
        
                                        time.sleep(1.5)
                                        state = "10"

                                    else:
                                        print("Failed to cancel search operation. Restarting total station.\n")
                                        log_data("Failed to cancel search operation. Restarting total station", logFile)
                                        #Restart total station
                                        status["trimbleConnection"] = False
                                        time.sleep(1.5)
                                        state = "999"
                                        continue

                                #If total station is not in movement, go back to main menu
                                else:
                                    print("Search operation cancelled.\n")
                                    log_data("Search operation cancelled", logFile)
                                    status["prismLocked"] = False
                                    status["searchState"] = False
                                    status["backgroundStreamEnabled"] = True
                                    time.sleep(1.5)
                                    state = "10"
                        
                        except KeyboardInterrupt:
                            print("\nSearchLock monitoring stopped.")
                            time.sleep(1.5)
                            state = "10"


                    #Get angle and distance measurements
                    case "190":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            if status["targetType"] is None:
                                print("Target type not yet selected.\n")
                                log_data("Target type not yet selected", logFile)
                                state = "0"
                                continue

                            outcome = get_measurements(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        status = status)

                            if outcome == True:
                                print("Angle and Distance measurements retrieved.\n")
                                log_data("Angle and Distance measurements retrieved", logFile)
                                time.sleep(1.5)
                                state = "10"
                            
                            elif outcome == False:
                                print("Angle and Distance measurements failed to be retrieved.\n")
                                log_data("Angle and Distance measurements failed to be retrieved", logFile)
                                time.sleep(1.5)
                                state = "10"

                        except KeyboardInterrupt:
                            print("\nStopped retrieving angle and distance measurements.")
                            log_data("Stopped retrieving angle and distance measurements", logFile)
                            state = "10"

                    
                    #Set desired horizontal angle
                    case "200":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            if (currentAngles["horizontalAngle"] is None or currentAngles["horizontalAngleAdjustment"] is None):
                                print("Background Stream not received yet.\n")
                                log_data("Background Stream not received yet", logFile)
                                state = "10"
                                continue

                            desiredHA = float(input("Enter desired displayed HA in degrees: "))

                            outcome = set_ha_adjustment(
                                trimbleSerial = trimbleSerial,
                                logFile = logFile,
                                desiredHA = desiredHA,
                                currentAngles = currentAngles,
                                status = status
                            )

                            if outcome:
                                print("HA adjustment updated.\n")
                                log_data("HA adjustment updated", logFile)
                            else:
                                print("Failed to update HA adjustment.\n")
                                log_data("Failed to update HA adjustment", logFile)

                            time.sleep(1.5)
                            state = "10"

                        except ValueError as error:
                            print(f"\nInvalid input: {error}")
                            time.sleep(1.5)
                            state = "10"

                        except KeyboardInterrupt:
                            print("\nStopped setting HA adjustment.")
                            time.sleep(1.5)
                            state = "10"


                    #Turn total station to target HA/VA
                    case "300":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            if (currentAngles["horizontalAngle"] is None or currentAngles["horizontalAngleAdjustment"] is None):
                                print("Background Stream not received yet.\n")
                                log_data("Background Stream not received yet", logFile)
                                state = "10"
                                continue

                            #Perform total station turn
                            outcome = turn_total_station(trimbleSerial = trimbleSerial,
                                                        logFile = logFile,
                                                        turnTotalStation = turnTotalStation,
                                                        currentAngles = currentAngles,
                                                        status = status)
                            
                            if outcome == True:
                                print("Total Station has turned to desired angles.\n")
                                log_data("Total Station has turned to desired angles", logFile)
                                time.sleep(1.5)
                                state = "10"

                            else:
                                print("Total Station did not turn to desired angles. Restarting total station.\n")
                                log_data("Total Station did not turn to desired angles. Restarting total station.", logFile)
                                time.sleep(1.5)
                                state = "999"
                                continue
                        
                        except KeyboardInterrupt:
                            print("\nStopped turning total station.")
                            log_data("Stopped turning total station", logFile)
                            time.sleep(1.5)
                            state = "10"


                    # Change Face
                    case "310":
                        try:
                            if status["trimbleConnection"] == False:
                                print("Serial communication is not yet established.\n")
                                log_data("Serial communication is not yet established", logFile)
                                state = "0"
                                continue

                            outcome = change_face(
                                status=status,
                                trimbleSerial=trimbleSerial,
                                logFile = logFile,
                                turnTotalStation=turnTotalStation,
                                currentAngles=currentAngles
                            )

                            if outcome:
                                print("Face changed successfully.\n")
                                log_data("Face changed successfully", logFile)
                                time.sleep(1.5)
                                state = "10"

                            else:
                                print("Face change failed. Restarting total station.\n")
                                log_data("Face change failed. Restarting total station.", logFile)
                                time.sleep(1.5)
                                state = "999"
                                continue

                        except KeyboardInterrupt:
                            print("\nStopped changing face.")
                            log_data("Stopped changing face.", logFile)
                            time.sleep(1.5)
                            state = "10"


                    #Print measurement variables
                    case "900":
                        if status["trimbleConnection"] == False:
                            print("Serial communication is not yet established.\n")
                            log_data("Serial communication is not yet established", logFile)
                            state = "0"
                            continue

                        #Wait for 3 seconds to allow the latest readings
                        time.sleep(3)

                        #Check if at least one variable has updated in the background stream
                        if currentAngles["horizontalAngle"] is None:
                            print("Stream measurement has not yet been received.\n")
                            log_data("Stream measurement has not yet been received", logFile)
                            state = "10"
                            continue

                        #Print all readings
                        log_measurements(
                            currentAngles=currentAngles,
                            correctionValues=correctionValues,
                            searchWindow=searchWindow,
                            status=status,
                            logFile=logFile
                        )

                        time.sleep(1.5)
                        #Go back to main menu
                        state = "10"


                    #Restart connection
                    case "999":
                        print("Restart connection with Trimble device")
                        log_data("Restart connection with Trimble device", logFile)

                        status["trimbleConnection"] = False
                        status["tiltCompensator"] = False
                        status["targetType"] = None
                        status["targetID"] = None
                        status["prismLocked"] = False
                        status["searchState"] = False

                        currentAngles["horizontalAngle"] = None
                        currentAngles["verticalAngle"] = None
                        currentAngles["horizontalAngleAdjustment"] = None
                        currentAngles["sighting"] = None
                        currentAngles["trunnion"] = None
                        currentAngles["slopeDistance"] = None
                        currentAngles["face"] = "Face 1"

                        searchWindow["xAxis"] = 0
                        searchWindow["yAxis"] = 0

                        turnTotalStation["newHorizontalAngle"] = None
                        turnTotalStation["newVerticalAngle"] = None
                        turnTotalStation["newFace"] = None
                        turnTotalStation["inMovement"] = None

                        try:
                            trimbleSerial.write(bytes(deviceLogout1))
                            trimbleSerial.flush()
                            time.sleep(0.05)

                            trimbleSerial.write(bytes(deviceLogout2))
                            trimbleSerial.flush()
                            time.sleep(0.05)

                            trimbleSerial.write(bytes(deviceLogout3))
                            trimbleSerial.flush()

                        except (serial.SerialException, OSError) as error:
                            print(f"Disconnect failed because serial port is unavailable: {error}")
                            log_data(f"Disconnect failed because serial port is unavailable: {error}", logFile)

                        state = "0"


                    #Exit program
                    case "1000":
                        print("Closing COM Port Connection\n")
                        log_data("Closing COM Port Connection", logFile)
                        streamStopEvent.set()
                        streamThread.join(timeout=1)
                        break

                    case _:
                        print("Invalid choice.\n")
                        state = "10"

            if streamStopEvent.is_set():
                break

    except (serial.SerialException, OSError) as error:
        print(f"\nSerial communication failed: {error}")
        print("Trimble may still be booting. Please try again.\n")

        try:
            if streamStopEvent is not None:
                streamStopEvent.set()

            if streamThread is not None:
                streamThread.join(timeout=1)

        except Exception:
            pass

        try:
            trimbleSerial.close()
        except Exception:
            pass

        status["trimbleConnection"] = False
        status["backgroundStreamEnabled"] = False

        time.sleep(2)
        continue

    except Exception as error:
        print(f"\nSerial session crashed: {error}")
        print("Returning to COM-port selection.\n")

        try:
            if streamStopEvent is not None:
                streamStopEvent.set()

            if streamThread is not None:
                streamThread.join(timeout=1)

        except Exception:
            pass

        try:
            trimbleSerial.close()
        except Exception:
            pass

        status["trimbleConnection"] = False
        status["backgroundStreamEnabled"] = False

        time.sleep(5)
        continue
