import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

# Butterworth Low Pass Filter Class
class Filtering_LPF:
    # Class variables
    order = 6  # Butterworth filter order
    
    # Constructor
    def __init__(self, frequency, sampling_rate):
        print('new LPF Created')
        self.cutoff = frequency
        self.fs = sampling_rate

    # Destructor
    def __del__(self):
        print("LPF deleted")

    # Butterworth filter function
    def butter_lowpass(self):
        # Get the Nyquist frequency
        nyq = 0.5 * self.fs
        # Normalize cutoff frequency
        normal_cutoff = self.cutoff / nyq
        # Get Butterworth filter parameters
        b, a = scipy.signal.butter(self.order, normal_cutoff, btype='low', analog=False)
        return b, a

    # Butterworth filtering function
    def butter_filter(self, data):
        b, a = self.butter_lowpass()
        # Apply the filter to the data
        y = scipy.signal.lfilter(b, a, data)
        return y

# FFT-based Low Pass Filter Function
def fft_filter(data, cutoff_freq, sampling_rate):
    # Get relative cutoff freq index
    cutoff_index = int(cutoff_freq * len(data) / sampling_rate)
    
    # FFT transform to frequency domain
    F = np.fft.fft(data)
    F_freq = np.fft.fftfreq(len(data), 1 / sampling_rate)
    
    # Apply the filter by setting the frequencies above cutoff to 0
    F[cutoff_index + 1 : -cutoff_index] = 0
    
    # Transform back to time domain
    filtered_data = np.fft.ifft(F).real
    
    return filtered_data

# Arguments for the low pass filters
cut_off_frequency = 30
sampling_rate = 500

# Create an instance of the Butterworth filter class
Low_Pass = Filtering_LPF(cut_off_frequency, sampling_rate)

# Creating the data for filtering
T = 0.5  # value taken in seconds
n = int(T * sampling_rate)  # total number of samples
t = np.linspace(0, T, n, endpoint=False)
data = np.sin(2 * 2 * np.pi * t) + 1.5 * np.cos((sampling_rate / 2 - 50) * 2 * np.pi * t)

# Filter the data using the Butterworth low pass filter
filtered_data_butterworth = Low_Pass.butter_filter(data)

# Filter the data using the FFT-based low pass filter
filtered_data_fft = fft_filter(data, cut_off_frequency, sampling_rate)

# Plotting the results
plt.figure(figsize=(12, 8))

# Original Data Plot
plt.subplot(3, 1, 1)
plt.plot(t, data, label='Original Data', color='blue')
plt.title('Original Data')
plt.xlabel('Time [seconds]')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)

# Butterworth Filtered Data Plot
plt.subplot(3, 1, 2)
plt.plot(t, filtered_data_butterworth, label='Butterworth Filtered Data', color='green')
plt.title('Butterworth Filtered Data')
plt.xlabel('Time [seconds]')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)

# FFT Filtered Data Plot
plt.subplot(3, 1, 3)
plt.plot(t, filtered_data_fft, label='FFT Filtered Data', color='red')
plt.title('FFT Filtered Data')
plt.xlabel('Time [seconds]')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

