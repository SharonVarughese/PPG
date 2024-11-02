import PySimpleGUI as sg
import serial
import time
from datetime import datetime
import numpy as np
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Initialize packet sequence number and serial communication
packet_sequence_number = 0
last_sequence_number = -1

# Function to establish or reconnect the serial connection
def connect_serial(port, baud_rate, timeout=100):
    ser = None
    while not ser:
        try:
            ser = serial.Serial(port, baud_rate, timeout=timeout)
            if ser.is_open:
                sg.popup_auto_close("Connection established with microcontroller.")
                return ser
        except serial.SerialException:
            sg.popup_auto_close("Attempting to reconnect to the microcontroller...")
            time.sleep(2)  # Wait before retrying

# Initialize serial connection (adjust COM port and baud rate)
ser = connect_serial('COM5', 115200)

# Function to handle reconnection logic when connection is lost
def check_connection(ser, port, baud_rate):
    try:
        if not ser.is_open:
            ser.close()
            raise serial.SerialException("Port not open")
    except (serial.SerialException, OSError):
        sg.popup_auto_close("Connection lost. Attempting to reconnect...")
        ser = connect_serial(port, baud_rate)
    return ser

# Function to apply Butterworth low-pass filter
def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

# Sampling frequency and cutoff frequency for the filter
fs = 50  # Hz
cutoff = 2.5  # Hz

# Function to draw the figure on the canvas
def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

# Create the initial Matplotlib figures
def create_plots():
    fig1, ax1 = plt.subplots(figsize=(15, 12))  # PPG signal plot
    ax1.set_xlabel("Sample Points")
    ax1.set_ylabel("Pulse Data")

    fig2, ax2 = plt.subplots(figsize=(15, 12))  # Heart rate plot
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Heart Rate (BPM)")

    return (fig1, ax1), (fig2, ax2)

# Create the GUI layout
layout = [
    [sg.Text("Pulse Rate: "), sg.Text("0", key='-BPM-', font=("Helvetica", 50), size=(10, 1))],
    [sg.Canvas(key='-CANVAS-', size=(1200, 800)),
     sg.Column([
         [sg.Canvas(key='-ALARM-', size=(300, 150))],
         [sg.Text("High Pulse Threshold"), sg.Slider(range=(50, 150), orientation='h', size=(40, 20), default_value=100, key='-HIGH-THRESH-'), sg.InputText('100', size=(5, 1), key='-HIGH-INPUT-')],
         [sg.Text("Low Pulse Threshold"), sg.Slider(range=(50, 150), orientation='h', size=(40, 20), default_value=60, key='-LOW-THRESH-'), sg.InputText('60', size=(5, 1), key='-LOW-INPUT-')],
         [sg.Button("Info"), sg.Button("PPG signal"), sg.Button("Heart rate (bpm)")]
     ])],
    [sg.Multiline(size=(100, 10), key='-LOG-', disabled=True, font=("Helvetica", 16))],
    [sg.Button("Exit", font=("Helvetica", 16))]
]

# Create the window
window = sg.Window("PPG Monitor", layout, finalize=True, resizable=True)

# Draw the initial plots
(fig1, ax1), (fig2, ax2) = create_plots()
canvas = draw_figure(window['-CANVAS-'].TKCanvas, fig1)

# Draw the initial alarm state
alarm_canvas = window['-ALARM-'].TKCanvas
pulse_data = []
filtered_pulse_data = []
heart_rate_data = []
time_data = []
t = 0
last_update_time = time.time()
last_packet_time = time.time()
last_log_time = time.time()
heart_rate = None
adp_threshold = None

# Main loop
while True:
    event, values = window.read(timeout=100)

    if event == sg.WIN_CLOSED or event == 'Exit':
        break

    # Check and handle reconnection
    ser = check_connection(ser, 'COM5', 115200)

    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            last_packet_time = time.time()

            if line:
                if line.startswith("R,"):
                    pulse_values = [int(val.strip()) for val in line[2:].split(",")]
                    pulse_data.extend(pulse_values)
                    filtered_pulse_data = butter_lowpass_filter(pulse_data, cutoff, fs)

                    if len(pulse_data) > 100:
                        pulse_data = pulse_data[-100:]
                        filtered_pulse_data = filtered_pulse_data[-100:]

                    ax1.clear()
                    ax1.plot(pulse_data, label="Raw Pulse Data", alpha=0.5)
                    ax1.plot(filtered_pulse_data, label="Filtered Pulse Data", linestyle='--', color='blue')
                    if adp_threshold is not None:
                        ax1.axhline(y=adp_threshold, color='r', linestyle='--', label="Threshold")
                    ax1.legend()
                    canvas.draw()

                elif line.startswith("H,"):
                    heart_rate = float(line[2:])
                    if heart_rate <= 120:
                        heart_rate_data.append(heart_rate)
                        window['-BPM-'].update(f"{heart_rate:.1f} BPM")

                    if len(time_data) > 10:
                        time_data = time_data[-10:]
                        heart_rate_data = heart_rate_data[-10:]

                    ax2.clear()
                    ax2.plot(time_data, heart_rate_data, label="Heart Rate")
                    ax2.legend()
                    canvas.draw()

                elif line.startswith("T,"):
                    adp_threshold = int(line[2:])

                elif line.startswith("S,"):
                    packet_sequence_number = int(line[2:])
                    if packet_sequence_number != last_sequence_number + 1:
                        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet out of order! Order: {packet_sequence_number}")
                    else:
                        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet received. Order: {packet_sequence_number}")
                    last_sequence_number = packet_sequence_number

                t += 1
                time_data.append(t)

                current_time = time.time()
                if current_time - last_log_time >= 0.8:
                    if heart_rate is not None:
                        timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                        if heart_rate > high_threshold:
                            log_message = f"{timestamp}: Pulse High"
                            draw_alarm(alarm_canvas, "high")
                        elif heart_rate < low_threshold:
                            log_message = f"{timestamp}: Pulse Low"
                            draw_alarm(alarm_canvas, "low")
                        else:
                            log_message = f"{timestamp}: Pulse Normal"
                            draw_alarm(alarm_canvas, "normal")

                        window['-LOG-'].print(log_message)
                        last_log_time = current_time

        except ValueError:
            pass

    elif time.time() - last_packet_time > 5:
        if time.time() - last_log_time > 1:
            window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet not received for 5 seconds!")
            last_log_time = time.time()

    window.refresh()

# Close serial and GUI on exit
ser.close()
window.close()
