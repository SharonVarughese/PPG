import PySimpleGUI as sg
import time
import threading
import serial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Initialize serial connection
ser = serial.Serial('COM4', 115200, timeout=1)  # Change COM port if necessary

# Global variables for data tracking
bpm_trend = []  # List to store BPM data over time
pulse_waveform = []  # Store pulse waveform data (sensor values)
x_axis = []  # X-axis to represent sample count or time
last_packet_time = time.time()  # Track time for packet loss detection

# Function to create a matplotlib figure for embedding
def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

# Function to read data from the ESP32
def read_from_esp():
    global last_packet_time
    buffer = []  # Buffer to store multi-line data
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                if data:
                    buffer.append(data)

                # Expecting 3 lines of data: raw pulse data, BPM, and adaptive threshold
                if len(buffer) == 3:
                    window.write_event_value('-DATA-', buffer.copy())
                    last_packet_time = time.time()  # Update packet arrival time
                    buffer.clear()

        except Exception as e:
            print(f"Error reading from ESP32: {e}")

# GUI layout
layout = [
    [sg.Column([
        [sg.Frame("Pulse Waveform", [[sg.Canvas(key='-CANVAS1-')]], size=(600, 400))],
        [sg.Frame("BPM Trend", [[sg.Canvas(key='-CANVAS2-')]], size=(600, 400))],
        [sg.Frame("Log Window", [[sg.Multiline(size=(80, 10), key='-LOG-', autoscroll=True)]], size=(600, 150))]
    ]),
    sg.Column([
        [sg.Frame("Alarm", [[sg.Text("BPM Normal", key='-ALARM-', font=('Helvetica', 20), size=(40, 1))]])],
        [sg.Text('Current BPM:', font=('Helvetica', 20)), sg.Text('', key='-BPM-', font=('Helvetica', 20))],
        [sg.Button('Exit', size=(10, 2), font=('Helvetica', 16))]
    ])]
]

# Create the window
window = sg.Window('Pulse Monitor', layout, finalize=True, resizable=True)  # Make the window resizable

# Create matplotlib figures for pulse waveform and BPM trend
fig1, ax1 = plt.subplots(figsize=(6, 4))  # Larger figure size
ax1.set_title("Pulse Waveform with Adaptive Threshold", fontsize=16)
ax1.set_ylabel("Sensor Value", fontsize=12)
ax1.set_xlabel("Time (seconds)", fontsize=12)

fig2, ax2 = plt.subplots(figsize=(6, 4))  # Larger figure size
ax2.set_title("BPM Trend Analysis", fontsize=16)
ax2.set_ylabel("BPM", fontsize=12)
ax2.set_xlabel("Time (seconds)", fontsize=12)

# Embed the figures in PySimpleGUI
fig_canvas_agg1 = draw_figure(window['-CANVAS1-'].TKCanvas, fig1)
fig_canvas_agg2 = draw_figure(window['-CANVAS2-'].TKCanvas, fig2)

# Start thread to read data from ESP32
threading.Thread(target=read_from_esp, daemon=True).start()

# Function to update the GUI with real-time data
def update_gui(pulse_values, bpm, adp_threshold):
    global bpm_trend, pulse_waveform, x_axis

    # Update BPM text display
    window['-BPM-'].update(f'{bpm:.1f}')

    # Generate X-axis values (either sample count or time in seconds)
    if not x_axis:
        x_axis = [i * 0.02 for i in range(len(pulse_values))]  # Time-based x-axis (20ms intervals)
    else:
        x_axis = x_axis[-len(pulse_values):]  # Ensure x_axis matches pulse_values length

    # Update the pulse waveform plot and add the adaptive threshold line
    pulse_waveform = pulse_values
    ax1.clear()
    ax1.plot(x_axis, pulse_waveform, label="Pulse Waveform")
    ax1.axhline(y=adp_threshold, color='red', linestyle='--', label="Adaptive Threshold")
    ax1.set_title("Pulse Waveform with Adaptive Threshold", fontsize=16)
    ax1.set_ylabel("Sensor Value", fontsize=12)
    ax1.set_xlabel("Time (seconds)", fontsize=12)
    ax1.legend(fontsize=10)  # Add a legend
    fig1.tight_layout()  # Adjust layout to prevent overlap
    fig_canvas_agg1.draw()

    # Update BPM trend plot
    bpm_trend.append(bpm)
    if len(bpm_trend) > 60:  # Keep last 60 seconds of data
        bpm_trend.pop(0)
    ax2.clear()
    ax2.plot(bpm_trend, label="BPM Trend")
    ax2.set_title("BPM Trend Analysis", fontsize=16)
    ax2.set_ylabel("BPM", fontsize=12)
    ax2.set_xlabel("Time (seconds)", fontsize=12)
    ax2.legend(fontsize=10)  # Add a legend
    fig2.tight_layout()  # Adjust layout to prevent overlap
    fig_canvas_agg2.draw()

    # Log event
    window['-LOG-'].print(f"{time.strftime('%a %b %d %H:%M:%S %Y')}: New Data Received, BPM: {bpm:.1f}")

    # Check for high/low BPM and display alarm
    if bpm < 60 or bpm > 100:  # Define thresholds
        window['-ALARM-'].update("Alarm: BPM Out of Range!", text_color='red')
    else:
        window['-ALARM-'].update("BPM Normal", text_color='green')

# Event loop for the GUI with enhanced error handling
while True:
    try:
        event, values = window.read(timeout=1000)  # Update every second
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        # Process incoming data from the ESP32
        if event == '-DATA-':
            data = values[event]
            if len(data) == 3:
                try:
                    # Clean sensor values string (removing stray characters)
                    sensor_values_str = data[0].replace("'", "").replace('"', '').strip()
                    sensor_values_list = sensor_values_str.split(',')

                    # Ensure we only process valid numeric strings
                    sensor_values = [float(v.strip()) for v in sensor_values_list if v.strip().replace('.', '', 1).isdigit()]

                    bpm_str = data[1].strip()
                    adp_threshold_str = data[2].strip()

                    # Convert BPM and adaptive threshold
                    bpm = float(bpm_str)
                    adp_threshold = float(adp_threshold_str)

                    # Update the GUI
                    update_gui(sensor_values, bpm, adp_threshold)

                except ValueError as e:
                    window['-LOG-'].print(f"Error processing data: {e}")
                    window['-ALARM-'].update("Error processing data", text_color='red')

        # Check for packet loss
        if time.time() - last_packet_time > 5:
            window['-ALARM-'].update("Alarm: No Packet Received for 5 Seconds!", text_color='orange')

    except Exception as e:
        print(f"Error in event loop: {e}")
        window['-LOG-'].print(f"Error: {e}")

window.close()
