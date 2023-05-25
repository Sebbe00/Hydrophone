import utime
from machine import I2C, Pin, reset, deepsleep
import network
import time
import json
import urequests
 
SSID = "ZTE_D656BE"
PASSWORD = "22896806"
 
wlan = network.WLAN(network.STA_IF)
if not wlan.active():
    wlan.active(True)

 
def establish_wifi_connection(ssid, password, max_retries=50, retry_delay=5):
    retry_count = 1
    while not wlan.isconnected() and retry_count < max_retries:
        try:
            print ('Trying to connect to WiFi...' , 'Attempt:' , retry_count)
            wlan.connect(ssid, password)
            retry_count += 1
            utime.sleep(retry_delay)
        except Exception as e:
            print("Error occurred while connecting to Wi-Fi:", e)
            retry_count += 1
            utime.sleep(retry_delay)
 
    if not wlan.isconnected() and retry_count >= max_retries:
        print("Failed to establish Wi-Fi connection after maximum retries.")
        machine.deepsleep()
 
# Call the function to establish Wi-Fi connection
establish_wifi_connection(SSID, PASSWORD)
 
# Constants
HYDROPHONE_ADDRESS = 72
HYDROPHONE_SENSITIVITY_DB = 4  # var 4 tidigare
HYDROPHONE_FREQ_RANGE_HZ = (20, 4500)
 
 
# Set up I2C connection to hydrophone sensor
i2c = I2C(1, freq=400000, scl=Pin(15), sda=Pin(14))
 
def read_config():
    i2c.writeto(HYDROPHONE_ADDRESS, bytearray([1]))
    response = i2c.readfrom(HYDROPHONE_ADDRESS, 2)
    return response[0] << 8 | response[1]
 
def read_value():
    i2c.writeto(HYDROPHONE_ADDRESS, bytearray([0]))
    response = i2c.readfrom(HYDROPHONE_ADDRESS, 2)
    config = read_config()
    config &= ~(7 << 12) & ~(7 << 9)
    config |= (HYDROPHONE_SENSITIVITY_DB << 12) | (1 << 9) | (1 << 15)
    config_bytes = [int(config >> i & 0xff) for i in (8, 0)]
    i2c.writeto(HYDROPHONE_ADDRESS, bytearray([1] + config_bytes))
    return response[0] << 8 | response[1]
 
def val_to_voltage(val, max_val=65536, voltage_ref=1.024):
    return (val / max_val) * voltage_ref
 
def voltage_to_db(voltage):
    if voltage == 0:
        return 14  # return 14 dB at 0 volts
    else:
        # calculate dB for other voltages
        reference_voltage = 0.08  # voltage at 14 dB
        max_voltage = 1.024  # voltage at 120 dB
        min_db = 14
        max_db = 120
        slope = (max_db - min_db) / (max_voltage - reference_voltage)
        db = min_db + slope * (voltage - reference_voltage)
        return db
 
def push_data(data):
    url = "https://citizensailors.wixsite.com/citizen-sailors/_functions/Measurements"
    headers = {"Content-Type": "application/json"}
    response = urequests.post(url, headers=headers, data=json.dumps(data))
 
    if response.status_code >= 200 and response.status_code < 300:
        print("Request successful")
    else:
        print("Request failed with status code", response.status_code)
        print("Error message:", response.text)
 
    response.close()  # Clear response object to free up memory
 
def restart_program():
    # Delay before restarting (if needed)
    utime.sleep(5)
    # Reset the microcontroller or board
    reset()
 
data = []
start_time = utime.time()
 
while True:
    try:
        hydrophone_reading = read_value()
        voltage = val_to_voltage(hydrophone_reading)
        db = voltage_to_db(voltage)
        print(f"ADC Value: {hydrophone_reading}, Voltage: {voltage:.3f} V, dB: {db:.2f}")
        new_measurement = {'Recording': db}
        data.append(new_measurement)
        utime.sleep(0.25)  # Pause between each loop (seconds)
 
        if utime.time() - start_time >= 45:  # 10 seconds have passed
            push_data(data)
            data = []  # Clear the data list
            restart_program()
 
    except Exception as e:
        print(f"Error occurred: {e}")
        restart_program()