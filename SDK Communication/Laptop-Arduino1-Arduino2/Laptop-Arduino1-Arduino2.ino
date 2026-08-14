const unsigned long USB_BAUD  = 9600;
const unsigned long LINK_BAUD = 9600;

void setup()
{
  // USB connection to the PC
  Serial.begin(USB_BAUD);

  // Physical RX/TX pins
  Serial1.begin(LINK_BAUD);
}

void loop()
{
  // Forward bytes received from the laptop to the other MKR
  while (Serial.available() > 0)
  {
    byte incomingByte = Serial.read();
    Serial1.write(incomingByte);
  }

  // Forward bytes received from the other MKR to the laptop
  while (Serial1.available() > 0)
  {
    byte incomingByte = Serial1.read();
    Serial.write(incomingByte);
  }
}
