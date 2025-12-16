# protocols/mqtt_handler.py
import time, json
from typing import Optional, Any, TYPE_CHECKING

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None  # runtime fallback if library missing

if TYPE_CHECKING:
    from paho.mqtt.client import Client  # for static type checkers only
else:
    Client = Any  # at runtime, we don't need the actual type

class MQTTHandler:
    """
    Minimal MQTT publisher with built-in metrics.
    - If paho-mqtt is missing, uses a latency simulator.
    """
    def __init__(self, broker="localhost", port=1883, topic="iot/data", qos: int = 0):
        self.broker, self.port, self.topic, self.qos = broker, port, topic, int(qos)
        self.client: Optional[Client] = None
        self.messages = 0
        self.bytes_sent = 0
        self.latencies = []

    def connect(self):
        if mqtt is None:
            print("[MQTT] paho-mqtt not installed — simulating publish() latency.")
            return
        self.client = mqtt.Client()
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def publish(self, payload: dict):
        t0 = time.perf_counter()
        msg = json.dumps(payload).encode("utf-8")
        if self.client:
            self.client.publish(self.topic, msg, qos=self.qos)
        else:
            # simulate network delay: base + qos factor
            time.sleep(0.005 + 0.003 * self.qos)
        t1 = time.perf_counter()
        self.messages += 1
        self.bytes_sent += len(msg)
        self.latencies.append(t1 - t0)

    def close(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def stats(self):
        avg = (sum(self.latencies)/len(self.latencies)) if self.latencies else 0.0
        return {"messages": self.messages, "bytes_sent": self.bytes_sent, "avg_latency_s": avg}
