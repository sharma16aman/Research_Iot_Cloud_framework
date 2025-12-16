"""
Adaptive Sampling Algorithm
Based on: Lou et al., "A Data-Driven Adaptive Sampling Method Based on Edge Computing" (Sensors, 2020)

This module dynamically adjusts sampling frequency based on data variability.
It uses a lightweight linear prediction model to estimate the next sample and
adjusts the sampling interval based on the prediction error.

Author: Aman Sharma (2025)
"""

import numpy as np

class AdaptiveSampler:
    def __init__(self, 
                 base_interval=1.0,
                 min_interval=0.2,
                 max_interval=5.0,
                 low_thresh=0.1,
                 high_thresh=0.5):
        """
        Args:
            base_interval: starting sampling interval (seconds or data steps)
            min_interval: minimum possible sampling interval
            max_interval: maximum possible sampling interval
            low_thresh: error threshold for stable region (expand interval)
            high_thresh: error threshold for unstable region (reduce interval)
        """
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.low_thresh = low_thresh
        self.high_thresh = high_thresh
        self.last_sent_idx = 0
        self.next_interval = base_interval
        self.sent_data = []

    def fit_line(self, x1, y1, x2, y2, x):
        """Simple 2-point linear interpolation."""
        if x2 == x1:
            return y1
        slope = (y2 - y1) / (x2 - x1)
        return y2 + slope * (x - x2)

    def run(self, data):
        """
        Runs adaptive sampling on a numeric sequence.
        Args:
            data: list or np.array of sensor readings
        Returns:
            sampled_indices: indices of retained samples
            sampled_values: sampled sensor readings
        """
        sampled_indices = [0]
        sampled_values = [data[0]]
        self.last_sent_idx = 0
        self.next_interval = self.base_interval

        for i in range(1, len(data)):
            if i - self.last_sent_idx < self.next_interval:
                continue

            # Predict current value using last 2 samples
            if len(sampled_indices) >= 2:
                x1, x2 = sampled_indices[-2], sampled_indices[-1]
                y1, y2 = sampled_values[-2], sampled_values[-1]
                y_pred = self.fit_line(x1, y1, x2, y2, i)
            else:
                y_pred = sampled_values[-1]

            err = abs(data[i] - y_pred)

            # Adjust interval adaptively
            if err < self.low_thresh:
                self.next_interval = min(self.next_interval * 1.5, self.max_interval)
            elif err > self.high_thresh:
                self.next_interval = max(self.next_interval / 2, self.min_interval)

            # Record sample
            sampled_indices.append(i)
            sampled_values.append(data[i])
            self.last_sent_idx = i

        return np.array(sampled_indices), np.array(sampled_values)
    