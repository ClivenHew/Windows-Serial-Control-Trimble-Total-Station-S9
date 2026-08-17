/*
  Arduino 1 (MKR WiFi 1010) - SDK <-> Arduino 2 relay
  -----------------------------------------------------
  Serial   (USB CDC)   -> connects to the SDK laptop (was COM9 in SDKMain.py)
  Serial1  (hardware UART, pins 13/14) -> connects to Arduino 2

  Wiring (MKR WiFi 1010 pinout):
    Arduino1 pin 13 (RX1) <---- Arduino2 pin 14 (TX1)
    Arduino1 pin 14 (TX1) ----> Arduino2 pin 13 (RX1)
    Arduino1 GND          ----- Arduino2 GND        (common ground is required)

  MKR boards run on 3.3V logic. If Arduino2 is also an MKR/SAMD board this is
  fine directly. If Arduino2 is a 5V board (Uno/Nano/Mega), you MUST use a
  logic level shifter on the RX/TX lines - 5V on an MKR's RX pin can damage it.
*/

const long BAUD_RATE = 9600;  // Must match Arduino2's Serial1 speed and the SDK's port speed

void setup() {
  Serial.begin(BAUD_RATE);   // USB link to the SDK
  Serial1.begin(BAUD_RATE);  // Hardware UART link to Arduino 2
}

void loop() {
  // SDK -> Arduino 1 -> Arduino 2
  while (Serial.available()) {
    Serial1.write(Serial.read());
  }

  // Arduino 2 -> Arduino 1 -> SDK
  while (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}
