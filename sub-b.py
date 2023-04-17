#!/usr/bin/env python
"""Subsystem B unit testing script."""

import pyvisa
import time
from numpy import *
from matplotlib.pyplot import *
import sys

__author__ = 'Sean Victor Hum'
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
        scope.write(':WGEN:OUTP OFF')
        fxngen.write('OUTPut1 OFF')
        fxngen.write('OUTPut2 OFF')
        scope.close()
        fxngen.close()
        sys.exit(0)
        
# Open instrument connection(s)
rm = pyvisa.ResourceManager()
#school_ip = True
school_ip = True
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
print('Place the demodulator in LSB mode and connect the output to channel 2.')
user_prompt()

# Set waveform generator output impedance to high Z
fxngen.write('OUTPUT1:LOAD INF')
fxngen.write('OUTPUT2:LOAD INF')
fxngen.write('UNIT:ANGL DEG')

# Setup waveform generator
fxngen.write('SOUR1:FUNCtion SIN')
fxngen.write('SOUR1:VOLTage:AMPL +1.0')
fxngen.write('SOUR1:VOLTage:OFFS +0.0')
fxngen.write('SOUR1:PHASe +0.0')
fxngen.write('OUTPut1 ON')

fxngen.write('SOUR2:FUNCtion SIN')
fxngen.write('SOUR2:VOLTage:AMPL +1.0')
fxngen.write('SOUR2:VOLTage:OFFS +0.0')
fxngen.write('SOUR2:PHASe -9.0E+01')
fxngen.write('OUTPut2 ON')

# Setup acquisition
scope.write(':TIMebase:SCAL +5.0E-04') # 500 us/div
scope.write(':CHAN1:COUP AC')
scope.write(':CHAN2:COUP AC')

# Frequency sweep
N = 41
fc = 10e3
#fc = 12.2e3
freq = arange(N)/(N-1)*8e3 + 6e3
#freq = arange(N)/(N-1)*8e3 + 8.2e3

print('The following frequency points will be measured:', freq)

# Set up instruments for first frequency point (LSB)
fxngen.write('SOUR1:FREQuency %e' % (freq[0]))
fxngen.write('SOUR2:FREQuency %e' % (freq[0]))
fxngen.write('SOUR2:PHASe:SYNC')
scope.write(':TRIG:EDGE:SOURce CHAN2')
print(scope.query(':TRIGger:EDGE:LEVel?'))

print('LSB MEASUREMENT')
print('You should have a strong LSB signal on CH2 at %.1f kHz.' % ((fc-freq[0])/1e3))
print('Adjust the voltage scale on CH1 (and CH2) so they are identical')
print('and the desired signal (USB or LSB) occupies most of the screen.')
print('Adjust the triggering so the signals are stable.')
user_prompt()

# Initialize vectors for storing data
ampl_lsb = zeros(N, float)
ampl_usb = zeros(N, float)

# Check the scale is identical on both channels
scale1 = scope.query(':CHAN1:SCAL?')
scale2 = scope.query(':CHAN2:SCAL?')

if (scale1 != scale2):
    print('The scales of the 2 channels do not match.')
    user_abort()

# LSB frequency sweep loop
for k in range(N):
    fxngen.write('SOUR1:FREQuency %e' % freq[k])
    fxngen.write('SOUR2:FREQuency %e' % freq[k])
    time.sleep(0.5)
    fxngen.write('SOUR2:PHASe:SYNC')
    time.sleep(1)
    #ampl_usb[k] = float(scope.query(':MEAS:VRMS? CHAN1'))
    ampl_lsb[k] = float(scope.query(':MEAS:VRMS? CHAN2'))
    print('Frequency point %d/%d, f=%.2f kHz: %f' % (k+1, N, freq[k]/1e3, ampl_lsb[k]))

print('Place the demodulator in USB mode and connect the output to channel 1.')
user_prompt()

# Set up instruments for first frequency point (USB)
fxngen.write('SOUR1:FREQuency %e' % (freq[N-1]))
fxngen.write('SOUR2:FREQuency %e' % (freq[N-1]))
fxngen.write('SOUR2:PHASe:SYNC')
scope.write(':TRIG:EDGE:SOURce CHAN1')
print(scope.query(':TRIGger:EDGE:LEVel?'))

print('USB DEMODULATION')
print('You should have a strong USB signal on CH1 at %.1f kHz.' % ((freq[N-1])/1e3))
print('Adjust the voltage scale on CH1 (and CH2) so they are identical')
print('and the desired signal (USB or LSB) occupies most of the screen.')
print('Adjust the triggering so the signals are stable.')
user_prompt()

# Check the scale is identical on both channels
scale1 = scope.query(':CHAN1:SCAL?')
scale2 = scope.query(':CHAN2:SCAL?')

if (scale1 != scale2):
    print('The scales of the 2 channels do not match.')
    user_abort()

# Frequency sweep loop
for k in range(N):
    fxngen.write('SOUR1:FREQuency %e' % freq[k])
    fxngen.write('SOUR2:FREQuency %e' % freq[k])
    fxngen.write('SOUR2:PHASe:SYNC')
    time.sleep(1)
    ampl_usb[k] = float(scope.query(':MEAS:VRMS? CHAN1'))
    #ampl_lsb[k] = float(scope.query(':MEAS:VRMS? CHAN2'))
    print('Frequency point %d/%d, f=%.2f kHz: %f' % (k+1, N, freq[k]/1e3, ampl_usb[k]))
    
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

rej_lsb = 20*log10(ampl_lsb / ampl_usb)
rej_usb = 20*log10(ampl_usb / ampl_lsb)

fig, ax = subplots()
ax.plot(freq/1e3, rej_lsb)
ax.plot(freq/1e3, rej_usb)
ax.set_xlabel('Frequency [kHz]');
ax.set_ylabel('Sideband rejection ratio [dB]');
ax.grid(True)
ax.legend(('USB', 'LSB'))
ax.set_title('SSB demodulation performance')
savefig('rejection.png')
