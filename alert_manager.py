import aiohttp
import logging
import config

async def send_alert(message: str, title: str = "Sensor Alert"):
    topic_val = config.NTFY_TOPIC.strip()
    if topic_val.startswith("http://") or topic_val.startswith("https://"):
        url = topic_val
    elif "/" in topic_val:
        url = f"https://{topic_val}"
    else:
        url = f"https://ntfy.sh/{topic_val}"

    logging.info(f"Attempting to send ntfy alert to URL: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Title": title,
                "Priority": "high",
                "Tags": "warning,thermometer"
            }
            async with session.post(url, data=message.encode('utf-8'), headers=headers) as resp:
                if config.DEBUG_MODE:
                    logging.info(f"Alert sent to {url}. Response: {resp.status}")
                if resp.status != 200:
                    logging.error(f"Failed to send alert via ntfy. HTTP {resp.status}")
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")

async def check_thresholds_and_alert(device, temp_f, humidity):
    """
    Checks if a measurement is outside the device's thresholds and sends an alert.
    """
    alerts = []
    
    # Check Temperature
    if device.get('min_temp') is not None and temp_f < device['min_temp']:
        alerts.append(f"Temperature is too low: {temp_f:.1f}°F (Min: {device['min_temp']:.1f}°F)")
    if device.get('max_temp') is not None and temp_f > device['max_temp']:
        alerts.append(f"Temperature is too high: {temp_f:.1f}°F (Max: {device['max_temp']:.1f}°F)")
        
    # Check Humidity
    if device.get('min_hum') is not None and humidity < device['min_hum']:
        alerts.append(f"Humidity is too low: {humidity:.1f}% (Min: {device['min_hum']:.1f}%)")
    if device.get('max_hum') is not None and humidity > device['max_hum']:
        alerts.append(f"Humidity is too high: {humidity:.1f}% (Max: {device['max_hum']:.1f}%)")
        
    if alerts:
        device_name = device.get('name', device.get('mac_address'))
        message = f"Alerts for {device_name}:\n" + "\n".join(alerts)
        await send_alert(message, title=f"Sensor Alert: {device_name}")
        logging.warning(message)
