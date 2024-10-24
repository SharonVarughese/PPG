
#include "BluetoothSerial.h"
#include "switch.h"

#define LED1_PIN 32
#define LED2_PIN 35
#define SWITCH_PIN 33
#define SENSOR_PIN 25

#define TICK_20MSEC 20000
#define TICK_1SEC 50
#define DEBOUNCE_CNT 5
#define DEBOUNCE_DELAY 50 
Switch switch_1(1, DEBOUNCE_CNT);

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

#include "BluetoothSerial.h"
#include <Esp.h>
//#include "btSupport.h"

String btName = "ESP32LW576";
bool connected;

BluetoothSerial SerialBT;

uint8_t count = 1;
uint8_t switchCount = 0;
bool switch_state = false;
uint16_t sensor_reading;
bool old_state = false;
bool current_state = false;
bool led1Enabled = false;
unsigned long last_transition;
unsigned long new_transition;
unsigned long pulse_period;

unsigned long last_tick_time;
uint16_t tick_1_sec = 0;  
char raw_pulse_data[251];
int buffer_indicator_2 = 1;
static int buffer_indicator = 0;

int THRESHOLD = 1900;
int adp_threshold = 0;
float alpha = 0.01;
float emaValue = 1900;
float heart_rate;

unsigned long lastDebounceTime = 0;
int lastSwitchState = LOW;
int switchState = LOW;
// the setup function runs once when you press reset or power the board
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
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(SWITCH_PIN, INPUT_PULLDOWN);
  pinMode(SENSOR_PIN, INPUT);
  
  Serial.begin(115200);

  Serial.println("****************************");
  Serial.println("* ESP Bluetooth SLAVE DEMO *");
  Serial.println("****************************");
  Serial.println("\nNow run the host program...");

  SerialBT.register_callback(btCallback);

  SerialBT.begin(btName); //Bluetooth device name

  if (!SerialBT.begin(btName))
  {
    Serial.println("An error occurred initializing Bluetooth");
  }
  else
  {
    Serial.println("Bluetooth initialized");
    Serial.println(btName);
  }
}
char buf[128];
unsigned char i;
char j = '0';
//unsigned int disconnectCount = 0;

void loop() {
    checkSwitch();

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
    if (buffer_indicator >= 50){
      buffer_indicator = 0;
    }
    tick_1_sec = 0;
    sprintf(raw_pulse_data + 249, "\n");
    Serial.printf(raw_pulse_data);
    Serial.printf("%f\n", heart_rate);
    Serial.printf("%d\n", adp_threshold);
  }
}

int openEvt = 0;

void btCallback(esp_spp_cb_event_t event, esp_spp_cb_param_t *param)
//
// This function displays SPP events when they occur. This provides 
// information on what is hapening on the bluetooth link.
//
//
{
  if (event == ESP_SPP_SRV_OPEN_EVT) {
    char buf[50];
    openEvt++;
    sprintf(buf, "Client Connected:%d", openEvt);
    Serial.println(buf);
    Serial.print("  Address = ");

    for (int i = 0; i < 6; i++)
    {
      sprintf(&(buf[i * 3]), "%02X:", param->srv_open.rem_bda[i]);
    }
    buf[17] = 0;
    Serial.println(buf);
  }


  if (event == ESP_SPP_INIT_EVT)
    Serial.println("ESP_SPP_INIT_EVT");
  else if (event == ESP_SPP_UNINIT_EVT)
    Serial.println("ESP_SPP_INIT_EVT");
  else if (event == ESP_SPP_DISCOVERY_COMP_EVT )
    Serial.println("ESP_SPP_DISCOVERY_COMP_EVT");
  else if (event == ESP_SPP_OPEN_EVT )
    Serial.println("ESP_SPP_OPEN_EVT");
  else if (event == ESP_SPP_CLOSE_EVT )
    Serial.println("ESP_SPP_CLOSE_EVT");
  else if (event == ESP_SPP_START_EVT )
    Serial.println("ESP_SPP_START_EVT");
  else if (event == ESP_SPP_CL_INIT_EVT )
    Serial.println("ESP_SPP_CL_INIT_EVT");
  else if (event == ESP_SPP_DATA_IND_EVT )
    Serial.println("ESP_SPP_DATA_IND_EVT");
  else if (event == ESP_SPP_CONG_EVT )
    Serial.println("ESP_SPP_CONG_EVT");
  else if (event == ESP_SPP_WRITE_EVT )
    Serial.println("ESP_SPP_WRITE_EVT");
  else if (event == ESP_SPP_SRV_OPEN_EVT )
    Serial.println("ESP_SPP_SRV_OPEN_EVT");
  else if (event == ESP_SPP_SRV_STOP_EVT )
    Serial.println("ESP_SPP_SRV_STOP_EVT");
  else
  {
    Serial.print("EV: ");
    Serial.println(event);
  };
}
