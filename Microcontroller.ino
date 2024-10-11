#include "BluetoothSerial.h"

#define LED1_PIN 32
#define LED2_PIN 35
#define SWITCH_PIN 33
#define SENSOR_PIN 25
#define Button_pressed_threshold 10
#define Button_held_threshold 50
#define TICK_20MSEC 20000
#define SAMPLING_PERIOD 20        // Sampling period for sensor and button (20 ms)
#define ADAPTIVE_THRESHOLD_WINDOW 50 // Number of samples to calculate the adaptive threshold

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

BluetoothSerial SerialBT;
String btName = "ESP32_PPG";

bool switch_state = false;
unsigned long last_sample_time = 0;
unsigned long last_bpm_time = 0;
unsigned long last_transition = 0;
unsigned long pulse_period = 0;

int sensor_value = 0;
float adaptive_threshold = 0;
float pulse_data[ADAPTIVE_THRESHOLD_WINDOW] = {0}; // Buffer for pulse waveform data
float ema_value = 1900;
float alpha = 0.1;
bool recording_data = false;

int button_click_count = 0;
unsigned long last_click_time = 0;
const unsigned long click_timeout = 500; // Time window for multiple clicks (500 ms)
int debounce_counter = 0;
int last_button_state = LOW;

void setup() {
    // Initialize serial and Bluetooth
    Serial.begin(115200);
    SerialBT.begin(btName); // Initialize Bluetooth serial communication
    Serial.println("Bluetooth initialized");
    Serial.println(btName);

    // Initialize digital pins
    pinMode(LED1_PIN, OUTPUT);
    pinMode(LED2_PIN, OUTPUT);
    pinMode(SWITCH_PIN, INPUT_PULLUP);  // Internal pull-up for button
    pinMode(SENSOR_PIN, INPUT);

    initializePulseDataBuffer();
    digitalWrite(LED1_PIN, LOW);
}

// Function to initialize the pulse data buffer
void initializePulseDataBuffer() {
    for (int i = 0; i < ADAPTIVE_THRESHOLD_WINDOW; i++) {
        pulse_data[i] = 0;
    }
}

void loop() {
    unsigned long current_time = millis();

    // Sample the sensor and button every 20 ms
    if (current_time - last_sample_time >= SAMPLING_PERIOD) {
        last_sample_time = current_time;
        sensor_value = analogRead(SENSOR_PIN);
        updateAdaptiveThreshold();
        handlePulseDetection();
        handleButtonClick();
    }

    // Calculate BPM every second
    if (current_time - last_bpm_time >= 1000) {
        last_bpm_time = current_time;
        calculateBPM();
        sendBluetoothData();
        printPulseWaveform();
    }
}

// Function to update the adaptive threshold value
void updateAdaptiveThreshold() {
    float sum = 0;
    for (int i = 0; i < ADAPTIVE_THRESHOLD_WINDOW - 1; i++) {
        pulse_data[i] = pulse_data[i + 1];
        sum += pulse_data[i];
    }
    pulse_data[ADAPTIVE_THRESHOLD_WINDOW - 1] = sensor_value;
    sum += sensor_value;
    adaptive_threshold = sum / ADAPTIVE_THRESHOLD_WINDOW; // Calculate the new adaptive threshold
}

// Function to handle pulse detection using the adaptive threshold
void handlePulseDetection() {
    if (sensor_value > adaptive_threshold) {
        digitalWrite(LED1_PIN, HIGH); // Turn on LED if pulse is detected
    } else {
        digitalWrite(LED1_PIN, LOW);  // Turn off LED if no pulse is detected
    }
}

// Function to calculate BPM based on pulse detection
void calculateBPM() {
    static int pulse_count = 0;
    static unsigned long start_time = millis();

    if (digitalRead(LED1_PIN) == HIGH) {
        pulse_count++;
    }

    unsigned long elapsed_time = millis() - start_time;
    if (elapsed_time >= 60000) { // Calculate BPM every 60 seconds
        float bpm = (pulse_count / (elapsed_time / 60000.0));
        pulse_count = 0;
        start_time = millis();
        Serial.printf("BPM: %0.1f\n", bpm);
    }
}

// Function to handle button clicks for different functions
void handleButtonClick() {
    int button_state = digitalRead(SWITCH_PIN);

    if (button_state != last_button_state) {
        if (button_state == LOW) { // Button pressed
            debounce_counter++;
            if (debounce_counter >= 5) { // Debounce logic
                button_click_count++;
                last_click_time = millis();
                debounce_counter = 0;
            }
        }
    }

    last_button_state = button_state;

    if (millis() - last_click_time > click_timeout && button_click_count > 0) {
        if (button_click_count == 1) {
            toggleSystemPower();
        } else if (button_click_count == 2) {
            restartSystem();
        } else if (button_click_count == 3) {
            toggleDataRecording();
        }
        button_click_count = 0; // Reset click count
    }
}

// Function to toggle system power
void toggleSystemPower() {
    Serial.println("System Power Toggled");
}

// Function to restart the system
void restartSystem() {
    Serial.println("System Restarted");
}

// Function to toggle data recording
void toggleDataRecording() {
    recording_data = !recording_data;
    digitalWrite(LED1_PIN, recording_data ? HIGH : LOW);
    Serial.println(recording_data ? "Data Recording Started" : "Data Recording Stopped");
}

// Function to send data over Bluetooth
void sendBluetoothData() {
    SerialBT.printf("BPM: %0.1f, Sensor Value: %d\n", bpm, sensor_value);
}

// Function to print pulse waveform data for the Serial Plotter
void printPulseWaveform() {
    Serial.printf("Sensor Value: %d, Adaptive Threshold: %0.1f\n", sensor_value, adaptive_threshold);
}
