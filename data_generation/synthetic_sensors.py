# data_generation/synthetic_sensors.py
"""
Unified synthetic sensor generator (streaming + vectorized)
-----------------------------------------------------------
This module integrates:
1) A realistic, timestamped, multivariate STREAM generator (great for MQTT/HTTP demos).
2) A fast, VECTORIZED generator for multi-sensor × multi-run sweeps (great for experiments/plots).

Key features
- Reproducible via numpy Generator seeds.
- Diurnal temperature with inverse humidity; improved slow-varying pressure.
- Mean-reverting trends (no unbounded random walk).
- Event injection: spikes, step changes, drift episodes, and random dropouts.
- Backward-compatible generate_dataset(...) for your current main.py.

Public API (most used):
- SyntheticSensorStream: per-sensor streaming with timestamps.
- MultiSensorNetwork: convenience wrapper to stream multiple sensors.
- generate_array(...): fast vectorized N×T signal matrix + time grid.
- generate_dataset(...): thin wrapper returning only signals (N×T) for backwards compatibility.

Author: You + ChatGPT (2025)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator, List, Tuple, Dict, Optional
import time
from datetime import datetime, timedelta

import numpy as np


# ----------------------------
# Configuration dataclasses
# ----------------------------
@dataclass
class StreamConfig:
    sampling_hz: float = 1.0
    base_temp: float = 25.0
    base_humidity: float = 50.0
    base_pressure: float = 1013.25
    noise_temp: float = 0.15
    noise_humidity: float = 0.8
    noise_pressure: float = 0.4
    # mean-reverting trend strength (phi in AR(1)). 0.0=no trend, 0.95=slowly mean-reverting
    trend_phi: float = 0.95
    # event rates / magnitudes (per sample)
    spike_rate: float = 0.003
    spike_mag_temp: Tuple[float, float] = (0.8, 1.8)
    spike_mag_hum: Tuple[float, float] = (2.0, 6.0)
    step_rate: float = 0.0008
    step_mag_temp: Tuple[float, float] = (0.5, 1.2)
    step_mag_hum: Tuple[float, float] = (2.0, 5.0)
    dropout_rate: float = 0.0006  # probability the sensor returns None (missing)
    # diurnal amplitude/scales
    diurnal_temp_amp: float = 5.0
    diurnal_hum_amp: float = 8.0
    diurnal_phase_shift_hours: float = 14.0  # hottest ~2pm by default
    # slow synoptic pressure variation (~weekly)
    pressure_week_amp: float = 2.0
    # seed for RNG (per sensor)
    seed: Optional[int] = None


@dataclass
class VectorConfig:
    # simulation dimensions
    n_sensors: int = 8
    timesteps: int = 600
    # base signal + noise
    base_temp: float = 25.0
    diurnal_temp_amp: float = 5.0
    diurnal_phase_shift_hours: float = 14.0
    noise: float = 0.15
    # events
    spike_rate: float = 0.003
    spike_mag: Tuple[float, float] = (0.8, 1.8)
    step_rate: float = 0.0008
    step_mag: Tuple[float, float] = (0.5, 1.2)
    drift_prob: float = 0.02            # probability a drift episode occurs for a sensor
    drift_len: Tuple[int, int] = (60, 180)  # duration (samples)
    drift_mag: Tuple[float, float] = (0.002, 0.01)  # per-sample slope during drift
    dropout_rate: float = 0.0006
    seed: int = 42


# ----------------------------
# Helper functions
# ----------------------------
def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def _inject_spikes(rng: np.random.Generator, X: np.ndarray,
                   rate: float, mag: Tuple[float, float]) -> None:
    mask = rng.random(X.shape) < rate
    spikes = rng.uniform(mag[0], mag[1], size=X.shape) * rng.choice([-1.0, 1.0], size=X.shape)
    X += mask * spikes


def _inject_steps(rng: np.random.Generator, X: np.ndarray,
                  rate: float, mag: Tuple[float, float]) -> None:
    # for each sensor, at each time t a step might be added and persists
    n, T = X.shape
    for i in range(n):
        offset = 0.0
        for t in range(T):
            if rng.random() < rate:
                offset += rng.uniform(mag[0], mag[1]) * rng.choice([-1.0, 1.0])
            X[i, t] += offset


def _inject_drift_episodes(rng: np.random.Generator, X: np.ndarray,
                           prob: float, len_rng: Tuple[int, int],
                           slope_rng: Tuple[float, float]) -> None:
    n, T = X.shape
    for i in range(n):
        if rng.random() < prob:
            L = int(rng.integers(low=len_rng[0], high=min(len_rng[1], T)))
            start = int(rng.integers(low=0, high=T - L))
            slope = rng.uniform(slope_rng[0], slope_rng[1]) * rng.choice([-1.0, 1.0])
            X[i, start:start+L] += slope * np.arange(L)


def _inject_dropouts(rng: np.random.Generator, X: np.ndarray, rate: float) -> np.ndarray:
    mask = rng.random(X.shape) < rate
    X = X.copy()
    X[mask] = np.nan
    return X


def _diurnal_wave(t_seconds: np.ndarray, amp: float, phase_shift_hours: float) -> np.ndarray:
    # one full cycle per 24 hours -> angular frequency = 2*pi / 86400
    omega = 2.0 * np.pi / 86400.0
    return amp * np.sin(omega * (t_seconds - phase_shift_hours * 3600.0))


# ----------------------------
# STREAMING (your original idea, improved)
# ----------------------------
class SyntheticSensorStream:
    """
    Timestamped, realistic, multivariate sensor stream.
    Exposes .stream(...) generator yielding per-sample dicts with timestamps.

    Signals:
    - temperature: diurnal wave + mean-reverting trend + noise + events
    - humidity: inversely related to temperature (+ noise + events)
    - pressure: slow weekly oscillation + slight noise
    """

    def __init__(self, config: StreamConfig):
        self.cfg = config
        self.rng = _rng(config.seed)
        # internal mean-reverting states
        self.temp_trend = 0.0
        self.hum_trend = 0.0

    def _update_trend(self):
        # mean-reverting AR(1) toward 0 with Gaussian shock
        phi = self.cfg.trend_phi
        self.temp_trend = phi * self.temp_trend + self.rng.normal(0.0, 0.03)
        self.hum_trend = phi * self.hum_trend + self.rng.normal(0.0, 0.2)

    def _temperature(self, t: datetime) -> float:
        # diurnal + trend + noise + possible event
        tsec = t.timestamp()
        temp = self.cfg.base_temp + _diurnal_wave(
            np.array([tsec]), self.cfg.diurnal_temp_amp, self.cfg.diurnal_phase_shift_hours
        )[0]
        temp += self.temp_trend + self.rng.normal(0.0, self.cfg.noise_temp)

        # random spikes/steps
        if self.rng.random() < self.cfg.spike_rate:
            temp += self.rng.uniform(*self.cfg.spike_mag_temp) * self.rng.choice([-1.0, 1.0])
        if self.rng.random() < self.cfg.step_rate:
            self.temp_trend += self.rng.uniform(*self.cfg.step_mag_temp) * self.rng.choice([-1.0, 1.0])
        return temp

    def _humidity(self, current_temp: float) -> float:
        # inverse relation to temp + trend + noise + events
        hum = self.cfg.base_humidity - 0.9 * (current_temp - self.cfg.base_temp)
        hum += self.hum_trend + self.rng.normal(0.0, self.cfg.noise_humidity)
        hum = np.clip(hum, 5.0, 98.0)
        # spikes/steps
        if self.rng.random() < self.cfg.spike_rate:
            hum += self.rng.uniform(*self.cfg.spike_mag_hum) * self.rng.choice([-1.0, 1.0])
        if self.rng.random() < self.cfg.step_rate:
            self.hum_trend += self.rng.uniform(*self.cfg.step_mag_hum) * self.rng.choice([-1.0, 1.0])
        return float(np.clip(hum, 0.0, 100.0))

    def _pressure(self, t: datetime) -> float:
        # slow weekly oscillation + small noise
        day_of_year = t.timetuple().tm_yday
        weekly = self.cfg.pressure_week_amp * np.sin(2*np.pi * (day_of_year / 7.0))
        return self.cfg.base_pressure + weekly + self.rng.normal(0.0, self.cfg.noise_pressure)

    def stream(self, n_steps: Optional[int] = None,
               start_time: Optional[datetime] = None,
               realtime: bool = False) -> Iterator[Dict]:
        """
        Yield dictionaries: {"ts": datetime, "temperature": float|None,
                             "humidity": float|None, "pressure": float|None}
        If realtime=True, sleep to honor sampling_hz.
        """
        dt = 1.0 / max(1e-9, self.cfg.sampling_hz)
        t = start_time or datetime.utcnow()

        steps = 0
        while True:
            self._update_trend()
            # random dropout (all channels)
            if self.rng.random() < self.cfg.dropout_rate:
                yield {"ts": t, "temperature": None, "humidity": None, "pressure": None}
            else:
                temp = self._temperature(t)
                hum = self._humidity(temp)
                pres = self._pressure(t)
                yield {"ts": t, "temperature": temp, "humidity": hum, "pressure": pres}

            steps += 1
            if n_steps is not None and steps >= n_steps:
                break

            t = t + timedelta(seconds=dt)
            if realtime:
                time.sleep(dt)


class MultiSensorNetwork:
    """Manage multiple SyntheticSensorStream sensors on a shared clock."""
    def __init__(self, num_sensors: int, base_config: StreamConfig, seed: Optional[int] = None):
        self.num_sensors = num_sensors
        base_seed = seed if seed is not None else base_config.seed
        # give each sensor a different, reproducible seed
        self.sensors = [
            SyntheticSensorStream(StreamConfig(**{**base_config.__dict__, "seed": (None if base_seed is None else base_seed + i)}))
            for i in range(num_sensors)
        ]

    def stream_round_robin(self, n_steps: Optional[int] = None,
                           start_time: Optional[datetime] = None,
                           realtime: bool = False) -> Iterator[Dict]:
        """
        Iterate sensors in round-robin order, yielding per-sample dicts with 'sensor_id'.
        """
        gens = [s.stream(n_steps=n_steps, start_time=start_time, realtime=False) for s in self.sensors]
        active = True
        while active:
            active = False
            for i, g in enumerate(gens):
                try:
                    rec = next(g)
                    rec["sensor_id"] = i
                    yield rec
                    active = True
                    if realtime:
                        time.sleep(0.0)  # let caller control sleep; shared clock is advanced per sensor
                except StopIteration:
                    continue


# ----------------------------
# VECTORIZED (for experiments)
# ----------------------------
def generate_array(cfg: VectorConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fast vectorized generator.
    Returns:
        X: (n_sensors, T) array (temperature-like signal)
        t: (T,) time grid in seconds from 0
    """
    rng = _rng(cfg.seed)
    n, T = cfg.n_sensors, cfg.timesteps
    t = np.arange(T, dtype=float)

    # diurnal temperature baseline
    # assume 1 sample/sec; adjust as needed in your experiments
    base = cfg.base_temp + _diurnal_wave(t, cfg.diurnal_temp_amp, cfg.diurnal_phase_shift_hours)

    X = base[None, :].repeat(n, axis=0)
    X += rng.normal(0.0, cfg.noise, size=(n, T))

    # events
    _inject_spikes(rng, X, cfg.spike_rate, cfg.spike_mag)
    _inject_steps(rng, X, cfg.step_rate, cfg.step_mag)
    _inject_drift_episodes(rng, X, cfg.drift_prob, cfg.drift_len, cfg.drift_mag)
    X = _inject_dropouts(rng, X, cfg.dropout_rate)  # NaNs mark missing

    return X, t


# ---------------------------------------------
# Backward compatibility for your main.py
# ---------------------------------------------
def generate_dataset(n_sensors: int = 8, T: int = 600,
                     noise: float = 0.05, spikes: bool = True, drift: float = 0.0,
                     seed: int = 42) -> np.ndarray:
    """
    Matches the signature you already use in main.py.
    - 'spikes' toggles spike/step injection (drift episodes always on lightly).
    - 'drift' scales the diurnal amplitude slightly to imitate slow drift (kept for compatibility).
    Returns: (n_sensors, T) ndarray of temperature-like signals (NaNs possible).
    """
    vc = VectorConfig(
        n_sensors=n_sensors, timesteps=T,
        noise=max(1e-9, noise),
        spike_rate=0.003 if spikes else 0.0,
        step_rate=0.0008 if spikes else 0.0,
        drift_prob=0.02 if drift != 0.0 else 0.01,
        drift_len=(60, 180),
        drift_mag=(0.002 + abs(drift)*0.001, 0.01 + abs(drift)*0.002),
        seed=seed
    )
    X, _ = generate_array(vc)
    return X
