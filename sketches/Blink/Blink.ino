
const int LED_PIN = 13;

void setup() {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    Serial.begin(9600);

}

void loop() {
   if (Serial.available() > 0) {
      char command = Serial.read();

      if (command == '1') {   
         digitalWrite(LED_PIN, HIGH);
         Serial.println("LED ON");
      }
      
      if (command == '0') {
         digitalWrite(LED_PIN, LOW);
         Serial.println("LED OFF");

      }
   }
}
