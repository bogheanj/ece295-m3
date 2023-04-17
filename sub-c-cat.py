#!/usr/bin/env python
"""Subsystem C script the tests CAT command functionality."""

import time
import sys

__author__ = 'Sean Victor Hum'
__copyright__ = 'Copyright 2023'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'sean.hum@utoronto.ca'

def user_prompt():
    str = input('Hit Enter to proceed or ! to abort:')
    if (str == '!'):
        print('Test aborted')
        user_abort()

def user_abort():
        scope.close()
        sys.exit(0)

def checkcat(cmd, query, expected):
    """Sends CAT command in 'cmd' to device, followed by CAT query command in 'query'.
    Checks that the response string matches that in 'expected'."""
    ser.write(serial.to_bytes(cmd.encode()))
    ser.write(serial.to_bytes(query.encode()))
    response = ser.readline().decode('UTF-8')
    print('  CAT response:', response, '. Expected:', cmd)
    if (cmd == response):
        print('  Result: PASS')
    else:
        print('  Result: FAIL')
        globalpass = False

def checkcatq(query, expected):
    """Like checkcat() but no preceding set command."""
    ser.write(serial.to_bytes(query.encode()))
    response = ser.readline().decode('UTF-8')
    print('  CAT response:', response, '. Expected:', expected)
    if (expected == response):
        print('  Result: PASS')
    else:
        print('  Result: FAIL')
        globalfail = True

#comport = 'COM3'
#comport = 'COM10'
comport = 'COM11'

globalpass = True               # Unless proven otherwise

# Try to load serial library and initialize serial port
try:
    import serial
    #ser = serial.Serial(port=comport, baudrate=9600, timeout=1)
    ser = serial.Serial(port=comport, baudrate=115200, timeout=1)
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

freq = 14.074e6
print('FA COMMAND')

sercmd = 'FA%09d;' % (int(freq))
checkcat(sercmd, 'FA;', sercmd)

print('TX COMMAND')
checkcat('TX1;', 'TX;', 'TX1;')
checkcat('TX0;', 'TX;', 'TX0;')

print('AI COMMAND')
checkcat('AI1;', 'AI;', 'AI1;')
checkcat('AI0;', 'AI;', 'AI0;')

print('ID COMMAND')
checkcatq('ID;', '0650;')

print('MD COMMAND')
checkcatq('MD0;', 'MD0C;')

print('SH COMMAND')
checkcatq('SH0;', 'SH0000;')

print('NA COMMAND')
checkcatq('NA0;', 'NA00;')

print('NA COMMAND')
checkcatq('IF;', 'IF001014074000+000000C00000;')

print('ST COMMAND')
checkcat('ST1;', 'ST;', 'ST1;')
checkcat('ST0;', 'ST;', 'ST0;')

ser.close()
print('\nOverall CAT test result: ', end='')
if (globalpass):
    print('PASS')
else:
    print('FAIL')
    
