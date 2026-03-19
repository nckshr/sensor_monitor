import asyncio
import logging
from bleak import BleakScanner

# --- CONFIGURATION ---
ALERT_MIN_TEMP_F = -50.0 
DEBUG_MODE = False  # Set to True if you see issues again

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def c_to_f(celsius):
    return (celsius * 9/5) + 32

def send_alert(device_name, temp_f, humidity):
    logging.warning(f"⚠️ ALERT! {device_name} is low: {temp_f:.1f}°F (Humidity: {humidity}%)")

def decode_govee_h5075(mfg_data):
    """ Decodes Govee H5075 (0xEC88) """
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
    """
    Decodes ThermoPro TP357 by reconstructing the full packet
    from the Manufacturer ID + Payload.
    """
    try:
        # Reconstruct the full byte stream (ID is Little Endian)
        # ID: 0xEFC2 -> Bytes: C2 EF
        id_bytes = mfg_id.to_bytes(2, byteorder='little')
        full_data = id_bytes + mfg_data
        
        # Structure for your TP357:
        # [0]: Type/Flag (C2)
        # [1]: Temp Low  (EF)
        # [2]: Temp High (00)
        # [5]: Humidity  (2C)
        
        if len(full_data) < 6: return None, None

        # 1. Parse Temp (Bytes 1-2, Little Endian)
        temp_raw = full_data[1] + (full_data[2] << 8)
        
        # Handle Negative Temps (Signed Short)
        if temp_raw > 32767:
            temp_raw -= 65536
            
        temp_c = temp_raw / 10.0
        
        # 2. Parse Humidity (Byte 5)
        humidity = full_data[5]

        # Sanity Check
        if temp_c > 80 or temp_c < -40 or humidity > 100:
            return None, None
            
        return temp_c, humidity

    except Exception as e:
        if DEBUG_MODE: logging.error(f"TP Decode Error: {e}")
        return None, None

async def detection_callback(device, advertisement_data):
    dev_name = device.name or "Unknown"
    
    # --- GOVEE ---
    if "GVH5075" in dev_name:
        if 0xEC88 in advertisement_data.manufacturer_data:
            data = advertisement_data.manufacturer_data[0xEC88]
            temp_c, hum = decode_govee_h5075(data)
            if temp_c is not None:
                temp_f = c_to_f(temp_c)
                logging.info(f"✅ Govee Detected: {temp_f:.1f}°F | {hum}%")
                if temp_f < ALERT_MIN_TEMP_F: send_alert("Govee", temp_f, hum)

    # --- THERMOPRO ---
    elif "TP35" in dev_name or "ThermoPro" in dev_name:
        # ThermoPro puts data in the ID, so we loop through all IDs found
        for mfg_id, data in advertisement_data.manufacturer_data.items():
            
            if DEBUG_MODE:
                logging.info(f"🔍 TP Raw: ID={hex(mfg_id)} Data={data.hex()}")

            temp_c, hum = decode_thermopro_tp357(mfg_id, data)
            
            if temp_c is not None:
                temp_f = c_to_f(temp_c)
                logging.info(f"✅ ThermoPro Detected: {temp_f:.1f}°F | {hum}%")
                if temp_f < ALERT_MIN_TEMP_F: send_alert("ThermoPro", temp_f, hum)
                break 

async def main():
    logging.info("📡 Scanning for Govee and ThermoPro devices...")
    scanner = BleakScanner(detection_callback)
    await scanner.start()
    while True:
        await asyncio.sleep(5.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping...")
