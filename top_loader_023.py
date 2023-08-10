import time
import pyvisa as visa

import numpy as np
from IPython.display import clear_output


def Pt1000_cal(r):
    if r < 25 or r > 1400:
        return 0
    coeffs = [
        -469.544790033,
        2142.429105073,
        -4278.355519358,
        4917.129912473,
        -3583.140137551,
        1717.059717072,
        -541.269035711,
        108.277676198,
        -12.478784052,
        0.631579503,
    ]
    return np.power(10, np.polynomial.polynomial.polyval(np.log10(r), coeffs))

def RuO2_10k_cal(r):
    r = r / 1000
    if r < 10.8 or r > 320:
        return 0
    coeffs = [
        6909.149278051,
        -38314.105969326,
        93795.121719782,
        -132881.190697614,
        120024.664196962,
        -71674.983797385,
        28300.34446649,
        -7125.704599868,
        1038.446472548,
        -66.75479913,
    ]
    return np.power(10, np.polynomial.polynomial.polyval(np.log10(r), coeffs)) / 1000

def RuO2_1k5_cal(r):
    if r < 2000 or r > 17000:
        return 0
    coeffs = [
        -109406225.453069,
        264570367.275206,
        -284130767.924156,
        177858095.325872,
        -71516430.0477208,
        19156216.6038666,
        -3418108.54721648,
        391778.170838493,
        -26174.3212975398,
        776.590777082747,
    ]
    return np.power(10, np.polynomial.polynomial.polyval(np.log10(r), coeffs)) / 1000

def TT1304_cal(r):
    if r < 1600 or r > 75000:
        return 0
    coeffs = [
        -85991.97200244224,
       170101.13604422542,
        -146816.39437206375,
        72250.85152375244,
        -22180.90228857295,
        4351.18582667978,
        -532.76537613975,
        37.23402757752,
        -1.13741001238,
        0,      
    ]
    return np.power(10, np.polynomial.polynomial.polyval(np.log10(r), coeffs)) / 1000


def S0927_cal(r):
    if r < 600 or r > 100000:
        return 0
    coeffs = [
        340.0066359697,
        -428.9444332334,
        219.360664071,
        -56.2474119288,
        7.2087047046,
        -0.3691158405,
    ]
    return np.power(10, np.polynomial.polynomial.polyval(np.log10(r), coeffs)) / 1000

_SENSORS = [
    ('3K_low', RuO2_10k_cal),      # 0
    ('Still', RuO2_10k_cal),       # 1
    ('50mK', RuO2_1k5_cal),        # 2
    ('MixingCh_low', TT1304_cal),  # 3
    ('MixingCh_high', Pt1000_cal), # 4
    ('Magnet', RuO2_10k_cal),      # 5
]

# _SENSORS = [
#     ('3K_high', RuO2_1k5_cal),      # 0
#     ('Still', RuO2_1k5_cal),       # 1
#     ('50mK', RuO2_1k5_cal),        # 2
#     ('MixingCh_low', TT1304_cal),  # 3
#     ('MixingCh_high', Pt1000_cal), # 4
#     ('Magnet', RuO2_1k5_cal),      # 5
# ]

def FridgeScan(avs):
    # Wait for it to finish whatever it was doing.
    while avs.query('*OPC?').strip() != '1':
        time.sleep(1)
    # Sweep settings.
    avs.write(f'REM 1;FCH 0;LCH 5;SCI 600;ETC 0;TCP 30;ARN 1;REM 0')
    for i in [int(0),int(1),int(2),int(3),int(4),int(5)]:
        avs.write(f'REM 1;SCP {i};EXC 3;SDY 5;CNT 10;REM 0')
    # Start the sweep and wait for it to complete.
    avs.write('REM 1;SCN 0;REM 0')
    while avs.query('*OPC?').strip() != '1':
        time.sleep(1)
    # Read out the results.
    for i in [int(0),int(1),int(2),int(3),int(4),int(5)]:
        avg, std = avs.query(f'REM 1;SCR {i};AVE?;STD?;REM 0').strip().split(';')
        avg = float(avg.split(' ')[-1])
        std = float(std.split(' ')[-1])
        yield i, avg, std


def print_stuff():
    channel = int(avs.query('MUX?').strip().split(' ')[1])
    
    avs.write('ADC')
    while int(avs.query('*OPC?').strip()) != 1:
        time.sleep(0.1)
    res = float(avs.query('RES?').strip().split(' ')[2])
    
    if int(avs.query('OVL?').strip().split(' ')[1]) != 0:
        return
    
    name, temp_cal = _SENSORS[channel]
    temp = temp_cal(res)
    print(f'Channel {channel}\t{name}\tResistance {res} Ω\tTemperature {temp:.4f} K')

    
def scan_fridge(delay=120):
    while True:
        rm = visa.ResourceManager()
        t = int(time.time())
        t2= time.ctime(t)
        path = "/Users/dgglab/Desktop/TempDataStorage/"
        try:
            print("SCANNING")
            with rm.open_resource('GPIB0::21::INSTR') as avs: # GPIB0::21 should be fridge side AVS
                avs.clear()
                print('ID:', avs.query('*IDN?').strip())
                values = list(FridgeScan(avs))
                print(values)
        except Exception as e:
            print(e)
            time.sleep(10)
            continue
        clear_output(wait=True)
        print(time.strftime('%l:%M%p %Z on %b %d, %Y'))
        for chan, avg, std in values:
            name = _SENSORS[chan][0]
            temp = _SENSORS[chan][1](avg)
            print(f'{name:>15}\t{avg:>10.2f} Ω\t{temp:>10.5f} K')
            errs = []
            with open(path+f'Fridge_{name}.txt', "a") as myfile: # Ensure File name matches AVS
                myfile.write(f'{t}\t{t2}\t{avg:>10.2f}\t{temp:>10.5f}\tIdle\t\n')
                myfile.close()
        print(f'Scanned in {time.time() - t:.1f} seconds.')
        for chan, err in errs:
            print(f'{chan}: {err}')
        time.sleep(delay)

