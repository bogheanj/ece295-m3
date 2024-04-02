#!/usr/bin/env python
"""Subsystem B unit testing script."""

import pyvisa
import time
from numpy import *
from matplotlib.pyplot import *
import sys

__author__ = 'Sean Victor Hum'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'sean.hum@utoronto.ca'

def user_prompt():
    str = input('Hit Enter to proceed or ! to abort:')
    if (str == '!'):
        print('Measurement aborted')
        user_abort()

def user_abort():
        scope.write(':WGEN:OUTP OFF')
        fxngen.write('OUTPut1 OFF')
        fxngen.write('OUTPut2 OFF')
        scope.close()
        fxngen.close()
        sys.exit(0)
        
def meas_prompt():
    print('Wait for waveform to be stable and adjust vertical scale if desired.')
    print('This can sometimes take a few seconds.')
    str = input('Hit Enter to proceed or ! to abort:')
    if (str == '!'):
        print('Measurement aborted')
        user_abort()

# Open instrument connection(s)
rm = pyvisa.ResourceManager()
school_ip = True
#school_ip = False
if (school_ip):
    scope = rm.open_resource('TCPIP0::192.168.0.253::hislip0::INSTR')
    fxngen = rm.open_resource('TCPIP0::192.168.0.254::5025::SOCKET')
else:
    scope = rm.open_resource('TCPIP0::192.168.2.253::hislip0::INSTR')
    fxngen = rm.open_resource('TCPIP0::192.168.2.254::5025::SOCKET')

# Define string terminations and timeouts
scope.write_termination = '\n'
scope.read_termination = '\n'
fxngen.write_termination = '\n'
fxngen.read_termination = '\n'
scope.timeout = 10000           # 10s
fxngen.timeout = 10000          # 10s

# Get ID info
scope_id = scope.query('*IDN?').strip().split(',')
fxngen_id = fxngen.query('*IDN?').strip().split(',')
print('Connected to oscilloscope:', scope_id[1], flush=True)
print('Connected to function generator:', fxngen_id[1], flush=True)

# Set probe scaling to 1:1
scope.write('CHANnel1:PROBe +1.0')
scope.write('CHANnel2:PROBe +1.0')

# Setup trigger
scope.write(':TRIG:SWEep AUTO')
scope.write(':TRIG:EDGE:LEVel +0.0')

#print('Trigger:', scope.query(':TRIG?'), flush=True)

print('Connect your subsystem as shown in the wiring diagram and power it on.')
print('If your demodulator supports both LSB and USB mode, place it in USB mode.')
print('The desired demodulated signal should be on channel 2 of the')
print('oscilloscope.')
user_prompt()

# Set waveform generator output impedance to high Z
fxngen.write('OUTPUT1:LOAD INF')
fxngen.write('OUTPUT2:LOAD INF')
fxngen.write('UNIT:ANGL DEG')

# Setup waveform generator
drive_amplitude = 0.2          # Set to input drive amplitude required in V
fxngen.write('SOUR1:FUNCtion SIN')
fxngen.write('SOUR1:VOLTage:AMPL %e' % (drive_amplitude))
fxngen.write('SOUR1:VOLTage:OFFS +0.0')
fxngen.write('SOUR1:PHASe +0.0')
fxngen.write('OUTPut1 ON')

fxngen.write('SOUR2:FUNCtion SIN')
fxngen.write('SOUR2:VOLTage:AMPL %e' % (drive_amplitude))
fxngen.write('SOUR2:VOLTage:OFFS +0.0')
fxngen.write('SOUR2:PHASe -9.0E+01')
fxngen.write('OUTPut2 ON')

# Setup acquisition
scope.write(':TIMebase:SCAL +1.0E-03') # 1 ms/div
scope.write(':CHAN1:COUP AC')
scope.write(':CHAN2:COUP AC')
scope.write(':CHAN1:SCAL %e' % (drive_amplitude/5))
scope.write(':CHAN1:DISP OFF')

# Frequency sweep
N = 21
fstart = 100
fstop = 6100
df = (fstop- fstart)/(N-1)
freq = arange(N)*df + fstart

print('The amplitude of the function generator outputs is set to: %f V.' % (drive_amplitude))
print('The following frequency points will be measured:', freq)

# Set up instruments for 1 kHz test point (USB)
fxngen.write('SOUR1:FREQuency %e' % (1e3))
fxngen.write('SOUR2:FREQuency %e' % (1e3))
fxngen.write('SOUR2:PHASe:SYNC')
scope.write(':TRIG:EDGE:SOURce CHAN2')
#print(scope.query(':TRIGger:EDGE:LEVel?'))

print('USB MEASUREMENT')
print('A 1 kHz test signal should be visible on CH1, and you should have a')
print('strong demodulated USB signal on CH2.')
print('Adjust the voltage scales on CH2, and/or the volume control on your')
print('so that the CH2 voltage waveform occupies most of the screen.')
user_prompt()

# Initialize vectors for storing data
ampl_lsb = zeros(N, float)
ampl_usb = zeros(N, float)

# # Check the scale is identical on both channels
# scale1 = scope.query(':CHAN1:SCAL?')
# scale2 = scope.query(':CHAN2:SCAL?')

# if (scale1 != scale2):
#     print('The scales of the 2 channels do not match.')
#     user_abort()

# USB frequency sweep loop
for k in range(N):
    fxngen.write('SOUR1:FREQuency %e' % freq[k])
#    time.sleep(1)
    fxngen.write('SOUR2:FREQuency %e' % freq[k])
#    time.sleep(1)
    fxngen.write('SOUR2:PHASe:SYNC')
    meas_prompt()
    #time.sleep(2)
    ampl_usb[k] = float(scope.query(':MEAS:VRMS? CHAN2'))
    print('Frequency point %d/%d, f=%.2f kHz: %f' % (k+1, N, freq[k]/1e3, ampl_usb[k]))

# Set up instruments for first frequency point (LSB)
# Set up instruments for 1 kHz test point (USB)
fxngen.write('SOUR1:FREQuency %e' % (1e3))
fxngen.write('SOUR2:FREQuency %e' % (1e3))
fxngen.write('SOUR2:PHASe +9.0E+01')
fxngen.write('SOUR2:PHASe:SYNC')
scope.write(':TRIG:EDGE:SOURce CHAN1')
#print(scope.query(':TRIGger:EDGE:LEVel?'))
   
print('\nLSB MEASUREMENT')
print('You should now have a weak LSB signal on CH1 at 1 kHz.')
user_prompt()

# Check the scale is identical on both channels
# scale1 = scope.query(':CHAN1:SCAL?')
# scale2 = scope.query(':CHAN2:SCAL?')

# if (scale1 != scale2):
#     print('The scales of the 2 channels do not match.')
#     user_abort()

# Frequency sweep loop
for k in range(N):
    fxngen.write('SOUR1:FREQuency %e' % freq[k])
    #time.sleep(1)
    fxngen.write('SOUR2:FREQuency %e' % freq[k])
    #time.sleep(1)
    fxngen.write('SOUR2:PHASe:SYNC')
    meas_prompt()
    #time.sleep(2)
    ampl_lsb[k] = float(scope.query(':MEAS:VRMS? CHAN2'))
    print('Frequency point %d/%d, f=%.2f kHz: %f' % (k+1, N, freq[k]/1e3, ampl_lsb[k]))
    
print('Done')
    
fxngen.write('OUTPut1 OFF')
fxngen.write('OUTPut2 OFF')
fxngen.close()
scope.close()
    
# Save and plot data
savetxt('demod.txt', (freq, ampl_lsb, ampl_usb))

fig, ax = subplots()
ax.plot(freq/1e3, ampl_usb)
ax.plot(freq/1e3, ampl_lsb)
ax.set_xlabel('Frequency [kHz]');
ax.set_ylabel('Output amplitude [V]');
ax.grid(True)
ax.legend(('USB', 'LSB'))
ax.set_title('Frequency response of demodulator')
savefig('demod.png')

#rej_lsb = 20*log10(ampl_lsb / ampl_usb)
rej_usb = 20*log10(ampl_usb / ampl_lsb)

fig, ax = subplots()
#ax.plot(freq/1e3, rej_lsb)
ax.plot(freq/1e3, rej_usb)
ax.set_xlabel('Frequency [kHz]');
ax.set_ylabel('Sideband rejection ratio [dB]');
ax.grid(True)
ax.set_title('SSB demodulation performance')
savefig('rejection.png')
