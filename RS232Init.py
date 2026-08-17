import time
from logData import log_data
from unescapeBytes import escape_bytes

#Handshake payload to wake up the Trimble device.
trimbleHandshake =  [
                    0xFF, 0xC0, 0x0B, 0x0C, 0x00, 0x00, 0x00, 0x09, 
                    0x00, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
                    ]
                
#Define the two-part authentication payloads to send to the Trimble device.
deviceAuthentication1 = [
    0x0B, 0x0C, 0x00, 0x00, 0x02, 0x01, 0x02, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
]

deviceAuthentication2 = [
    0x0B, 0x0C, 0x00, 0x00, 0x02, 0x0B, 0x02, 0x39, 0x30, 0x00, 0x00, 0x00, 0xC0
]

#Request for challenge from Trimble to authorize device
trimbleRequestChallenge = [
    0x13, 0x09, 0x00, 0x01, 0x02, 0xA0, 0x40, 0x64, 0x00, 0xC0
]

#17-part Initialization sequence
trimbleInitSequence1 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0x5B, 0x40, 0xC0
]

trimbleInitSequence2 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xAB, 0x40, 0xC0
]

trimbleInitSequence3 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xA2, 0x40, 0xC0
]

trimbleInitSequence4 = [
    0x13, 0x0B, 0x00, 0x01, 0x02, 0xBF, 0x40, 0xEA, 0x07, 0x06, 0x1D, 0xC0
]

trimbleInitSequence5 = [
    0x13, 0x08, 0x00, 0x01, 0x02, 0xE4, 0x40, 0x02, 0xC0
]

trimbleInitSequence6 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xAD, 0x40, 0xC0
]

trimbleInitSequence7 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xC8, 0x41, 0xC0
]

trimbleInitSequence8 = [
    0x13, 0x08, 0x00, 0x01, 0x02, 0x68, 0x40, 0x05, 0xC0
]

trimbleInitSequence9 = [
    0x13, 0x08, 0x00, 0x01, 0x02, 0xA7, 0x41, 0x02, 0xC0
]

trimbleInitSequence10 = [
    0x13, 0x0B, 0x00, 0x01, 0x02, 0x99, 0x40, 0x01, 0x01, 0x02, 0x01, 0xC0
]

trimbleInitSequence11 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xAE, 0x40, 0xC0
]

trimbleInitSequence12 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0x9F, 0x40, 0xC0
]

trimbleInitSequence13 = [
    0x13, 0x07, 0x00, 0x01, 0x02, 0xBD, 0x40, 0xC0
]

trimbleInitSequence14 = [
    0x13, 0x09, 0x00, 0x01, 0x02, 0x87, 0x40, 0x00, 0x00, 0xC0
]

def rs232_init_trimble(status, logFile, currentAngles, turnTotalStation, searchWindow, correctionValues, trimbleSerial):
    try:
        initializationTimeout = 15
        state = 0
        trimbleBuffer = bytearray()

        while True:
            match state:
                #Check if there is an existing connection
                case 0:
                    if status["trimbleConnection"]:
                            print("\nTrimble is already connected.")
                            print("Disconnect first before starting initialization again.")
                            return True
                    else:
                        #Reset all the variables
                        status["trimbleConnection"] = False
                        status["prismTarget"] = False
                        status["searchWindow"] = False
                        status["tiltCompensator"] = False
                        status["searchLock"] = False
                        status["prismLocked"] = False
                        status["searchState"] = False
                        status["powerSource"] = None
                        status["laserPointer"] = False

                        currentAngles["horizontalAngle"] = None
                        currentAngles["verticalAngle"] = None
                        currentAngles["horizontalAngleAdjustment"] = None
                        currentAngles["sighting"] = None
                        currentAngles["trunnion"] = None
                        currentAngles["slopeDistance"] = None
                        currentAngles["face"] = "Face 1"

                        turnTotalStation["newHorizontalAngle"] = None
                        turnTotalStation["newVerticalAngle"] = None
                        turnTotalStation["newFace"] = None
                        turnTotalStation["inMovement"] = None
                        turnTotalStation["angleTurnFlag"] = False
                        turnTotalStation["faceTurnFlag"] = False

                        searchWindow["xAxis"] = 0
                        searchWindow["yAxis"] = 0

                        correctionValues["opticalCollimationHorizontalAngle"] = 0
                        correctionValues["opticalCollimationVerticalAngle"] = 0
                        correctionValues["trackerCollimationHorizontalAngle"] = 0
                        correctionValues["trackerCollimationVerticalAngle"] = 0
                        correctionValues["trunnionAxis"] = 0

                        #Go to next state
                        state = 10
                
                #Send Handshake
                case 10:
                    print("Sending Handshake\n")
                    log_data(trimbleHandshake, logFile)
                    #Send handshake data packet
                    trimbleSerial.write(bytes(trimbleHandshake))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Handshake timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Handshake initialization timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for handshake acknowledgement
                            if b'\x2B\x3E\x00\x00\x00\x0A\x00' in trimbleBuffer:
                                print("Handshake received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 20
                                break
                    
                
                #Device Authentication 1
                case 20:
                    print("Sending Device Authentication 1\n")
                    log_data(deviceAuthentication1, logFile)
                    #Send handshake data packet
                    trimbleSerial.write(bytes(deviceAuthentication1))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Device Authentication 1 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Device Authentication 1 initialization timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for handshake acknowledgement
                            if b'\x2B\x0C\x00\x02\x00\x02\x01\x02\x39\x30\x00\x00\xC0' in trimbleBuffer:
                                print("Device Authentication 1 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 30
                                break
                    
                
                                #Device Authentication 2
                case 30:
                    print("Sending Device Authentication 2\n")
                    log_data(deviceAuthentication2, logFile)
                    #Send authentication 2 data packet
                    trimbleSerial.write(bytes(deviceAuthentication2))
                    trimbleSerial.flush()

                    authentication2Received = False
                    keepAliveCount = 0
                    nextKeepAliveTime = None

                    keepAlivePacket = b'\xFF\xC0'
                    backgroundStreamHeader = b'\x02\x45\x00\x02\x01\x64'

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Device Authentication 2 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Device Authentication 2 initialization timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for authentication 2 acknowledgement
                            if (authentication2Received == False and b'\x2B\x0C\x00\x02\x00\x0C\x01\x02' in trimbleBuffer):
                                print("Device Authentication 2 received.\n")
                                authentication2Received = True

                                #Find the end of the authentication response
                                end = trimbleBuffer.find(b'\xC0') + 1

                                #Log the authentication response
                                log_data(trimbleBuffer[:end], logFile)

                                #Remove data through the authentication frame
                                del trimbleBuffer[:end]

                                #Send the first keep-alive after approximately 2.7 seconds
                                nextKeepAliveTime = time.monotonic() + 2.7

                        #Once acknowledgement is received, send two keep-alive packets
                        if authentication2Received == True and keepAliveCount < 2:
                            if time.monotonic() >= nextKeepAliveTime:
                                print(f"Sending Keep-Alive {keepAliveCount + 1}\n")
                                log_data(keepAlivePacket, logFile)

                                #Send keep-alive packet to the Trimble device
                                trimbleSerial.write(keepAlivePacket)
                                trimbleSerial.flush()

                                keepAliveCount += 1

                                #Send the next keep-alive after approximately 2.7 seconds
                                nextKeepAliveTime = time.monotonic() + 2.7

                        #Once both keep-alives are sent, wait for the background stream
                        if authentication2Received == True and keepAliveCount == 2:
                            streamStart = trimbleBuffer.find(backgroundStreamHeader)

                            #If background stream header is found
                            if streamStart != -1:
                                #Find the end of the background stream packet
                                streamEnd = trimbleBuffer.find(b'\xC0', streamStart)

                                #If complete background stream packet is received
                                if streamEnd != -1:
                                    print("Initial background stream received.\n")

                                    #Store the complete background stream packet
                                    streamPacket = trimbleBuffer[streamStart:streamEnd + 1]

                                    #Log the background stream packet
                                    log_data(streamPacket, logFile)

                                    #Remove data through the background stream packet
                                    del trimbleBuffer[:streamEnd + 1]

                                    #SDK waited approximately 1 second after receiving the background stream
                                    time.sleep(1)

                                    #Go to request challenge
                                    state = 40
                                    break

                        time.sleep(0.001)
                

                #Request for Challenge
                case 40:
                    print("Send Request for Challenge.\n")
                    log_data(trimbleRequestChallenge, logFile)
                    #Send handshake data packet
                    trimbleSerial.write(bytes(trimbleRequestChallenge))

                    #Check if success or failure
                    success = b'\x12\x0C\x00\x02\x01\xA0\x80\x00'
                    fail = b'\x12\x08\x00\x02\x01\xA0\x80\x62\xC0'
                    fail62 = b'\x12\x08\x00\x02\x01\xA0\x80\x62\xC0'
                    fail63 = b'\x12\x08\x00\x02\x01\xA0\x80\x63\xC0'

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Request for Challenge timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Request for Challenge initialization timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #If challenge is found in data packet
                            if success in trimbleBuffer:
                                start = trimbleBuffer.find(success)
                                end = trimbleBuffer.find(b'\xC0', start)
                                
                                #If end not found yet, continue accumulating data packets
                                if end == -1:
                                    continue

                                #Store challenge packet
                                challengePacket = bytes(trimbleBuffer[start:end + 1])

                                #Decode escaped DB/C0 bytes before extracting the last four.
                                decodedPacket = challengePacket[:-1]
                                decodedPacket = decodedPacket.replace(b'\xDB\xDC', b'\xC0')
                                decodedPacket = decodedPacket.replace(b'\xDB\xDD', b'\xDB')

                                trimbleChallenge = decodedPacket[-4:]

                                print("Challenge Found.\n")

                                log_data(trimbleBuffer, logFile)

                                #Clear buffer
                                trimbleBuffer.clear()

                                #Go to next step to respond to challenge
                                state = 45
                                break

                            #If no challenge is found in data packet
                            elif fail in trimbleBuffer:
                                print("Failed to request for challenge.\n")

                                log_data(trimbleBuffer, logFile)

                                #Clear buffer
                                trimbleBuffer.clear()
                                return False

                            elif fail62 in trimbleBuffer or fail63 in trimbleBuffer:
                                print("Challenge not ready yet. Retrying request for challenge.\n")
                                log_data("Challenge not ready yet. Retrying request for challenge", logFile)
                                log_data(trimbleBuffer, logFile)

                                trimbleBuffer.clear()

                                time.sleep(1)

                                trimbleSerial.write(bytes(trimbleRequestChallenge))
                                trimbleSerial.flush()

                                initializationStartTime = time.monotonic()
                                previousCountdown = None

                                continue
                    

                #Respond to challenge
                case 45:
                    trimbleBuffer = bytearray()
                    print("Send Response to Challenge\n")

                    #Convert challenge to the DLL's little-endian DWORD.
                    challengeValue = int.from_bytes(trimbleChallenge, "little")

                    #First transformation, parameter 20.
                    value20 = challengeValue
                    divisor20 = 20 + 3

                    for _ in range(4 * divisor20):
                        value20 = (value20 * value20 + value20 % divisor20 + 0x0015A9CB) & 0xFFFFFFFF

                    #Second transformation, parameter 15.
                    value15 = challengeValue
                    divisor15 = 15 + 3

                    for _ in range(4 * divisor15):
                        value15 = (value15 * value15 + value15 % divisor15 + 0x0015A9CB) & 0xFFFFFFFF

                    answerValue = (value20 + 3 * value15 + 100) & 0xFFFFFFFF

                    answer = answerValue.to_bytes(4, "little")

                    #Escape reserved bytes inside the answer.
                    escapedAnswer = answer.replace(b'\xDB', b'\xDB\xDD')
                    escapedAnswer = escapedAnswer.replace(b'\xC0', b'\xDB\xDC')

                    responseToChallenge = (b'\x13\x0B\x00\x01\x02\xA1\x40' + escapedAnswer + b'\xC0')

                    log_data(responseToChallenge, logFile)

                    #Send response
                    trimbleSerial.write(responseToChallenge)

                    #Check if success or failure
                    success = b'\x12\x08\x00\x02\x01\xA1\x80\x00\xC0'
                    failure = b'\x12\x08\x00\x02\x01\xA1\x80\x63\xC0'

                    initializationStartTime = time.monotonic()
                    elapsedTime = None

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Response to Challenge timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Response to Challenge initialization timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        if trimbleSerial.in_waiting > 0:
                            #Read and buffer incoming data
                            trimbleRawData = trimbleSerial.read(trimbleSerial.in_waiting)
                            trimbleBuffer.extend(trimbleRawData)

                            #If success response found
                            if success in trimbleBuffer:
                                print("Response to Challenge successful.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 50
                                break

                            #If failure response found
                            elif failure in trimbleBuffer:
                                print("Response to Challenge failed.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                return False
                    
                
                #Initialization 1
                case 50:
                    print("Sending Initialization 1\n")
                    log_data(trimbleInitSequence1, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence1))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 1 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 1 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\x5B\x80\x00\xC0' in trimbleBuffer:
                                print("Initialization 1 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 60
                                break
                

                #Initialization 2
                case 60:
                    print("Sending Initialization 2\n")
                    log_data(trimbleInitSequence2, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence2))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 2 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 2 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x13\x75\x00\x02\x01\xAB\x80\x00' in trimbleBuffer:
                                print("Initialization 2 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 70
                                break
            

                #Initialization 3
                case 70:
                    print("Sending Initialization 3\n")
                    log_data(trimbleInitSequence3, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence3))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 3 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 3 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x13\x0F\x00\x02\x01\xA2\x80\x00' in trimbleBuffer:
                                print("Initialization 3 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 80
                                break
                

                #Initialization 4
                case 80:
                    print("Sending Initialization 4\n")
                    log_data(trimbleInitSequence4, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence4))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 4 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 4 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x10\x00\x02\x01\xBF\x80\x00' in trimbleBuffer:
                                print("Initialization 4 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 90
                                break
                

                #Initialization 5
                case 90:
                    print("Sending Initialization 5\n")
                    log_data(trimbleInitSequence5, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence5))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 5 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 5 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\xE4\x80\x00\xC0' in trimbleBuffer:
                                print("Initialization 5 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 100
                                break
                

                #Initialization 6
                case 100:
                    print("Sending Initialization 6\n")
                    log_data(trimbleInitSequence6, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence6))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 6 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 6 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x13\x5C\x01\x02\x01\xAD\x80\x00' in trimbleBuffer:
                                print("Initialization 6 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 110
                                break
                
                #Initialization 7: Get Horizontal Angle Adjustment
                case 110:
                    print("Sending Initialization 7\n")
                    log_data(trimbleInitSequence7, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence7))

                    responseHeader = b"\x12\x0C\x00\x02\x01\xC8\x81\x00"

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 7 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 7 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                        #Recalculate start after receiving data.
                        start = trimbleBuffer.find(responseHeader)

                        if start == -1:
                            continue

                        #C8 response is 13 bytes.
                        if start != -1 and len(trimbleBuffer) >= start + 13:
                            responsePacket = bytes(trimbleBuffer[start:start + 13])

                            if responsePacket[-1] != 0xC0:
                                continue

                            adjustmentBytes = responsePacket[8:12]

                            adjustmentInteger = int.from_bytes(adjustmentBytes, byteorder="little", signed=True)

                            currentAngles["horizontalAngleAdjustment"] = (adjustmentInteger * 360.0/ 400_000_000) % 360.0

                            print("Initialization 7 received.\n")
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            state = 120
                            break
                    

                #Initialization 8
                case 120:
                    print("Sending Initialization 8\n")
                    log_data(trimbleInitSequence8, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence8))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 8 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 8 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\x68\x80\x00\xC0' in trimbleBuffer:
                                print("Initialization 8 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 130
                                break


                #Initialization 9
                case 130:
                    print("Sending Initialization 9\n")
                    log_data(trimbleInitSequence9, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence9))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 9 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 9 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\xA7\x81\x00\xC0' in trimbleBuffer:
                                print("Initialization 9 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 140
                                break
                

                #Initialization 10
                case 140:
                    print("Sending Initialization 10\n")
                    log_data(trimbleInitSequence10, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence10))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 10 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 10 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\x99\x80\x00\xC0' in trimbleBuffer:
                                print("Initialization 10 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 150
                                break
                

                #Initialization 11: Get Correction Values
                case 150:
                    print("Sending Initialization 11\n")
                    log_data(trimbleInitSequence11, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence11))
                    trimbleSerial.flush()

                    responseHeader = (b"\x12\x1C\x00\x02\x01\xAE\x80\x00")

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 11 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 11 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                        start = trimbleBuffer.find(responseHeader)

                        if start == -1:
                            continue

                        decodedPayload = bytearray()
                        index = start + len(responseHeader)

                        while index < len(trimbleBuffer):
                            currentByte = trimbleBuffer[index]

                            #Actual packet end.
                            if currentByte == 0xC0:
                                break

                            #Escaped byte.
                            if currentByte == 0xDB:
                                if index + 1 >= len(trimbleBuffer):
                                    break

                                nextByte = trimbleBuffer[index + 1]

                                if nextByte == 0xDC:
                                    decodedPayload.append(0xC0)
                                    index += 2
                                    continue

                                if nextByte == 0xDD:
                                    decodedPayload.append(0xDB)
                                    index += 2
                                    continue

                            decodedPayload.append(currentByte)
                            index += 1

                        #Need exactly 20 payload bytes:
                        #5 correction values × 4 bytes each.
                        if len(decodedPayload) < 20:
                            continue

                        correctionPayload = decodedPayload[0:20]

                        opticalCollimationHAInteger = int.from_bytes(correctionPayload[0:4], byteorder="little", signed=True)
                        opticalCollimationVAInteger = int.from_bytes(correctionPayload[4:8], byteorder="little", signed=True)
                        trackerCollimationHAInteger = int.from_bytes(correctionPayload[8:12], byteorder="little", signed=True)
                        trackerCollimationVAInteger = int.from_bytes(correctionPayload[12:16], byteorder="little", signed=True)
                        trunnionAxisInteger = int.from_bytes(correctionPayload[16:20], byteorder="little", signed=True)

                        correctionValues["opticalCollimationHorizontalAngle"] = (opticalCollimationHAInteger * 360.0 / 4_000_000)
                        correctionValues["opticalCollimationVerticalAngle"] = (opticalCollimationVAInteger * 360.0 / 4_000_000)
                        correctionValues["trackerCollimationHorizontalAngle"] = (trackerCollimationHAInteger * 360.0 / 4_000_000)
                        correctionValues["trackerCollimationVerticalAngle"] = (trackerCollimationVAInteger * 360.0 / 4_000_000)
                        correctionValues["trunnionAxis"] = (trunnionAxisInteger * 360.0 / 4_000_000)

                        print("Initialization 11 received.\n")
                        log_data(trimbleBuffer, logFile)
                        #Clear buffer
                        trimbleBuffer.clear()
                        state = 160
                        break
                

                #Initialization 12: Get current power source
                case 160:
                    print("Sending Initialization 12\n")

                    log_data(trimbleInitSequence12, logFile)
                    trimbleSerial.write(bytes(trimbleInitSequence12))
                    trimbleSerial.flush()

                    responseHeader = b"\x12\x09\x00\x02\x01\x9F\x80\x00"

                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        elapsedTime = time.monotonic() - initializationStartTime
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        if remainingTime != previousCountdown:
                            print(f"Initialization 11 timeout in: " f"{remainingTime:02d} seconds", end="\n", flush=True)
                            previousCountdown = remainingTime

                        if elapsedTime > initializationTimeout:
                            print("Initialization 11 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            trimbleBuffer.clear()
                            return False

                        if trimbleSerial.in_waiting > 0:
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                        start = trimbleBuffer.find(responseHeader)

                        if start == -1:
                            continue

                        print("Initialization 11 received.\n")

                        log_data(trimbleBuffer, logFile)
                        trimbleBuffer.clear()
                        state = 170
                        break

                #Initialization 13
                case 170:
                    print("Sending Initialization 13\n")
                    log_data(trimbleInitSequence13, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence13))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 13 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 13 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x0C\x00\x02\x01\xBD\x80\x00\xE8\x03\x00\x00\xC0' in trimbleBuffer:
                                print("Initialization 13 received.\n")
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                state = 190
                                break
                

                #Initialization 14
                case 190:
                    print("Sending Initialization 14\n")
                    log_data(trimbleInitSequence14, logFile)
                    #Send data packet
                    trimbleSerial.write(bytes(trimbleInitSequence14))

                    #Set start time to current time
                    initializationStartTime = time.monotonic()
                    previousCountdown = 0

                    while True:
                        #Track the time taken
                        elapsedTime = time.monotonic() - initializationStartTime
                        #Don't allow tracked time to go below 0 seconds
                        remainingTime = max(0, initializationTimeout - int(elapsedTime))

                        #Print out the remaining time if it is a different value
                        if remainingTime != previousCountdown:
                            print(f"Initialization 14 timeout in: " f"{remainingTime:02d} seconds", end = "\n", flush = True)
                            previousCountdown = remainingTime

                        #If elapsed time has exceeded 10 seconds
                        if elapsedTime > initializationTimeout:
                            print("Initialization 14 timed out.\n")
                            log_data("Timeout waiting for expected response", logFile)
                            log_data(trimbleBuffer, logFile)
                            #Clear buffer
                            trimbleBuffer.clear()
                            return False
                        
                        #If there is data in the serial buffer
                        if trimbleSerial.in_waiting > 0:
                            #Read and append incoming data in array
                            trimbleBuffer.extend(trimbleSerial.read(trimbleSerial.in_waiting))

                            #Listen for acknowledgement
                            if b'\x12\x08\x00\x02\x01\x87\x80\x00\xC0' in trimbleBuffer:
                                print("Initialization 14 received.\n")
                                #Set variables that connection is established
                                status["trimbleConnection"] = True
                                log_data(trimbleBuffer, logFile)
                                #Clear buffer
                                trimbleBuffer.clear()
                                return True
                    
    #If user forcibly interrupts (Ctrl + C)
    except KeyboardInterrupt:
        #Clear buffer
        trimbleBuffer.clear()
        return False