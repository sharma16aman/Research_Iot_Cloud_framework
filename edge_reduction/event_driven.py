# edge_reduction/event_driven.py
import numpy as np

class Kalman1D:
    def __init__(self, process_var=1e-3, meas_var=1e-2, x0=0.0, p0=1.0):
        self.q = process_var
        self.r = meas_var
        self.x = x0
        self.p = p0

    def predict_only(self):
        # time update without measurement
        self.p += self.q
        return self.x

    def predict(self):
        # alias when caller wants the predicted state value
        return self.predict_only()

    def update(self, z):
        # measurement update
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (z - self.x)
        self.p = (1 - k) * self.p
        return self.x

class PageHinkley:
    def __init__(self, delta=0.5, lam=50, alpha=0.99):
        self.delta = delta
        self.lam = lam
        self.alpha = alpha
        self.mean = 0.0
        self.cummin = 0.0
        self.cum = 0.0

    def update(self, x):
        # x should be the residual/error
        self.mean = self.alpha * self.mean + (1 - self.alpha) * x
        self.cum += (x - self.mean - self.delta)
        self.cummin = min(self.cummin, self.cum)
        return (self.cum - self.cummin) > self.lam

class AdaptiveThresholdReducer:
    def __init__(self,
                 initial_thresh=0.12,
                 min_thresh=0.03,
                 max_thresh=0.6,
                 thresh_smooth=0.15,
                 ph_delta=0.08,
                 ph_lambda=15,
                 kf_process_var=5e-3,
                 kf_meas_var=1e-2,
                 max_gap=30,           # heartbeat: send at least every N samples
                 drift_boost=3.0):     # temporarily increase process noise on drift
        self.init_th = initial_thresh
        self.th = initial_thresh
        self.th_min = min_thresh
        self.th_max = max_thresh
        self.th_alpha = thresh_smooth
        self.detector = PageHinkley(delta=ph_delta, lam=ph_lambda)
        self.kf0 = (kf_process_var, kf_meas_var)
        self.kf = Kalman1D(kf_process_var, kf_meas_var, 0.0, 1.0)
        self.max_gap = int(max_gap)
        self.drift_boost = float(drift_boost)

    def reset(self, x0):
        pv, rv = self.kf0
        self.kf = Kalman1D(pv, rv, x0=x0, p0=1.0)
        self.detector = PageHinkley(delta=self.detector.delta, lam=self.detector.lam)
        self.th = np.clip(self.init_th, self.th_min, self.th_max)

    def run(self, data):
        data = np.asarray(data, dtype=float)
        if len(data) == 0:
            return np.array([], dtype=int), np.array([])
        self.reset(data[0])

        sent_idx = [0]
        sent_val = [data[0]]
        self.kf.update(data[0])
        last_sent_i = 0
        boosted_until = -1  # index until which process var is boosted

        for i in range(1, len(data)):
            # pure predict (no measurement update unless we send)
            self.kf.predict_only()
            pred = self.kf.x
            err = abs(data[i] - pred)

            # drift detection runs on residuals
            drift = self.detector.update(err)
            if drift:
                # be more sensitive: lower threshold and temporarily boost process noise
                self.th = max(self.th_min, self.th * 0.5)
                boosted_until = i + 10  # boost for next 10 steps

            # temporary process noise boost after drift
            if i <= boosted_until:
                self.kf.p += self.kf.q * self.drift_boost

            # send if err >= threshold OR heartbeat gap exceeded
            gap = i - last_sent_i
            should_send = (err >= self.th) or (gap >= self.max_gap)

            if should_send:
                sent_idx.append(i)
                sent_val.append(data[i])
                self.kf.update(data[i])  # now we learn from the measurement
                last_sent_i = i
                # adapt threshold toward recent error
                self.th = (1 - self.th_alpha) * self.th + self.th_alpha * min(self.th_max, err)

        return np.array(sent_idx), np.array(sent_val)
