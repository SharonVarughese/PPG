#include "BluetoothSerial.h"  // Include BluetoothSerial library

#define LED1_PIN 32  // LED1 will display the pulse when switched on
#define LED2_PIN 35
#define SWITCH_PIN 33
#define SENSOR_PIN 25

#define TICK_20MSEC 20000
#define TICK_1SEC 50
#define DEBOUNCE_DELAY 50  // 50ms debounce delay

BluetoothSerial SerialBT;  // Declare SerialBT object

bool led1Enabled = false;  // LED1 control flag
bool current_state = false;
bool old_state = false;
unsigned long last_transition;
unsigned long new_transition;
unsigned long pulse_period;
float heart_rate;
float emaValue = 1900;
int sensor_reading;
int adp_threshold = 0;
float alpha = 0.01;
static int buffer_indicator = 0;
char raw_pulse_data[251];

unsigned long last_tick_time;
uint16_t tick_1_sec = 0;

unsigned long lastDebounceTime = 0;
int lastSwitchState = LOW;
int switchState = LOW;

void checkSwitch() {
  int reading = digitalRead(SWITCH_PIN);

  // If the switch state changed (due to noise or pressing)
  if (reading != lastSwitchState) {
    lastDebounceTime = millis();  // reset the debounce timer
  }

  // Only toggle the LED if the new state has been stable for the debounce delay
  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    // Whatever the reading is at, it’s been there for longer than the debounce
    // delay, so take it as the actual current state:
    if (reading != switchState) {
      switchState = reading;

      // Only toggle the LED when the switch is pressed (HIGH state)
      if (switchState == HIGH) {
        led1Enabled = !led1Enabled;

        // If LED1 is turned off by the switch, make sure it remains off
        if (!led1Enabled) {
          digitalWrite(LED1_PIN, LOW);  // Turn off LED1
        }
      }
    }
  }

  lastSwitchState = reading;
}

void setup() {
  // initialize digital pins
  pinMode(LED1_PIN, OUTPUT);  // LED1 is controlled by the switch and pulse
  pinMode(LED2_PIN, OUTPUT);
  pinMode(SWITCH_PIN, INPUT_PULLDOWN);
  pinMode(SENSOR_PIN, INPUT);

  Serial.begin(115200);

  Serial.println("****************************");
  Serial.println("* ESP Bluetooth SLAVE DEMO *");
  Serial.println("****************************");
  Serial.println("\nNow run the host program...");

  // Initialize Bluetooth Serial
  SerialBT.begin("ESP32LW576");  // Bluetooth device name

  if (!SerialBT.begin("ESP32LW576")) {
    Serial.println("An error occurred initializing Bluetooth");
  } else {
    Serial.println("Bluetooth initialized");
  }
}

void loop() {
  // Call the checkSwitch function to control LED1 based on the switch state
  checkSwitch();

  // If the switch is on (led1Enabled = true), control LED1 to display the pulse
  if (led1Enabled && (micros() - last_tick_time) > TICK_20MSEC) {
    last_tick_time = micros();

    sensor_reading = analogRead(SENSOR_PIN);
    sprintf(raw_pulse_data + buffer_indicator*5, "%4d,", sensor_reading);
    emaValue = (alpha * sensor_reading) + ((1 - alpha) * emaValue);
    adp_threshold = emaValue + 45;
    current_state = (sensor_reading > adp_threshold);

    if (current_state != old_state && current_state == true) {
      new_transition = millis();
      pulse_period = new_transition - last_transition;
      last_transition = new_transition;
      heart_rate = 60000.0 / (float)pulse_period;
    }

    // Display the pulse by blinking LED1 according to the sensor state
    digitalWrite(LED1_PIN, current_state ? HIGH : LOW);
    //Serial.printf("%d,%d\n",sensor_reading,adp_threshold);

    old_state = current_state;
    tick_1_sec++;
  }

  // If the switch is off (led1Enabled = false), LED1 stays off
  if (!led1Enabled && (micros() - last_tick_time) > TICK_20MSEC) {
    digitalWrite(LED1_PIN, LOW);  // Ensure LED1 is off if disabled
        last_tick_time = micros();

    sensor_reading = analogRead(SENSOR_PIN);
    sprintf(raw_pulse_data + buffer_indicator*5, "%4d,", sensor_reading);
    emaValue = (alpha * sensor_reading) + ((1 - alpha) * emaValue);
    adp_threshold = emaValue + 45;
    current_state = (sensor_reading > adp_threshold);

    if (current_state != old_state && current_state == true) {
      new_transition = millis();
      pulse_period = new_transition - last_transition;
      last_transition = new_transition;
      heart_rate = 60000.0 / (float)pulse_period;
    }
    old_state = current_state;
    tick_1_sec++;
    //Serial.printf("%d,%d\n",sensor_reading,adp_threshold);
  }

  if (tick_1_sec >= TICK_1SEC) {
    tick_1_sec = 0;
    sprintf(raw_pulse_data + 249, "\n");
    SerialBT.printf(raw_pulse_data);
    SerialBT.printf("%f", heart_rate);
    SerialBT.printf("%d\n", adp_threshold);
  }
}
