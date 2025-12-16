import numpy as np

def bytes_per_message(serializer, t, v):
    return len(serializer.dumps({"t": int(t), "v": float(v)}))

def total_bytes(idx, vals, serializer):
    return int(np.sum([bytes_per_message(serializer, t, v) for t, v in zip(idx, vals)]))

def reduction_pct(bytes_used, baseline_bytes):
    if baseline_bytes == 0: return 0.0
    return 100.0 * (1.0 - (bytes_used / baseline_bytes))

def energy_proxy(bytes_used, n_msgs, a_per_byte=1.0, b_per_msg=200.0):
    """
    Simple linear proxy: E = a*bytes + b*messages
    Units are arbitrary; tune a,b from literature or device tests.
    """
    return a_per_byte * float(bytes_used) + b_per_msg * float(n_msgs)
