#include <Arduino.h>

const uint8_t LED_PIN = LED_BUILTIN;
const unsigned long BLINK_INTERVAL_MS = 500;
String inputLine;
bool blinking = false;
bool ledOn = false;
unsigned long lastToggle = 0;

void setLed(bool on) {
  ledOn = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();
  if (command == "LED ON") {
    blinking = false;
    setLed(true);
    Serial.println("OK LED ON");
  } else if (command == "LED OFF") {
    blinking = false;
    setLed(false);
    Serial.println("OK LED OFF");
  } else if (command == "LED BLINK") {
    blinking = true;
    lastToggle = millis();
    setLed(true);
    Serial.println("OK LED BLINK");
  } else if (command == "STATUS") {
    Serial.print("OK STATUS ");
    Serial.println(blinking ? "BLINK" : (ledOn ? "ON" : "OFF"));
  } else {
    Serial.println("ERR UNKNOWN COMMAND");
  }
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  setLed(false);
  Serial.begin(115200);
  inputLine.reserve(64);
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      handleCommand(inputLine);
      inputLine = "";
    } else if (c != '\r') {
      if (inputLine.length() < 63) inputLine += c;
      else inputLine = "";
    }
  }
  if (blinking && millis() - lastToggle >= BLINK_INTERVAL_MS) {
    lastToggle = millis();
    setLed(!ledOn);
  }
}
