import numpy as np

def reconstruct_from_samples(length, idx, vals, method="hold"):
    idx = np.asarray(idx, dtype=int)
    vals = np.asarray(vals, dtype=float)
    recon = np.zeros(length, dtype=float)
    if len(idx) == 0:
        return recon
    pos = 0
    last = vals[0]
    for i in range(length):
        if pos + 1 < len(idx) and i >= idx[pos + 1]:
            pos += 1
            last = vals[pos]
        recon[i] = last
    return recon

def rmse(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mae(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))
