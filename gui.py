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

# Create the initial Matplotlib figure
def create_plot():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))  # Increased figure size to be WAY larger
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Pulse Data")
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Heart Rate (BPM)")
    return fig, ax1, ax2

# Layout for the GUI
layout = [
    [sg.Text("Pulse Rate: "), sg.Text("0", key='-BPM-', font=("Helvetica", 50), size=(10, 1))],  # Even larger text
    [sg.Canvas(key='-CANVAS-', size=(1200, 800))],  # Significantly larger canvas
    [sg.Multiline(size=(100, 10), key='-LOG-', disabled=True, font=("Helvetica", 16))],  # Larger log
    [sg.Button("Exit", font=("Helvetica", 16))]
]

# Create the window
window = sg.Window("PPG Monitor", layout, finalize=True, resizable=True)

# Draw the initial plot
fig, ax1, ax2 = create_plot()
canvas = draw_figure(window['-CANVAS-'].TKCanvas, fig)

pulse_data = []
heart_rate_data = []
time_data = []
threshold = 100  # Example threshold for high/low pulse alarm
t = 0

# Set update frequency to 1 second
last_update_time = time.time()
last_packet_time = time.time()

# Main loop
while True:
    event, values = window.read(timeout=100)

    if event == sg.WIN_CLOSED or event == 'Exit':
        break

    # Read data from serial
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()  # Read serial data
        last_packet_time = time.time()  # Update last packet time
        
        # Process the received line
        if line:
            try:
                # Split the line by commas, assume the first value is the heart rate
                data = line.split(",")
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

                # Log the event
                timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                window['-LOG-'].print(f"{timestamp}: Received Data: Heart Rate = {heart_rate:.1f} BPM")

                # Refresh the plot every second
                if time.time() - last_update_time >= 1:
                    last_update_time = time.time()

                    # Clear and update both plots
                    ax1.clear()
                    ax1.plot(pulse_data, label="Pulse Waveform")
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
                error_message = f"Error processing line: {line} - {e}"
                window['-LOG-'].print(error_message)  # Log the error

    # Check for packet arrival alarm
    if time.time() - last_packet_time > 5:
        window['-LOG-'].print(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}: Packet not received for 5 seconds!")

ser.close()
window.close()
