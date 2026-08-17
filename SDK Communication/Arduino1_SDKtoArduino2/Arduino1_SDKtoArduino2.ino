/*
  Arduino 1 (MKR WiFi 1010) - SDK <-> Arduino 2 relay
  -----------------------------------------------------
  Serial   (USB CDC)   -> connects to the SDK laptop (COM13 on this setup)
  Serial1  (hardware UART, pins 13/14) -> connects to Arduino 2

  Wiring (MKR WiFi 1010 pinout):
    Arduino1 pin 13 (RX1) <---- Arduino2 pin 14 (TX1)
    Arduino1 pin 14 (TX1) ----> Arduino2 pin 13 (RX1)
    Arduino1 GND          ----- Arduino2 GND        (common ground is required)

  MKR boards run on 3.3V logic. If Arduino2 is also an MKR/SAMD board this is
  fine directly. If Arduino2 is a 5V board (Uno/Nano/Mega), you MUST use a
  logic level shifter on the RX/TX lines - 5V on an MKR's RX pin can damage it.
*/

const unsigned long USB_BAUD_RATE = 115200;  // Matches the TPSDK connection setting
const unsigned long UART_BAUD_RATE = 9600;   // Must match Arduino 2 Serial1
const byte MAX_BYTES_PER_PASS = 32;

void setup() {
  Serial.begin(USB_BAUD_RATE);   // USB CDC link to the SDK
  Serial1.begin(UART_BAUD_RATE); // Hardware UART link to Arduino 2
}

void loop() {
  // Limit each pass so traffic in one direction cannot starve the response.
  for (byte count = 0; count < MAX_BYTES_PER_PASS && Serial.available() > 0; count++) {
    const int value = Serial.read();
    if (value >= 0) {
      Serial1.write((byte)value);  // SDK -> Arduino 1 -> Arduino 2
    }
  }

  for (byte count = 0; count < MAX_BYTES_PER_PASS && Serial1.available() > 0; count++) {
    const int value = Serial1.read();
    if (value >= 0) {
      Serial.write((byte)value);   // Arduino 2 -> Arduino 1 -> SDK
    }
  }
}
