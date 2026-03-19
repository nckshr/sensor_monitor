import asyncio
import logging
import time
from bleak import BleakScanner
from config import MONITOR_FREQUENCY_MINUTES, DEBUG_MODE
import database
import alert_manager

# Cache the latest reading for any seen device: {mac_address: {"name": str, "temp_f": float, "humidity": float, "timestamp": float}}
discovered_devices_cache = {}

# Track when we last logged/alerted for a registered device: {mac_address: timestamp_float}
last_logged_time = {}

def c_to_f(celsius):
    return (celsius * 9/5) + 32

def decode_govee_h5075(mfg_data):
    if len(mfg_data) < 6: return None, None
    hex_val = int.from_bytes(mfg_data[1:4], byteorder='big')
    if hex_val == 0: hex_val = int.from_bytes(mfg_data[3:6], byteorder='big')

    is_negative = False
    if hex_val & 0x800000:
        is_negative = True
        hex_val = hex_val ^ 0x800000

    humidity = (hex_val % 1000) / 10.0
    temp_c = (hex_val - (hex_val % 1000)) / 10000.0
    if is_negative: temp_c = -temp_c
    return temp_c, humidity

def decode_thermopro_tp357(mfg_id, mfg_data):
    try:
        id_bytes = mfg_id.to_bytes(2, byteorder='little')
        full_data = id_bytes + mfg_data
        if len(full_data) < 6: return None, None
        
        temp_raw = full_data[1] + (full_data[2] << 8)
        if temp_raw > 32767:
            temp_raw -= 65536
            
        temp_c = temp_raw / 10.0
        humidity = full_data[5]

        if temp_c > 80 or temp_c < -40 or humidity > 100:
            return None, None
            
        return temp_c, humidity
    except Exception as e:
        if DEBUG_MODE: logging.error(f"TP Decode Error: {e}")
        return None, None

async def handle_measurement(mac_address, name, temp_f, humidity):
    now = time.time()
    
    # Update discovered cache
    discovered_devices_cache[mac_address] = {
        "mac_address": mac_address,
        "name": name,
        "temp_f": round(temp_f, 1),
        "humidity": round(humidity, 1),
        "timestamp": now
    }
    
    # Check if this is a registered device
    registered_device = await database.get_device(mac_address)
    if not registered_device:
        return

    # Throttle logging and alerting
    last_time = last_logged_time.get(mac_address, 0)
    if now - last_time >= (MONITOR_FREQUENCY_MINUTES * 60):
        # Time to log and check alerts
        if DEBUG_MODE:
            logging.info(f"Logging data for {name} ({mac_address}): {temp_f:.1f}°F, {humidity}%")
        await database.log_measurement(mac_address, temp_f, humidity)
        await alert_manager.check_thresholds_and_alert(registered_device, temp_f, humidity)
        last_logged_time[mac_address] = now

async def detection_callback(device, advertisement_data):
    mac_address = device.address or "UnknownMAC"
    dev_name = device.name or "Unknown"
    
    if "GVH5075" in dev_name:
        if 0xEC88 in advertisement_data.manufacturer_data:
            data = advertisement_data.manufacturer_data[0xEC88]
            temp_c, hum = decode_govee_h5075(data)
            if temp_c is not None:
                temp_f = c_to_f(temp_c)
                await handle_measurement(mac_address, f"Govee {mac_address[-5:]}", temp_f, hum)

    elif "TP35" in dev_name or "ThermoPro" in dev_name:
        for mfg_id, data in advertisement_data.manufacturer_data.items():
            temp_c, hum = decode_thermopro_tp357(mfg_id, data)
            if temp_c is not None:
                temp_f = c_to_f(temp_c)
                await handle_measurement(mac_address, f"ThermoPro {mac_address[-5:]}", temp_f, hum)
                break 

async def start_scanner():
    logging.info("📡 Starting BLE Scanner...")
    try:
        scanner = BleakScanner(detection_callback)
        await scanner.start()
        # Keep running
        while True:
            await asyncio.sleep(5.0)
    except Exception as e:
        logging.error(f"Scanner exception: {e}")

def get_discovered_cache():
    return list(discovered_devices_cache.values())
