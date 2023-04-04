#!/usr/bin/env python
"""Subsystem C unit testing script."""

import pyvisa
import time
from numpy import *
from matplotlib.pyplot import *
import sys

__author__ = 'Stewart Pearson and Sean Victor Hum'
__copyright__ = 'Copyright 2023'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'sean.hum@utoronto.ca'

def user_prompt():
    str = input('Hit Enter to proceed or ! to abort:')
    if (str == '!'):
        print('Measurement aborted')
        user_abort()

def user_abort():
        scope.close()
        sys.exit(0)

comport = 'COM3'
#comport = 'COM10'

# Try to load serial library and initialize serial port
try:
    import serial
    ser = serial.Serial(port=comport, baudrate=9600, timeout=1)
    ser.close()
except ImportError:
    print('pyserial not installed')
    print('To install pyserial type \r\n"pip install pyserial"')
    sys.exit(1)
except serial.SerialException:
    print('Cannot initialize serial communication.')
    print('Is the device plugged in? \r\nIs the correct COM port chosen?')
    sys.exit(1)

# Open serial port
ser.open()  
    
# Open instrument connection(s)
rm = pyvisa.ResourceManager()
school_ip = True
#school_ip = False
if (school_ip):
    scope = rm.open_resource('TCPIP0::192.168.0.253::hislip0::INSTR')
else:
    scope = rm.open_resource('TCPIP0::192.168.2.253::hislip0::INSTR')

# Define string terminations and timeouts
scope.write_termination = '\n'
scope.read_termination = '\n'
scope.timeout = 10000           # 10s

# Get ID info
scope_id = scope.query('*IDN?').strip().split(',')
print('Connected to oscilloscope:', scope_id[1], flush=True)

# Set probe scaling to 1:1
scope.write('CHANnel1:PROBe +1.0')
scope.write('CHANnel2:PROBe +1.0')

# Set vertical scale
scope.write(':CHANnel1:SCALe +1.0') 
scope.write(':CHANnel2:SCALe +1.0') 

# Set coupling
scope.write(':CHANnel1:COUPling AC') 
scope.write(':CHANnel2:COUPling AC') 

# Set up scope timebase and measurements
scope.write('TIMebase:MODE MAIN')
scope.write('TIMebase:REFerence CENTer')
scope.write(':MEASure:CLEAr')

# Setup trigger
scope.write(':TRIG:SWEep AUTO')
scope.write(':TRIG:EDGE:LEVel +0.0')
scope.write('TRIGger:EDGE:SLOPe POSITIVE')
scope.write('TRIGger:EDGE:COUPling AC')

print('Connect your subsystem as shown in the wiring diagram and power it on.')
user_prompt()

# Frequency sweep
N = 17

freq = arange(N)/(N-1)*8e6 + 8e6
print('FREQUENCY MEASUREMENT')
print('The following frequency points will be measured:', freq)

sercmd = 'FA%09d;' % (int(freq[0]))
ser.write(serial.to_bytes(sercmd.encode()))
fa_query = 'FA;'
ser.write(serial.to_bytes(fa_query.encode()))
response =ser.readline().decode('UTF-8')
#print('CAT response: ' + response)

scope.write('TIMebase:SCALe +50E-09')
scope.write('TRIGger:SOURce CHANnel1')

print('\nYou should have a LO signals on CH1 and CH2 at a frequency of %.1f MHz.' % (freq[0]/1e6))

phdiff = float(scope.query(':MEAS:PHASe? CHAN2'))
if (phdiff > 0):
    print('WARNING: The phase difference seems to be backwards (LO_90 leads LO_0 when it should lag). This should be corrected.')
    
user_prompt()

scope.write('TIMebase:SCALe +500E-09')
# Initialize vectors for storing data
meas_freq_0 = zeros(N, float)
meas_freq_90 = zeros(N, float)
phdiff = zeros(N, float)

# Frequency sweep loop
for k in range(N):
    print('Frequency point %d/%d, f=%.2f MHz' % (k+1, N, freq[k]/1e6))
    sercmd = 'FA%09d;' % (int(freq[k]))
    ser.write(serial.to_bytes(sercmd.encode()))
    fa_query = 'FA;'
    ser.write(serial.to_bytes(fa_query.encode()))
    response =ser.readline().decode('UTF-8')
    print('  CAT response: ' + response)
    scope.write('TRIGger:SOURce CHANnel1')
    time.sleep(0.5)
    meas_freq_0[k] = float(scope.query('MEASure:COUNter? CHANnel1'))
    scope.write('TRIGger:SOURce CHANnel2')
    time.sleep(0.5)
    meas_freq_90[k] = float(scope.query('MEASure:COUNter? CHANnel2'))
    phdiff[k] = float(scope.query(':MEAS:PHASe? CHAN2'))
    print('  Measured frequency:', meas_freq_0[k], 'Hz / ', meas_freq_90[k], 'Hz')
    print('  Phase difference:', phdiff[k], 'deg')
    
scope.close()

print('TX/RX SWITCH TEST')
print('About to initiate TX/RX switch test.')
user_prompt()

print('Entering transmit mode')
tx_set = 'TX1;'
ser.write(serial.to_bytes(tx_set.encode()))
tx_query = 'TX;'
ser.write(serial.to_bytes(tx_query.encode()))
response =ser.readline().decode('UTF-8')
print('CAT response: ' + response)
print('Transmit mode set. Check that /TXEN = 0V and there is continuity between ANT and PA_OUT.')
input("Press Enter to continue...")

print('Entering receive mode.')
tx_set = 'TX0;'
ser.write(serial.to_bytes(tx_set.encode()))
tx_query = 'TX;'
ser.write(serial.to_bytes(tx_query.encode()))
response =ser.readline().decode('UTF-8')
print('CAT response: ' + response)
print('Receive mode set. Check that /TXEN = 3.3V and there is continuity between ANT and RX_SIG.')
	
ser.close()
print('Done')
    
# Save and plot data
savetxt('freq.txt', (freq, meas_freq_0, meas_freq_90))

fig, ax = subplots()
ax.plot(freq/1e6, meas_freq_0/1e6)
ax.plot(freq/1e6, meas_freq_90/1e6)
ax.set_xlabel('Command frequency [MHz]');
ax.set_ylabel('Actual frequency [MHz]');
ax.grid(True)
ax.legend(('LO_0', 'LO_90'))
ax.set_title('Frequency output of Subsystem C')
savefig('freq.png')

freq_error_0 = meas_freq_0 - freq;
freq_error_90 = meas_freq_90 - freq;

fig, ax = subplots()
ax.plot(freq/1e6, freq_error_0)
ax.plot(freq/1e6, freq_error_90)
ax.set_xlabel('Command frequency [MHz]');
ax.set_ylabel('Frequency error [Hz]');
ax.grid(True)
ax.legend(('LO_0', 'LO_90'))
ax.set_title('Frequency error of Subsystem C')
savefig('freq_error.png')

fig, ax = subplots()
ax.plot(freq/1e6, phdiff)
ax.set_xlabel('Command frequency [MHz]');
ax.set_ylabel('Phase shift [deg]');
ax.grid(True)
ax.set_title('Phase of Subsystem C')
savefig('phase.png')
