const unsigned long USB_BAUD = 9600;
const unsigned long LINK_BAUD = 9600;

void setup()
{
  // USB connection to the laptop on COM20
  Serial.begin(USB_BAUD);

  // Physical RX and TX connection to Arduino 1
  Serial1.begin(LINK_BAUD);
}

void loop()
{
  // Arduino 1 -> Arduino 2 -> laptop COM20
  while (Serial1.available() > 0)
  {
    Serial.write(Serial1.read());
  }

  // Laptop COM20 -> Arduino 2 -> Arduino 1
  while (Serial.available() > 0)
  {
    Serial1.write(Serial.read());
  }
}
