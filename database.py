import aiosqlite
import logging

DB_FILE = "sensors.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                mac_address TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                min_temp REAL,
                max_temp REAL,
                min_hum REAL,
                max_hum REAL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                mac_address TEXT,
                temp_f REAL,
                humidity REAL,
                FOREIGN KEY (mac_address) REFERENCES devices(mac_address)
            )
        ''')
        await db.commit()
        logging.info("Database initialized.")

async def get_all_devices():
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM devices') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_device(mac_address: str):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM devices WHERE mac_address = ?', (mac_address,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def add_or_update_device(mac_address: str, name: str, min_temp: float = None, max_temp: float = None, min_hum: float = None, max_hum: float = None):
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute('''
                INSERT INTO devices (mac_address, name, min_temp, max_temp, min_hum, max_hum)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(mac_address) DO UPDATE SET
                    name=excluded.name,
                    min_temp=excluded.min_temp,
                    max_temp=excluded.max_temp,
                    min_hum=excluded.min_hum,
                    max_hum=excluded.max_hum
            ''', (mac_address, name, min_temp, max_temp, min_hum, max_hum))
            await db.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating device {mac_address}: {e}")
            return False

async def remove_device(mac_address: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM devices WHERE mac_address = ?', (mac_address,))
        await db.execute('DELETE FROM measurements WHERE mac_address = ?', (mac_address,))
        await db.commit()

async def log_measurement(mac_address: str, temp_f: float, humidity: float):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            INSERT INTO measurements (mac_address, temp_f, humidity)
            VALUES (?, ?, ?)
        ''', (mac_address, temp_f, humidity))
        await db.commit()

async def get_latest_measurements(limit: int = 100):
     async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT m.timestamp, m.mac_address, d.name, m.temp_f, m.humidity
            FROM measurements m
            LEFT JOIN devices d ON m.mac_address = d.mac_address
            ORDER BY m.timestamp DESC LIMIT ?
        ''', (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
