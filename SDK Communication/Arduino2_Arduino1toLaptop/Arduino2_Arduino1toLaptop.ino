/*
  Arduino 2 (MKR WiFi 1010) - Arduino 1 <-> Laptop relay
  ---------------------------------------------------------
  Serial   (USB CDC)   -> connects to the Laptop (COM14 in LaptopBridge.py)
  Serial1  (hardware UART, pins 13/14) -> connects to Arduino 1

  Wiring (MKR WiFi 1010 pinout):
    Arduino2 pin 13 (RX1) <---- Arduino1 pin 14 (TX1)
    Arduino2 pin 14 (TX1) ----> Arduino1 pin 13 (RX1)
    Arduino2 GND          ----- Arduino1 GND        (common ground is required)

  MKR boards run on 3.3V logic. If Arduino1 is also an MKR/SAMD board this is
  fine directly. If Arduino1 is a 5V board (Uno/Nano/Mega), you MUST use a
  logic level shifter on the RX/TX lines - 5V on an MKR's RX pin can damage it.
*/

const long BAUD_RATE = 9600;  // Must match Arduino1's Serial1 speed and the Laptop's port speed (COM14)

void setup() {
  Serial.begin(BAUD_RATE);   // USB link to the Laptop
  Serial1.begin(BAUD_RATE);  // Hardware UART link to Arduino 1
}

void loop() {
  // Arduino 1 -> Arduino 2 -> Laptop
  while (Serial1.available()) {
    Serial.write(Serial1.read());
  }

  // Laptop -> Arduino 2 -> Arduino 1
  while (Serial.available()) {
    Serial1.write(Serial.read());
  }
}
