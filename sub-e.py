#!/usr/bin/env python
"""Subsystem E unit testing script."""

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
        scope.write(':WGEN:OUTP OFF')
        scope.close()
        supply.close()
        sys.exit(1)

# Open instrument connection(s)
rm = pyvisa.ResourceManager()
scope = rm.open_resource('TCPIP0::192.168.2.253::hislip0::INSTR')
supply = rm.open_resource('TCPIP0::192.168.2.251::5025::SOCKET')

# Define string terminations and timeouts
scope.write_termination = '\n'
scope.read_termination = '\n'
supply.write_termination = '\n'
supply.read_termination = '\n'
scope.timeout = 10000           # 10s
supply.timeout = 10000          # 10s

# Get ID info
scope_id = scope.query('*IDN?').strip().split(',')
supply_id = supply.query('*IDN?').strip().split(',')
print('Connected to oscilloscope:', scope_id[1], flush=True)
print('Connected to power supply:', supply_id[1], flush=True)

# Set probe scaling to 1:1
scope.write('CHANnel1:PROBe +1.0')
scope.write('CHANnel2:PROBe +1.0')

# Setup trigger
scope.write(':TRIG:SWEep AUTO')
scope.write(':TRIG:EDGE:SOURce CHAN1')
scope.write(':TRIG:EDGE:LEVel +0.0')

#print('Trigger:', scope.query(':TRIG?'), flush=True)

# Disable power supply output and wavegen output
supply.write('OUTP OFF, (@2)')
scope.write(':WGEN:OUTP OFF')

print('Connect your subsystem as shown in the wiring diagram and power it on.')
print('Make sure you have asserted the /TXEN line (set it low)!')
user_prompt()

# Turn on power supply and set up wavegen
supply.write('OUTP ON, (@2)')
scope.write(':WGEN:FUNC SIN')
scope.write(':WGEN:FREQ 1.400E+07')

# Measure idle current
V = float(supply.query('VOLT? (@2)'))
Iidle = float(supply.query('MEAS:CURR? CH2'))
Pidle = V*Iidle

# Set wavegen amplitude and enable
drive_amplitude = 10.0          # Set to input drive amplitude required
scope.write(':WGEN:volt %e' % (drive_amplitude))
scope.write(':WGEN:OUTP ON')

# Setup acquisition
scope.write(':TIMebase:SCAL +5.0E-08') # 50 ns/div
scope.write(':CHAN1:COUP AC')
scope.write(':CHAN1:DISP ON')
scope.write(':FFT:DISP OFF')

print('Adjust the timebase and triggering so the signals are stable.')
print('You may adjust the operating frequency if you wish (default: 14 MHz).')
print('Adjust the voltage scale on CH1 so that it is stable and the')
print('signal occupies most of the screen.')
user_prompt()

# Query power supply and scope for single point measurement
V = float(supply.query('VOLT? (@2)'))
Iactive = float(supply.query('MEAS:CURR? CH2'))
Pactive = V*Iactive
Vrms = float(scope.query(':MEAS:VRMS? CHAN1'))

print('Supply voltage:', V, 'V')
print('Current draw (idle):', Iidle, 'A')
print('Current draw (active):', Iactive, 'A')
print('DC power consumption:', Pactive, 'W')
print('RF RMS voltage output:', Vrms, 'Vrms')

print('About to initiate FFT analysis.')
user_prompt()

A_dBV = zeros(5, float)         # Vector to store first 5 harmonic amplitudes

# Setup FFT
scope.write(':CHAN1:DISP OFF')
scope.write(':FFT:DISP ON')
scope.write(':FFT:CENT 37.5 MHz')
scope.write(':FFT:SPAN 75 MHz')
scope.write(':FFT:SOUR CHAN1')
scope.write(':TIMebase:SCAL +1.0E-06') # 1 us/div
scope.write(':MARKer:X1Y1source FFT')
scope.write(':MARKer:X2Y2source FFT')
scope.write(':MARK:MODE WAV')

f0 = float(scope.query('WGEN:FREQ?'))
print('Source frequency set to:', f0/1e6, 'MHz')

# Measure harmonics
scope.write(':MARKer:X1P %e' % (f0))
scope.write(':MARKer:X2P %e' % (2*f0))
time.sleep(1)
A_dBV[0] = float(scope.query(':MARK:Y1P?'))
A_dBV[1] = float(scope.query(':MARK:Y2P?'))

scope.write(':MARKer:X1P %e' % (3*f0))
scope.write(':MARKer:X2P %e' % (4*f0))
time.sleep(1)
A_dBV[2] = float(scope.query(':MARK:Y1P?'))
A_dBV[3] = float(scope.query(':MARK:Y2P?'))

scope.write(':MARKer:X1P %e' % (5*f0))
time.sleep(1)
A_dBV[4] = float(scope.query(':MARK:Y1P?'))

# Calculate power spectrum
n = arange(1, 6)
Pcoeffs = (10**(A_dBV/20))**2/50
P_dBW = 10*log10(Pcoeffs)
print('Measured harmonics (dBV):', A_dBV)

P1 = Pcoeffs[0]
print('RF power output at %.1f MHz: %f W' % (f0/1e6, P1))
eff = P1/Pactive

if (P1 < 1.0):
    print('Warning: RF output power < 1 W for 1 Vpp input signal!')

print('DC-to-RF power conversion efficiency:', eff*100, '%')

# Calculate THD
A = 10**(A_dBV/20)
A2 = A**2
numerator = sqrt(sum(A2[1:]))
denominator = A[0]
THD = numerator/denominator
print('Total harmonic distortion:', THD*100, '%')

print('About to initiate frequency sweep.')
user_prompt()

# Restore display
scope.write(':CHAN1:DISP ON')
scope.write(':FFT:DISP OFF')
scope.write(':TIMebase:SCAL +5.0E-08') # 5 us/div

# Frequency sweep
N = 41                          # Number of frequency points 
freq = arange(N)/(N-1)*14e6 + 4e6 # Array of frequency points
Vout = zeros(N, float)

print('Measuring frequency response...')
for k in range(N):
    scope.write(':WGEN:FREQ %e' % freq[k])
    time.sleep(1)
    Vout[k] = float(scope.query(':MEAS:VRMS? CHAN1'))
    #print(freq[k], Vout[k])
print('Done')
    
# Turn of waveform generator and close connections
scope.write(':WGEN:OUTP OFF')

scope.close()
supply.close()

# Save and plot data
Prf = Vout**2/50
savetxt('pout.txt', (freq, Prf))
savetxt('spectrum.txt', (n, Pcoeffs))

# Plot Pout vs frequency (dBW)
fig, ax = subplots()
ax.plot(freq/1e6, 10*log10(Prf))
ax.set_xlabel('Frequency [MHz]')
ax.set_ylabel('RF output power [dBW]')
ax.grid(True)
ax.set_title('PA Frequency Response for Vin = %.1f Vpp' % (drive_amplitude))
savefig('pout_dBW.png')

# Plot Pout vs frequency (W)
fig, ax = subplots()
ax.plot(freq/1e6, Prf)
# plot(freq/1e6, 20*log10(ampl_q/50e-3))
ax.set_xlabel('Frequency [MHz]')
ax.set_ylabel('RF output power [W]')
ax.set_yscale('log')
ax.set_ylim((1e-3, 10))
ax.grid(True)
ax.set_title('PA Frequency Response for Vin = %.1f Vpp' % (drive_amplitude))
savefig('pout.png')

# Plot output spectrum
fig, ax = subplots()
ax.stem(n, Pcoeffs, use_line_collection=True)
ax.set_ylabel('RF output power [W]')
ax.set_yscale('log')
ax.grid(True)
ax.set_title('PA Output Spectrum: f = %.1f MHz, eff=%.1f %%, THD=%.1f %%' % (f0/1e6, eff*100, THD*100))
savefig('spectrum.png')
