import pyvisa
import time
from numpy import *
from matplotlib.pyplot import *
import sys

rm = pyvisa.ResourceManager()
#print(rm)
scope = rm.open_resource('TCPIP0::192.168.2.253::hislip0::INSTR')
supply = rm.open_resource('TCPIP0::192.168.2.251::5025::SOCKET')

# Define string terminations
scope.write_termination = '\n'
scope.read_termination = '\n'
supply.write_termination = '\n'
supply.read_termination = '\n'

# Get the ID info
scope_id = scope.query('*IDN?').strip().split(',')
supply_id = supply.query('*IDN?').strip().split(',')
print('Connected to oscilloscope:', scope_id[1], flush=True)
print('Connected to power supply:', supply_id[1], flush=True)

scope.timeout = 10000  # 10s
supply.timeout = 10000  # 10s

# Set probes
scope.write('CHANnel1:PROBe +1.0')
scope.write('CHANnel2:PROBe +1.0')

# Setup trigger
scope.write(':TRIG:SWEep AUTO')
scope.write(':TRIG:EDGE:SOURce CHAN1')
scope.write(':TRIG:EDGE:LEVel +0.0')

#print('Trigger:', scope.query(':TRIG?'), flush=True)
#print('Trigger:', scope.query(':TRIG:EDGE:LEVel?'), flush=True)

# Disable power supply output and wavegen output
supply.write('OUTP OFF, (@2)')
scope.write(':WGEN:OUTP OFF')

input('Connect your subsystem as shown in the wiring diagram and power it on. Hit Enter when ready:')

supply.write('OUTP ON, (@2)')

# Setup function generator on scope as stimulus
scope.write(':WGEN:FUNC SIN')
#scope.write(':WGEN:volt 1.0')
scope.write(':WGEN:volt 10.0')
scope.write(':WGEN:FREQ 1.400E+07')
scope.write(':WGEN:OUTP ON')

# Setup acquisition
scope.write(':TIMebase:SCAL +5.0E-08') # 50 ns/div
scope.write(':CHAN1:COUP AC')
scope.write(':CHAN1:DISP ON')
scope.write(':FFT:DISP OFF')

print('Adjust the timebase and triggering so the signals are stable.')
print('You may adjust the operating frequency if you wish (default: 14 MHz).')
print('Adjust the voltage scale on CH1 so that it is stable and the')
input('signal occupies most of the screen. Hit Enter when ready:')

# Query power supply and scope for single point measurement
V = float(supply.query('VOLT? (@2)'))
I = float(supply.query('MEAS:CURR? CH2'))
Pdc = V*I
Vrms = float(scope.query(':MEAS:VRMS? CHAN1'))
Prf = Vrms**2/50

print('Supply voltage:', V, 'V')
print('Current draw:', I, 'A')
print('DC power consumption:', Pdc, 'W')
print('RF power output:', Prf, 'W')

if (Prf < 1.0):
    print('Warning: RF output power < 1 W for 1 Vpp input signal!')

print('DC-to-RF power conversion efficiency:', Prf/Pdc*100, '%')

str = input('Hit Enter to initiate FFT analysis or A to abort:')
if (str == 'A'):
    print('Measurement aborted')
    scope.close()
    supply.close()
    sys.exit(0)

A_dBV = zeros(5, float)
scope.write(':CHAN1:DISP OFF')
scope.write(':FFT:DISP ON')
scope.write(':FFT:CENT 37.5 MHz')
scope.write(':FFT:SPAN 75 MHz')
scope.write(':FFT:SOUR CHAN1')
scope.write(':TIMebase:SCAL +5.0E-06') # 5 us/div
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

print('Measured harmonics (dBV):', A_dBV)

# Calculate THD
A = 10**(A_dBV/20)
A2 = A**2
numerator = sqrt(sum(A2[1:]))
denominator = A[0]
THD = numerator/denominator
print('Total harmonic distortion:', THD*100, '%')

str = input('Hit Enter to initiate frequency sweep or A to abort:')

if (str == 'A'):
    print('Measurement aborted')
    scope.close()
    supply.close()
    sys.exit(0)

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
    
# Turn of waveform generator
scope.write(':WGEN:OUTP OFF')

scope.close()
supply.close()

# Save and plot data

Prf = Vout**2/50

savetxt('pout.txt', (freq, Prf));

fig, ax = subplots()

ax.plot(freq/1e6, 10*log10(Prf))
ax.set_xlabel('Frequency [MHz]');
ax.set_ylabel('RF output power [dBW]');
ax.grid(True)
ax.set_title('PA Frequency Response')
savefig('pout_dBw.png')

fig, ax = subplots()

ax.plot(freq/1e6, Prf)
# plot(freq/1e6, 20*log10(ampl_q/50e-3))
ax.set_xlabel('Frequency [MHz]');
ax.set_ylabel('RF output power [W]');
ax.grid(True)
ax.set_title('PA Frequency Response')
savefig('pout.png')
