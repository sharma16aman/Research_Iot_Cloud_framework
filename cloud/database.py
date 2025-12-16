# cloud/database.py
import os, sqlite3
from typing import Iterable, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sensor_id INTEGER,
  ts TEXT,
  temperature REAL,
  humidity REAL,
  pressure REAL
);
"""

class Database:
    """
    Tiny SQLite wrapper for demo/storage.
    """
    def __init__(self, path: str = "results/cloud_data.db"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def insert(self, sensor_id: int, ts: str, temperature, humidity, pressure):
        self.conn.execute(
            "INSERT INTO readings(sensor_id, ts, temperature, humidity, pressure) VALUES (?,?,?,?,?)",
            (sensor_id, ts, temperature, humidity, pressure)
        )
        self.conn.commit()

    def bulk_insert(self, rows: Iterable[Tuple[int,str,float,float,float]]):
        self.conn.executemany(
            "INSERT INTO readings(sensor_id, ts, temperature, humidity, pressure) VALUES (?,?,?,?,?)",
            rows
        )
        self.conn.commit()

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM readings")
        return int(cur.fetchone()[0])

    def close(self):
        self.conn.close()
