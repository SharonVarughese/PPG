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

# Initialize serial connection (adjust COM port and baud rate)
ser = serial.Serial('COM5', 115200, timeout=100)  # Replace 'COM5' with your port

# Function to apply Butterworth low-pass filter
def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

fs = 50  # Sampling frequency in Hz (adjust as needed)
cutoff = 2.5  # Desired cutoff frequency in Hz

# Add this text at the beginning of your code
info_text = (
    "A Photoplethysmography (PPG) sensor measures blood volume changes in \n\n"
    "the microvascular bed of tissue. It uses light to detect variations in \n\n"
    "blood flow, providing real-time information about heart rate and \n\n"
    "vascular health.\n\n"
    "\n\n"
    "The Butterworth low-pass filter is used to eliminate high-frequency noise \n\n"
    "from PPG signals while preserving the desired low-frequency components. \n\n"
    "With a smooth frequency response, it effectively attenuates frequencies \n\n"
    "above a specified cutoff (e.g., 2.5 Hz), ensuring cleaner signal processing \n\n"
    "for accurate heart rate detection."
)

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

# Function to draw the alarm LEDs
def draw_alarm(canvas, state):
    canvas.delete("all")
    colors = {"high": "red", "normal": "green", "low": "blue"}
    positions = {"high": (50, 50), "normal": (150, 50), "low": (250, 50)}
    for key, pos in positions.items():
        color = colors[key] if state == key else "grey"
        canvas.create_oval(pos[0] - 20, pos[1] - 20, pos[0] + 20, pos[1] + 20, fill=color)
        canvas.create_text(pos[0], pos[1] + 30, text=key.capitalize(), font=("Helvetica", 12))
    canvas.create_text(150, 10, text="ALARMS", font=("Helvetica", 16))

# Layout for the GUI
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
draw_alarm(alarm_canvas, "normal")

pulse_data = []
filtered_pulse_data = []
heart_rate_data = []
time_data = []
t = 0

# Set update frequency to 1 second
last_update_time = time.time()
last_packet_time = time.time()
last_log_time = time.time()  # Initialize the last log update time

# Initialize heart_rate to None before the main loop
heart_rate = None
adp_threshold = None  # Initialize adp_threshold to None

# Main loop
while True:
    event, values = window.read(timeout=100)

    if event == sg.WIN_CLOSED or event == 'Exit':
        break

    # Handle graph switching buttons
    if event == 'PPG signal':
        canvas.get_tk_widget().pack_forget()
        canvas = draw_figure(window['-CANVAS-'].TKCanvas, fig1)
        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Display PPG signal")
    elif event == 'Heart rate (bpm)':
        canvas.get_tk_widget().pack_forget()
        canvas = draw_figure(window['-CANVAS-'].TKCanvas, fig2)
        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Display heart rate (bpm)")
    elif event == 'Info':
        canvas.get_tk_widget().pack_forget()
        window['-CANVAS-'].TKCanvas.create_rectangle(0, 0, window['-CANVAS-'].TKCanvas.winfo_width(), window['-CANVAS-'].TKCanvas.winfo_height(), fill="white")
        window['-CANVAS-'].TKCanvas.create_text(
            window['-CANVAS-'].TKCanvas.winfo_width() // 2,
            window['-CANVAS-'].TKCanvas.winfo_height() // 2,
            text=info_text,
            fill="black",
            font=("Helvetica", 20),
            anchor='center',
            justify='left'
        )
        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Display Info")

    # Update threshold values from input fields and handle empty input gracefully
    try:
        high_threshold = int(values['-HIGH-INPUT-']) if values['-HIGH-INPUT-'] else int(values['-HIGH-THRESH-'])
        low_threshold = int(values['-LOW-INPUT-']) if values['-LOW-INPUT-'] else int(values['-LOW-THRESH-'])
        window['-HIGH-THRESH-'].update(high_threshold)
        window['-LOW-THRESH-'].update(low_threshold)
    except ValueError:
        pass

    # Read data from serial
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()  # Read serial data
        last_packet_time = time.time()  # Update last packet time

        # Process the received line
        if line:
            try:
                if line.startswith("R,"):  # Raw pulse data
                    pulse_values = [int(val.strip()) for val in line[2:].split(",")]
                    pulse_data.extend(pulse_values)

                    # Apply low-pass filter
                    filtered_pulse_data = butter_lowpass_filter(pulse_data, cutoff, fs)

                    # Keep the pulse data at a manageable size (last 250 samples)
                    if len(pulse_data) > 100:
                        pulse_data = pulse_data[-100:]
                        filtered_pulse_data = filtered_pulse_data[-100:]

                    # Plot the pulse data
                    ax1.clear()
                    ax1.plot(pulse_data, label="Raw Pulse Data", alpha=0.5)
                    ax1.plot(filtered_pulse_data, label="Filtered Pulse Data", linestyle='--', color='blue')
                    if adp_threshold is not None:
                        ax1.axhline(y=adp_threshold, color='r', linestyle='--', label="Threshold")
                    ax1.legend()
                    canvas.draw()

                elif line.startswith("H,"):  # Heart rate data
                    heart_rate = float(line[2:])
                    if heart_rate <= 120:  # Ignore readings above 120 BPM
                        heart_rate_data.append(heart_rate)
                        window['-BPM-'].update(f"{heart_rate:.1f} BPM")

                    # Manage x-axis sliding window for heart rate data
                    if len(time_data) > 10:
                        time_data = time_data[-10:]
                        heart_rate_data = heart_rate_data[-10:]

                    # Plot heart rate data
                    ax2.clear()
                    ax2.plot(time_data, heart_rate_data, label="Heart Rate")
                    ax2.legend()
                    canvas.draw()

                elif line.startswith("T,"):  # Adaptive threshold
                    adp_threshold = int(line[2:])

                elif line.startswith("S,"):  # Sequence number
                    packet_sequence_number = int(line[2:])
    
    # Check if the packet sequence is in order and print the sequence number in the log
                    if packet_sequence_number != last_sequence_number + 1:
                           window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet out of order! Order: {packet_sequence_number}")
                    else:
        # Update log with packet order if in sequence
                         window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet received. Order: {packet_sequence_number}")

                    last_sequence_number = packet_sequence_number



                # Update time data
                t += 1
                time_data.append(t)

                # Log only once per second
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

    # Check for packet loss (if 5 seconds have passed since the last packet)
    elif time.time() - last_packet_time > 5:
        if time.time() - last_log_time > 1:  # Log only once per second
            window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet not received for 5 seconds!")
            last_log_time = time.time()

    # Keep the GUI responsive
    window.refresh()


# Close serial and GUI on exit
ser.close()
window.close()

