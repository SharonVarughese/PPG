
#include "BluetoothSerial.h"

#define LED1_PIN 32
#define LED2_PIN 35
#define SWITCH_PIN 33
#define SENSOR_PIN 25
#define Button_pressed_threshold 10
#define Button_held_threshold 50
#define TICK_20MSEC 20000

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
unsigned long last_transition = 0;
unsigned long new_transition;
unsigned long pulse_period;

unsigned long last_tick_time;
char raw_pulse_data[250];
char empty_buffer[250];
static int buffer_indicator = 0;

int THRESHOLD = 1900;
int adp_threshold = 0;
float alpha = 0.1;
float emaValue = 1900;

// the setup function runs once when you press reset or power the board
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

char mask;

void loop() {
    
    //Switch reading module
    if (digitalRead(SWITCH_PIN) != switch_state) { 
    switchCount++;
    // When the button is pressed
    if (switchCount >= Button_pressed_threshold && switchCount < Button_held_threshold) { 
      switchCount = 0;
      switch_state = !switch_state; 

    }
    // When the button is pressed and held
      else if (switchCount >= Button_held_threshold) {
        
      }
      else {
    if (switchCount > 1) {
      switchCount--;
    }
      }
    }

  // pulse reading every 20ms
  for (buffer_indicator, bufferindicator++, buffer_indicator > 50){
    if ((micros() - last_tick_time) > TICK_20MSEC) {
    last_tick_time = micros(); 

    sensor_reading = analogRead(SENSOR_PIN);
    raw_pulse_data[]
    // reset the indicator when it is over limitation
    if (buffer_indicator > 50) {
      buffer_indicator = 1;

    }

  emaValue = (alpha * sensor_reading) + ((1 - alpha) * emaValue);
  adp_threshold = emaValue + 20;
  
    
    current_state = (sensor_reading > adp_threshold);

    if (current_state != old_state && current_state == true) {
      new_transition = millis();
      pulse_period = new_transition - last_transition;
      last_transition = new_transition;

    // Calculate heart rate in BPM
      //heart_rate = 60000.0 / (float)pulse_period;
      }

  old_state = current_state;
  }
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
