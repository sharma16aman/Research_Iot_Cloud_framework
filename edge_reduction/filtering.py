# edge_reduction/filtering.py
import numpy as np

def moving_average(series, window: int = 5) -> np.ndarray:
    """
    Symmetric moving average (same length output). Edges are handled by reflection.
    """
    if window <= 0: raise ValueError("window must be > 0")
    arr = np.asarray(series, dtype=float)
    pad = window // 2
    ext = np.pad(arr, (pad, pad), mode="edge")
    kernel = np.ones(window, dtype=float) / window
    out = np.convolve(ext, kernel, mode="valid")
    return out

def ema(series, alpha: float = 0.2) -> np.ndarray:
    """
    Exponential moving average (causal). alpha in (0,1].
    """
    if not (0 < alpha <= 1): raise ValueError("alpha must be in (0,1]")
    arr = np.asarray(series, dtype=float)
    out = np.empty_like(arr)
    if arr.size == 0: return out
    out[0] = arr[0]
    for i in range(1, arr.size):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i-1]
    return out
