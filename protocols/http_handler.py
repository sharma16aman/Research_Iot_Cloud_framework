# protocols/http_handler.py
import time, json
from typing import Optional

try:
    import requests
except Exception:
    requests = None  # will simulate if missing

class HTTPHandler:
    """
    Minimal HTTP poster with built-in metrics.
    - If 'requests' is missing, simulates a small network latency.
    """
    def __init__(self, endpoint="http://localhost:8000/data", timeout=2.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.messages = 0
        self.bytes_sent = 0
        self.latencies = []

    def post(self, payload: dict):
        t0 = time.perf_counter()
        body = json.dumps(payload).encode("utf-8")
        if requests:
            try:
                requests.post(self.endpoint, data=body, headers={"Content-Type":"application/json"}, timeout=self.timeout)
            except Exception:
                # fall back to simulated delay
                time.sleep(0.01)
        else:
            time.sleep(0.01)
        t1 = time.perf_counter()
        self.messages += 1
        self.bytes_sent += len(body)
        self.latencies.append(t1 - t0)

    def stats(self):
        lat = self.latencies
        avg = sum(lat)/len(lat) if lat else 0.0
        return {
            "messages": self.messages,
            "bytes_sent": self.bytes_sent,
            "avg_latency_s": avg,
        }
