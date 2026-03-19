import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from config import PORT, DEBUG_MODE
import database
import scanner

logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.init_db()
    scanner_task = asyncio.create_task(scanner.start_scanner())
    yield
    # Shutdown
    scanner_task.cancel()

app = FastAPI(title="Sensing API", lifespan=lifespan)

class DeviceConfig(BaseModel):
    mac_address: str
    name: str
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    min_hum: Optional[float] = None
    max_hum: Optional[float] = None

@app.get("/api/devices")
async def api_get_devices():
    devices = await database.get_all_devices()
    cache = {d['mac_address']: d for d in scanner.get_discovered_cache()}
    
    for d in devices:
        c = cache.get(d['mac_address'])
        if c:
            d['current_temp_f'] = c['temp_f']
            d['current_humidity'] = c['humidity']
            d['last_seen'] = c['timestamp']
        else:
            d['current_temp_f'] = None
            d['current_humidity'] = None
            d['last_seen'] = None
    return devices

@app.post("/api/devices")
async def api_add_device(device: DeviceConfig):
    success = await database.add_or_update_device(
        device.mac_address, device.name, 
        device.min_temp, device.max_temp, 
        device.min_hum, device.max_hum
    )
    return {"success": success}

@app.put("/api/devices/{mac_address}")
async def api_update_device(mac_address: str, device: DeviceConfig):
    success = await database.add_or_update_device(
        mac_address, device.name, 
        device.min_temp, device.max_temp, 
        device.min_hum, device.max_hum
    )
    return {"success": success}

@app.delete("/api/devices/{mac_address}")
async def api_delete_device(mac_address: str):
    await database.remove_device(mac_address)
    return {"success": True}

@app.get("/api/discovered")
async def api_get_discovered():
    """Returns devices seen recently that are NOT registered"""
    registered = await database.get_all_devices()
    reg_macs = {d['mac_address'] for d in registered}
    
    discovered = scanner.get_discovered_cache()
    # filter out registered
    unregistered = [d for d in discovered if d['mac_address'] not in reg_macs]
    # sort by timestamp descending
    unregistered.sort(key=lambda x: x['timestamp'], reverse=True)
    return unregistered

@app.get("/api/history")
async def api_get_history(limit: int = 100):
    return await database.get_latest_measurements(limit)

# Ensure static folder exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # If index.html doesn't exist, just return a dummy message until frontend is built
    if not os.path.exists("static/index.html"):
        return {"message": "Frontend not built yet."}
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG_MODE)
