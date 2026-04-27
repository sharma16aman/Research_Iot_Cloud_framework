import json

def total_bytes(indices, values, serializer):
    payload = {
        "idx": list(map(int, indices)),
        "vals": list(map(float, values))
    }
    return len(serializer.serialize(payload))

def reduction_pct(used, baseline):
    return 100.0 * (1.0 - (used / baseline)) if baseline > 0 else 0.0

def energy_proxy(bytes_sent, messages):
    return bytes_sent + 50 * messages
