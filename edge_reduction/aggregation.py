# edge_reduction/aggregation.py
import numpy as np
from typing import Iterable, List

def aggregate_array(series: np.ndarray, window: int = 5, method: str = "mean") -> np.ndarray:
    """
    Reduce a 1D array by fixed non-overlapping windows.
    Returns one value per window (last window included even if shorter).
    """
    if window <= 0: raise ValueError("window must be > 0")
    arr = np.asarray(series, dtype=float)
    out: List[float] = []
    for i in range(0, len(arr), window):
        chunk = arr[i:i+window]
        if chunk.size == 0: break
        if method == "mean": v = float(np.mean(chunk))
        elif method == "median": v = float(np.median(chunk))
        elif method == "min": v = float(np.min(chunk))
        elif method == "max": v = float(np.max(chunk))
        else: raise ValueError("method must be one of mean/median/min/max")
        out.append(v)
    return np.array(out, dtype=float)

def aggregate_stream(samples: Iterable[float], window: int = 5, method: str = "mean") -> Iterable[float]:
    """
    Generator version for streaming (yields once per completed window).
    """
    buf: List[float] = []
    for x in samples:
        buf.append(float(x))
        if len(buf) >= window:
            yield float(getattr(np, method)(buf) if method in {"mean","median","min","max"} else np.mean(buf))
            buf.clear()
    if buf:  # flush tail
        yield float(getattr(np, method)(buf) if method in {"mean","median","min","max"} else np.mean(buf))
