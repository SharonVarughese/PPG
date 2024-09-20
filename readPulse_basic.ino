#include "Switch.h"  
#define BAUD 115200
#define SENSOR_PIN 25
#define PULSE_ID 1
#define PULSE_CNT 1
#define THRESHOLD 1940
uint16_t sensor_reading;

Switch pulse(PULSE_ID, PULSE_CNT);
unsigned long last_transition = 0;
float heart_rate = 0;
void setup() {
  Serial.begin(BAUD);
  pinMode(SENSOR_PIN, INPUT);
}


void loop() {
  
  sensor_reading = analogRead(SENSOR_PIN);

  Serial.print(sensor_reading);
  Serial.print(", ");
  Serial.print(THRESHOLD);
  Serial.print("\n");



  //Serial.printf("%u\n",sensor_reading);
  bool thresholdExceeded = (sensor_reading > THRESHOLD);
  pulse.update(thresholdExceeded);

  if (pulse.changed() && pulse.state()) {
    unsigned long current_time = millis();
    uint16_t pulse_period = current_time - last_transition;
    last_transition = current_time;
    Serial.printf("Pulse period: %u ms\n", pulse_period);
  }
  delay(20);
}
