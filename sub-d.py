#!/usr/bin/env python
"""Subsystem D unit testing script.
This script measures the frequency response of the modulator."""

import pyvisa
import time
from numpy import *
from matplotlib.pyplot import *
import sys

__author__ = 'Sean Victor Hum'
__copyright__ = 'Copyright 2025'
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
        scope.close()
        sys.exit(1)

def check_scales():
    scale1 = scope.query(':CHAN1:SCAL?')
    scale2 = scope.query(':CHAN2:SCAL?')

    if (scale1 != scale2):
        print('The scales of the 2 channels do not match.')
        user_abort()
        
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

# Setup trigger
scope.write(':TRIG:SWEep AUTO')
scope.write(':TRIG:EDGE:SOURce CHAN1')
scope.write(':TRIG:EDGE:LEVel +0.0')

#print('Trigger:', scope.query(':TRIG?'), flush=True)

print('Connect your subsystem as shown in the wiring diagram and power it on.')
user_prompt()

# Setup function generator on scope as stimulus
scope.write(':WGEN:FUNC SIN')
scope.write(':WGEN:FREQ 1.0E+03') # 1 kHz test
scope.write(':WGEN:OUTP ON')

# Setup acquisition
scope.write(':TIMebase:SCAL +5.0E-04') # 500 us/div
scope.write(':CHAN1:COUP AC')
scope.write(':CHAN2:COUP AC')

# Check phase shift
print('Adjust the timebase and triggering so the signals are stable.')
print('Adjust the voltage scale on CH1 and CH2 so they are identical')
print('and the 2 signals occupy most of the screen.')
user_prompt()
check_scales()

phdiff = float(scope.query(':MEAS:PHASe? CHAN1'))
print('Measured phase shift between I and Q for 1 kHz message signal:', phdiff, 'deg')

if (phdiff > 0):
    print('WARNING: the phase shift is leading when it should be lagging. Ensure the function')
    print('generator and oscilloscope are connected as shown in the wiring diagram.')
else:
    print('Q is lagging I as expected.')
    
print('About to initiate frequency sweep.')

# Set up frequency sweep
N = 40
freq = arange(N)*100 + 100

input_ampl = 0.316*sqrt(2)              # Amplitude of wave generator output

print('The following message frequencies will be measured:', freq)

# Initialize vectors for storing data
ampl_i = zeros(N, float)
ampl_q = zeros(N, float)
phdiff = zeros(N, float)

scope.write(':TIMebase:SCAL +1.0E-03')
scope.write(':WGEN:volt %e' % (input_ampl))
scope.write(":WGEN:FREQ %e" % freq[0])

print('Adjust the triggering so the signals are stable.')
print('Adjust the voltage scale on CH1 and CH2 so they are identical')
print('and the 2 signals occupy most of the screen.')
user_prompt()
check_scales()

# Frequency sweep 1
for k in range(N):
    scope.write(":WGEN:FREQ %e" % freq[k])
    #scope.write(':SINGle')
    ampl_i[k] = float(scope.query(':MEAS:VPP? CHAN1'))
    ampl_q[k] = float(scope.query(':MEAS:VPP? CHAN2'))
    phdiff[k] = float(scope.query(':MEAS:PHASe? CHAN1'))
    print('Frequency point %d/%d, f=%.4f kHz: %f %f %f' % (k+1, N, freq[k]/1e3, ampl_i[k], ampl_q[k], phdiff[k]))

print('Done')
    
scope.write(':WGEN:OUTP OFF')
scope.close()
    
# Save and plot data
savetxt('mod_iq.txt', (freq, ampl_i, ampl_q, phdiff));

# H2 = (ampl_i/input_ampl)**2 + (ampl_q/input_ampl)**2
# H2max = max(H2)

# fig, ax = subplots()
# ax.plot(freq, 10*log10(H2/H2max))
# ax.set_xlabel('Message frequency [Hz]');
# ax.set_ylabel('Normalized modulator transfer function [dB]');
# ax.grid(True)
# savefig('mod_bode.png')

fig, ax = subplots()
ax.plot(freq, 20*log10(ampl_i/input_ampl))
ax.semilogx(freq, 20*log10(ampl_q/input_ampl))
ax.set_xlabel('Message frequency [Hz]');
ax.set_ylabel('|I|, |Q| [dB]');
ax.legend(('I', 'Q'))
ax.grid(True)
savefig('mod_iq_compare.png')

fig, ax = subplots()

ax.set_xlabel('Message frequency [Hz]')
ax.set_ylabel('Amplitude balance I/Q [dB]')
ax.plot(freq, 20*log10(ampl_i/ampl_q))
ax.grid(True)
savefig('mod_balance_ampl.png')

fig, ax = subplots()
ax.set_xlabel('Message frequency [Hz]')
ax.set_ylabel('Phase shift between I and Q [deg]')
ax.plot(freq, phdiff)
ax.grid(True)
ax.set_ylim((-200, 200))
savefig('mod_balance_phase.png')
