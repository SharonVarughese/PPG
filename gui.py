import serial
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.animation import FuncAnimation
import re  # Regular expression module

# Define your serial port settings
serial_port = 'COM4'  # Adjust the port according to your setup
baud_rate = 115200  # Updated baud rate

# Create a function to initialize the plot with darkgrid style
def create_matplotlib_fig():
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots()
    line, = ax.plot([], [], lw=2)
    ax.set_xlim(0, 100)  # Keep x-limits for the display
    ax.set_ylim(0, 2000)  # Adjust y-limits based on expected sensor values
    ax.set_title("Real-time Pulse Sensor Data")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Sensor Value")
    return fig, ax, line

# Update the plot in real-time
def update_plot(frame, ser, line, x_data, y_data):
    try:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            # Split data to extract sensor value
            parts = data.split(", ")
            if len(parts) > 0:
                try:
                    sensor_value = float(parts[0])  # Get the sensor reading
                    # Append new data
                    x_data.append(x_data[-1] + 0.02 if x_data else 0)  # Increment x by 20ms
                    y_data.append(sensor_value)

                    # Keep only the last 100 points for plotting
                    if len(x_data) > 100:
                        x_data.pop(0)
                        y_data.pop(0)

                    line.set_data(x_data, y_data)
                    plt.draw()
                except ValueError:
                    print("Could not convert sensor value to float.")

    except Exception as e:
        print(f"Error reading serial data: {e}")

# Initialize serial communication
ser = serial.Serial(serial_port, baud_rate, timeout=1)

# Create plot
fig, ax, line = create_matplotlib_fig()
x_data, y_data = [], []

# Animate the plot
ani = FuncAnimation(fig, update_plot, fargs=(ser, line, x_data, y_data), interval=20)

plt.show()

# Don't forget to close the serial connection when done
ser.close()
