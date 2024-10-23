import PySimpleGUI as sg
import serial
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Initialize serial connection (adjust COM port and baud rate)
ser = serial.Serial('COM5', 115200, timeout=1)  # Replace 'COM5' with your port

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

# Function to flash the alarm LEDs
def flash_alarm(canvas, state):
    colors = {"high": "red", "low": "blue"}
    positions = {"high": (50, 50), "low": (250, 50)}
    for key in ["high", "low"]:
        if state == key:
            for _ in range(3):  # Flashing three times
                canvas.create_oval(positions[key][0] - 20, positions[key][1] - 20,
                                   positions[key][0] + 20, positions[key][1] + 20,
                                   fill=colors[key])
                time.sleep(0.5)
                canvas.create_oval(positions[key][0] - 20, positions[key][1] - 20,
                                   positions[key][0] + 20, positions[key][1] + 20,
                                   fill="grey")
                time.sleep(0.5)

# Layout for the GUI
layout = [
    [sg.Text("Pulse Rate: "), sg.Text("0", key='-BPM-', font=("Helvetica", 50), size=(10, 1))],
    [sg.Canvas(key='-CANVAS-', size=(1200, 800)),
     sg.Column([
         [sg.Canvas(key='-ALARM-', size=(300, 100))],
         [sg.Text("High Pulse Threshold"), sg.Slider(range=(50, 150), orientation='h', size=(20, 15), default_value=100, key='-HIGH-THRESH-'), sg.InputText('100', size=(5, 1), key='-HIGH-INPUT-')],
         [sg.Text("Low Pulse Threshold"), sg.Slider(range=(50, 150), orientation='h', size=(20, 15), default_value=60, key='-LOW-THRESH-'), sg.InputText('60', size=(5, 1), key='-LOW-INPUT-')],
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
heart_rate_data = []
time_data = []
t = 0

# Set update frequency to 1 second
last_update_time = time.time()
last_packet_time = time.time()

# Initialize variables for adaptive threshold calculation
alpha = 0.1
emaValue = 1900
adp_threshold = emaValue + 20

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
                # Split the line by commas and strip any extra spaces
                data = [x.strip() for x in line.split(",")]
                heart_rate = float(data[0])  # First value is heart rate
                pulse_values = list(map(int, data[1:]))  # Remaining values are pulse signal

                # Update heart rate
                heart_rate_data.append(heart_rate)
                window['-BPM-'].update(f"{heart_rate:.1f} BPM")

                # Add time point for graph
                time_data.append(t)
                t += 1

                # Update raw pulse data
                pulse_data.extend(pulse_values)
                if len(pulse_data) > 250:  # Limit the size of data to avoid memory overload
                    pulse_data = pulse_data[-250:]
                    time_data = time_data[-250:]

                # Manage x-axis sliding window for both plots
                if len(time_data) > 10:
                    time_data = time_data[-10:]  # Keep last 10 seconds of data
                    heart_rate_data = heart_rate_data[-10:]  # Same for heart rate

                # Determine pulse status and log it in the required format
                timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                if heart_rate > high_threshold:
                    log_message = f"{timestamp}: Pulse High"
                    draw_alarm(alarm_canvas, "high")
                elif heart_rate < low_threshold:
                    log_message = f"{timestamp}: Pulse Low"
                    draw_alarm(alarm_canvas, "low")
                else:
                    log_message = f"{timestamp}:Pulse Normal"
                    draw_alarm(alarm_canvas, "normal")
                
                window['-LOG-'].print(log_message)

                # Calculate adaptive threshold
                emaValue = (alpha * pulse_values[-1]) + ((1 - alpha) * emaValue)
                adp_threshold = emaValue + 20

                # Refresh the plot every second
                if time.time() - last_update_time >= 1:
                    last_update_time = time.time()

                    # Clear and update both plots
                    ax1.clear()
                    ax1.plot(pulse_data, label="Pulse Waveform")
                    ax1.axhline(y=adp_threshold, color='r', linestyle='--', label="Threshold")  # Add threshold line
                    ax1.set_xlabel("Sample Points")
                    ax1.set_ylabel("Pulse Data")
                    ax1.legend()

                    ax2.clear()
                    ax2.plot(time_data, heart_rate_data, label="Heart Rate")
                    ax2.set_xlim([min(time_data), max(time_data)])  # Keep last 10 seconds range
                    ax2.set_ylim([min(heart_rate_data) - 5, max(heart_rate_data) + 5])  # Adjust Y range dynamically
                    ax2.set_xlabel("Time (s)")
                    ax2.set_ylabel("Heart Rate (BPM)")
                    ax2.legend()

                    canvas.draw()

            except Exception as e:
                # Hide error messages from the data log
                pass

    # Check for packet arrival alarm
    if time.time() - last_packet_time > 5:
        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet not received for 5 seconds!")

ser.close()
