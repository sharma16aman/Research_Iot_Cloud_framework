from typing import Dict, Iterable, Tuple
from cloud.database import Database

class Receiver:
    """
    In-process receiver that writes messages to SQLite.
    Serialization-agnostic by design.
    """
    def __init__(self, db_path: str = "results/cloud_data.db"):
        self.db = Database(db_path)

    def handle_message(self, msg: Dict):
        self.db.insert(
            int(msg.get("sensor_id", 0)),
            str(msg.get("ts")),
            msg.get("temperature"),
            msg.get("humidity"),
            msg.get("pressure"),
        )

    def handle_bulk(self, rows: Iterable[Tuple[int,str,float,float,float]]):
        self.db.bulk_insert(rows)

    def stats(self) -> int:
        return self.db.count()

    def close(self):
        self.db.close()
