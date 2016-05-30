import time
from calendar import timegm
from datetime import datetime
import re
import math
from stetl.util import Util

log = Util.get_log("SensorConverters")

# According to CityGIS the units are defined as follows. ::
#
# S.TemperatureUnit		milliKelvin
# S.TemperatureAmbient	milliKelvin
# S.Humidity				%mRH
# S.LightsensorTop		Lux
# S.LightsensorBottom		Lux
# S.Barometer				Pascal
# S.Altimeter				Meter
# S.CO					ppb
# S.NO2					ppb
# S.AcceleroX				2 ~ +2G (0x200 = midscale)
# S.AcceleroY				2 ~ +2G (0x200 = midscale)
# S.AcceleroZ				2 ~ +2G (0x200 = midscale)
# S.LightsensorRed		Lux
# S.LightsensorGreen		Lux
# S.LightsensorBlue		Lux
# S.RGBColor				8 bit R, 8 bit G, 8 bit B
# S.BottomSwitches		?
# S.O3					ppb
# S.CO2					ppb
# v3: S.ExternalTemp		milliKelvin
# v3: S.COResistance		Ohm
# v3: S.No2Resistance		Ohm
# v3: S.O3Resistance		Ohm
# S.AudioMinus5			Octave -5 in dB(A)
# S.AudioMinus4			Octave -4 in dB(A)
# S.AudioMinus3			Octave -3 in dB(A)
# S.AudioMinus2			Octave -2 in dB(A)
# S.AudioMinus1			Octave -1 in dB(A)
# S.Audio0				Octave 0 in dB(A)
# S.AudioPlus1			Octave +1 in dB(A)
# S.AudioPlus2			Octave +2 in dB(A)
# S.AudioPlus3			Octave +3 in dB(A)
# S.AudioPlus4			Octave +4 in dB(A)
# S.AudioPlus5			Octave +5 in dB(A)
# S.AudioPlus6			Octave +6 in dB(A)
# S.AudioPlus7			Octave +7 in dB(A)
# S.AudioPlus8			Octave +8 in dB(A)
# S.AudioPlus9			Octave +9 in dB(A)
# S.AudioPlus10			Octave +10 in dB(A)
# S.SatInfo
# S.Latitude				nibbles: n1:0=East/North, 8=West/South; n2&n3: whole degrees (0-180); n4-n8: degree fraction (max 999999)
# S.Longitude				nibbles: n1:0=East/North, 8=West/South; n2&n3: whole degrees (0-180); n4-n8: degree fraction (max 999999)
#
# P.Powerstate					Power State
# P.BatteryVoltage				Battery Voltage (milliVolts)
# P.BatteryTemperature			Battery Temperature (milliKelvin)
# P.BatteryGauge					Get Battery Gauge, BFFF = Battery full, 1FFF = Battery fail, 0000 = No Battery Installed
# P.MuxStatus						Mux Status (0-7=channel,F=inhibited)
# P.ErrorStatus					Error Status (0=OK)
# P.BaseTimer						BaseTimer (seconds)
# P.SessionUptime					Session Uptime (seconds)
# P.TotalUptime					Total Uptime (minutes)
# v3: P.COHeaterMode				CO heater mode
# P.COHeater						Powerstate CO heater (0/1)
# P.NO2Heater						Powerstate NO2 heater (0/1)
# P.O3Heater						Powerstate O3 heater (0/1)
# v3: P.CO2Heater					Powerstate CO2 heater (0/1)
# P.UnitSerialnumber				Serialnumber of unit
# P.TemporarilyEnableDebugLeds	Debug leds (0/1)
# P.TemporarilyEnableBaseTimer	Enable BaseTime (0/1)
# P.ControllerReset				WIFI reset
# P.FirmwareUpdate				Firmware update, reboot to bootloader
#
# Unknown at this moment (decimal):
# P.11
# P.16
# P.17
# P.18


# Conversion functions for raw values from Josene sensors

# Zie http://www.apis.ac.uk/unit-conversion
# ug/m3 = PPB * moleculair gewicht/moleculair volume
# waar molec vol = 22.41 * T/273 * 1013/P
#
# Typische waarden:
# Nitrogen dioxide 1 ppb = 1.91 ug/m3  bij 10C 1.98, bij 30C 1.85 --> 1.9
# Ozone 1 ppb = 2.0 ug/m3  bij 10C 2.1, bij 30C 1.93 --> 2.0
# Carbon monoxide 1 ppb = 1.16 ug/m3 bij 10C 1.2, bij 30C 1.1 --> 1.15
#
# Benzene 1 ppb = 3.24 ug/m3
# Sulphur dioxide 1 ppb = 2.66 ug/m3
# For now a crude approximation as the measurements themselves are also not very accurate
# For now a crude conversion (1 atm, 20C)
def ppb_to_ugm3(component, input):
    ppb_to_ugm3_factor = {'o3': 2.0, 'no2': 1.9, 'co': 1.15, 'co2': 1.8}
    if input == 0 or input > 1000000 or component not in ppb_to_ugm3_factor:
        return None

    return ppb_to_ugm3_factor[component] * float(input)


def ppb_co_to_ugm3(input, json_obj, name):
    return ppb_to_ugm3('co', input)


def ppb_co2_to_ugm3(input, json_obj, name):
    return ppb_to_ugm3('co2', input)


def ppb_co2_to_ppm(input, json_obj, name):
    return input/1000


def ppb_no2_to_ugm3(input, json_obj, name):
    return ppb_to_ugm3('no2', input)


def ppb_o3_to_ugm3(input, json_obj, name):
    return ppb_to_ugm3('o3', input)


def ohm_to_kohm(input, json_obj, name):
    return int(round(input/1000))


def convert_temperature(input, json_obj, name):
    if input == 0:
        return None

    tempC = int(round(float(input)/1000.0 - 273.1))
    if tempC > 100:
        return None

    return tempC


def convert_barometer(input, json_obj, name):
    result = float(input) / 100.0
    if result > 2000:
        return None
    return int(round(result))


def convert_humidity(input, json_obj, name):
    humPercent = int(round(float(input) / 1000.0))
    if humPercent > 100:
        return None
    return humPercent

# Lat or longitude conversion
# 8 nibbles:
# MSB                  LSB
# n1 n2 n3 n4 n5 n6 n7 n8
# n1: 0 of 8, 0=East/North, 8=West/South
# n2 en n3: whole degrees (0-180)
# n4-n8: fraction of degrees (max 999999)
def convert_coord(input, json_obj, name):
    sign = 1.0
    if input >> 28:
        sign = -1.0
    deg = float((input >> 20) & 255)
    dec = float(input & 1048575)

    result = (deg + dec / 1000000.0) * sign
    if result == 0.0:
        result = None
    return result

def convert_latitude(input, json_obj, name):
    res = convert_coord(input, json_obj, name)
    if res is not None and (res < -90.0 or res > 90.0):
        log.error('Invalid latitude %d' % res)
        return None
    return res

def convert_longitude(input, json_obj, name):
    res = convert_coord(input, json_obj, name)
    if res is not None and (res < -180.0 or res > 180.0):
        log.error('Invalid longitude %d' % res)
        return None
    return res

# https://aboutsimon.com/blog/2013/06/06/Datetime-hell-Time-zone-aware-to-UNIX-timestamp.html
def convert_timestamp(iso_str, json_obj, name):
    # iso_str : '2016-02-03T16:47:51.3844629Z'
    iso_str = iso_str.split('.')[0] + 'GMT'
    # timestamp = timegm(
    #         time.strptime(iso_str, '%Y-%m-%dT%H:%M:%SGMT')
    # )
    # print timestamp
    # print '-> %s' % datetime.utcfromtimestamp(timestamp).isoformat()
    return datetime.strptime(iso_str, '%Y-%m-%dT%H:%M:%SGMT')

def convert_none(value, json_obj, name):
    return value

# From https://www.teachengineering.org/view_activity.php?url=collection/nyu_/activities/nyu_noise/nyu_noise_activity1.xml
# level dB(A)
#  1     0-20  zero to quiet room
#  2     20-40 up to average residence
#  3     40-80 up to noisy class, alarm clock, police whistle
#  4     80-90 truck with muffler
#  5     90-up severe: pneumatic drill, artillery,
#
# Peter vd Voorn:
# Voor het categoriseren van de meetwaarden kunnen we het beste beginnen bij de 20 dB(A).
# De hoogte waarde zal 95 dB(A) zijn. Bijvoorbeeld een vogel van heel dichtbij.
# Je kunt dit nu gewoon lineair verdelen in 5 categorieen. Ieder 15 dB. Het betreft buiten meetwaarden.
# 20 fluister stil
# 35 rustige woonwijk in een stad
# 50 drukke woonwijk in een stad
# 65 wonen op korte afstand van het spoor
# 80 live optreden van een band aan het einde van het publieksdeel. Praten is mogelijk.
# 95 live optreden van een band midden op een plein. Praten is onmogelijk.
def calc_audio_level(db):
    levels = [20, 35, 50, 65, 80, 95]
    level_num = 1
    for i in range(0, len(levels)):
        if db > levels[i]:
            level_num = i + 1

    return level_num

# Converts audio var and populates virtual max value vars
# NB not used: now taking average of max values, see convert_audio_avg()
def convert_audio_max(value, json_obj, name):
    # For each audio observation:
    # decode into 3 bands (0,1,2)
    # determine max of these  bands
    # determine if this is greater than current t_audiomax
    # determine audio_level (1-5) from current t_audiomax

    # Extract values for bands 0-2
    bands = [value & 255, (value >> 8) & 255, (value >> 16) & 255]

    band_max = 0
    band_num = 0
    for i in range(0, len(bands)):
        if band_max < bands[i] < 255:
            band_max = bands[i]
            band_num = i

    if band_max == 0:
        return None

    # Assign band max value to virtual sensors if these are not yet present
    # or band_max value greater than current max
    if 't_audiomax' not in json_obj or band_max > json_obj['t_audiomax']:
        json_obj['t_audiomax'] = band_max
        # Determine octave nr from var name
        json_obj['t_audiomax_octave'] = int(re.findall(r'\d+', name)[0])
        json_obj['t_audiomax_octband'] = band_num
        json_obj['t_audiolevel'] = calc_audio_level(band_max)


    return band_max

# Converts audio var and populates average
# Logaritmisch optellen van de waarden per frequentieband voor het verkrijgen van de totaalwaarde:
#
# 10^(waarde/10)
# En dat voor de waarden van alle frequenties en bij elkaar tellen.
# Daar de log van en x10
#
# Normaal tellen wij op van 31,5 Hz tot 8 kHz. In totaal 9 oktaafanden. 31,5  63  125  250  500  1000  2000  4000 en 8000 Hz
#
# Of 27   1/3 oktaafbanden: 25, 31.5, 40, 50, 63, 80, enz
def convert_audio_avg(value, json_obj, name):
    # For each audio observation:
    # decode into 3 bands (0,1,2)
    # determine average of these  bands
    # determine overall average of all average bands

    # Extract values for bands 0-2
    bands = [float(value & 255), float((value >> 8) & 255), float((value >> 16) & 255)]

    # determine average of these 3 bands
    band_avg = 0
    band_cnt = 0
    for i in range(0, len(bands)):
        band_val  = bands[i]
        # outliers
        if band_val < 1 or band_val > 150:
            continue
        band_cnt += 1
        
        # convert band value Decibel to Bel and then get "real" value (power 10)
        band_avg += math.pow(10, band_val / 10)
        # print '%s : band[%d]=%f band_avg=%f' %(name, i, bands[i], band_avg)

    if band_cnt == 0:
        return None
    
    # Take average of "real" values and convert back to Bel via log10 and Decibel via *10
    band_avg = math.log10(band_avg / float(band_cnt)) * 10.0

    # print '%s : avg=%d' %(name, band_avg)

    if band_avg < 1 or band_avg > 150:
        return None

    # Initialize  average value to first average calc
    if 'v_audioavg' not in json_obj:
        json_obj['v_audioavg'] = band_avg
        json_obj['v_audioavg_total'] = math.pow(10, band_avg / 10)
        json_obj['v_audioavg_cnt'] = 1
    else:
        json_obj['v_audioavg_cnt'] += 1
        json_obj['v_audioavg_total'] += math.pow(10, band_avg / 10)
        json_obj['v_audioavg'] = int(round(math.log10(json_obj['v_audioavg_total'] / json_obj['v_audioavg_cnt']) * 10.0))

    # Determine octave nr from var name
    json_obj['v_audiolevel'] = calc_audio_level(json_obj['v_audioavg'])
    print 'Unit %s - %s band_db=%f avg_db=%d level=%d' % (json_obj['p_unitserialnumber'], name, band_avg, json_obj['v_audioavg'], json_obj['v_audiolevel'] )
    return band_avg

CONVERTERS = {
    's_co': ppb_co_to_ugm3,
    's_co2': ppb_co2_to_ppm,
    's_no2': ppb_no2_to_ugm3,
    's_o3': ppb_o3_to_ugm3,
    's_coresistance': ohm_to_kohm,
    's_no2resistance': ohm_to_kohm,
    's_o3resistance': ohm_to_kohm,
    's_temperatureambient': convert_temperature,
    's_barometer': convert_barometer,
    's_humidity': convert_humidity,
    's_latitude': convert_latitude,
    's_longitude': convert_longitude,
    'time': convert_timestamp,
    't_audio0': convert_audio_max,
    't_audioplus1': convert_audio_max,
    't_audioplus2': convert_audio_max,
    't_audioplus3': convert_audio_max,
    't_audioplus4': convert_audio_max,
    't_audioplus5': convert_audio_max,
    't_audioplus6': convert_audio_max,
    't_audioplus7': convert_audio_max,
    't_audioplus8': convert_audio_max,
    't_audioplus9': convert_audio_max,
    't_audioplus10': convert_audio_max,
    'v_audio0': convert_audio_avg,
    'v_audioplus1': convert_audio_avg,
    'v_audioplus2': convert_audio_avg,
    'v_audioplus3': convert_audio_avg,
    'v_audioplus4': convert_audio_avg,
    'v_audioplus5': convert_audio_avg,
    'v_audioplus6': convert_audio_avg,
    'v_audioplus7': convert_audio_avg,
    'v_audioplus8': convert_audio_avg,
    'v_audioplus9': convert_audio_avg,
    'v_audioplus10': convert_audio_avg,
    # These are assigned already in t_audioplusN conversions
    't_audiomax': convert_none,
    't_audiomax_octave': convert_none,
    't_audiomax_octband': convert_none,
    't_audiolevel': convert_none,
    # These are assigned already in t_audioplusN conversions
     'v_audioavg': convert_none,
     'v_audioavg_octave': convert_none,
     'v_audioavg_octband': convert_none,
     'v_audiolevel': convert_none
}

def convert(json_obj, name):
    if name not in CONVERTERS:
        log.error('Cannot find converter for %s' % name)
        return None

    return CONVERTERS[name](json_obj[name], json_obj, name)