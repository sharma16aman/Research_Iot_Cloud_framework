# main.py
import os, math, yaml, itertools, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Data generators
from data_generation.synthetic_sensors import (
    generate_dataset,
    StreamConfig, MultiSensorNetwork
)

# Reducers
from edge_reduction.adaptive_sampling import AdaptiveSampler
from edge_reduction.event_driven import AdaptiveThresholdReducer
from edge_reduction.aggregation import aggregate_array
from edge_reduction.filtering import moving_average

# Metrics
from evaluation.accuracy_metrics import reconstruct_from_samples, rmse
from evaluation.efficiency_metrics import total_bytes, reduction_pct, energy_proxy

# Serialization
from serialization import json_handler
HAS_CBOR = False
try:
    from serialization import cbor_handler
    HAS_CBOR = True
except Exception:
    pass

# Protocols / Cloud (for streaming demos)
from protocols.mqtt_handler import MQTTHandler
from protocols.http_handler import HTTPHandler
from cloud.receiver import Receiver


def get_serializer(name):
    if name.upper() == "JSON": return ("JSON", json_handler)
    if name.upper() == "CBOR":
        if not HAS_CBOR: raise RuntimeError("CBOR requested but cbor2 not installed.")
        return ("CBOR", cbor_handler)
    raise ValueError(f"Unknown serializer {name}")

def ffill_nan(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float).copy()
    # if first is NaN, set to 0 (or any sane default)
    if np.isnan(arr[0]) or np.isinf(arr[0]):
        arr[0] = 0.0
    for i in range(1, arr.size):
        if np.isnan(arr[i]) or np.isinf(arr[i]):
            arr[i] = arr[i-1]
    return arr

# -------- Reducer builders (single config) ----------
def build_reducer(name, cfg):
    n = name.lower()
    if n == "adaptivesampling":
        p = cfg.get("adaptive_sampling", {})
        return name, AdaptiveSampler(
            base_interval=p.get("base_interval", 1.0),
            low_thresh=p.get("low_thresh", 0.05),
            high_thresh=p.get("high_thresh", 0.30),
        )
    if n == "adaptivethreshold":
        p = cfg.get("adaptive_threshold", {})
        return name, AdaptiveThresholdReducer(
            initial_thresh=p.get("initial_thresh", 0.12),
            min_thresh=p.get("min_thresh", 0.03),
            max_thresh=p.get("max_thresh", 0.60),
            thresh_smooth=p.get("thresh_smooth", 0.15),
            ph_delta=p.get("ph_delta", 0.08),
            ph_lambda=p.get("ph_lambda", 15),
            kf_process_var=p.get("kf_process_var", 5e-3),
            kf_meas_var=p.get("kf_meas_var", 1e-2),
            max_gap=p.get("max_gap", 30),
            drift_boost=p.get("drift_boost", 3.0),
        )
    if n == "aggregation-mean":
        class _Agg:
            def run(self, series):
                out = aggregate_array(series, window=5, method="mean")
                idx = np.arange(4, len(series), 5)
                if len(out) > len(idx): idx = np.concatenate([idx, [len(series)-1]])
                return idx, out
        return name, _Agg()
    if n == "filtering-ma":
        class _Filt:
            def run(self, series):
                filt = moving_average(series, window=5)
                idx = np.arange(len(series))
                return idx, filt
        return name, _Filt()
    raise ValueError(f"Unknown reducer {name}")

# -------- Parameter sweep helpers ----------
def sweep_param_sets(sweep_cfg: dict):
    """
    sweep_cfg example:
      {"low_thresh":[0.03,0.05], "high_thresh":[0.2,0.3], "max_gap":[15,30]}
    Returns list of dicts, one per combination. If empty/None -> [ {} ].
    """
    if not sweep_cfg: return [ {} ]
    keys = list(sweep_cfg.keys())
    vals = [sweep_cfg[k] for k in keys]
    combos = []
    for tup in itertools.product(*vals):
        combos.append({k:v for k,v in zip(keys, tup)})
    return combos

def build_reducer_with_params(name: str, base_cfg: dict, param_overrides: dict):
    cfg = json.loads(json.dumps(base_cfg))  # deep copy
    if name.lower()=="adaptivesampling":
        cfg.setdefault("adaptive_sampling", {}).update(param_overrides)
    elif name.lower()=="adaptivethreshold":
        cfg.setdefault("adaptive_threshold", {}).update(param_overrides)
    else:
        pass
    return build_reducer(name, cfg)

def ci95(arr):
    arr = np.asarray(arr, dtype=float)
    m = float(np.mean(arr))
    s = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    half = 1.96 * s / max(1, np.sqrt(len(arr)))
    return m, half

# =========================
# Vectorized (paper sweeps)
# =========================
def run_vectorized(cfg):
    exp = cfg["experiment"]
    N = exp["sensors"]; T = exp["timesteps"]; runs = exp["runs"]
    noise = exp.get("noise", 0.05); spikes = exp.get("spikes", True); drift = exp.get("drift", 0.0)
    reducers = exp["reducers"]; serializers = exp["serializers"]
    master_seed = int(exp.get("seed", 2025))

    # Baseline "send-all" bytes per serializer
    baseline_bytes = {}
    baseline_sig = generate_dataset(1, T, noise, spikes, drift, seed=master_seed)[0]
    base_idx = np.arange(T); base_vals = ffill_nan(baseline_sig)

    for sname in serializers:
        key, ser = get_serializer(sname)
        baseline_bytes[key] = total_bytes(base_idx, base_vals, ser)

    # Sweeps config
    sweep = cfg.get("sweep", {})  # { "adaptivesampling": {...}, "adaptivethreshold": {...} }

    rows = []
    rng = np.random.default_rng(master_seed)
    seeds = rng.integers(0, 2**31-1, size=runs)

    for rname in reducers:
        # parameter sets for this reducer
        psets = sweep_param_sets(sweep.get(rname.lower(), None))
        for pidx, pset in enumerate(psets):
            for run_id, seed in enumerate(seeds):
                data = generate_dataset(N, T, noise, spikes, drift, seed=int(seed))
                rlabel, reducer = build_reducer_with_params(rname, cfg, pset)

                kept_msgs, rmses = [], []
                bytes_by_ser = {key: 0 for key in baseline_bytes.keys()}

                for s in range(N):
                    clean = ffill_nan(data[s])
                    idx, vals = reducer.run(clean)
                    recon = reconstruct_from_samples(T, idx, vals)
                    rmses.append(rmse(clean, recon))
                    kept_msgs.append(len(idx))
                    for sname in serializers:
                        key, ser = get_serializer(sname)
                        bytes_by_ser[key] += total_bytes(idx, vals, ser)

                for sname in serializers:
                    base_b = baseline_bytes[sname]
                    used_b = bytes_by_ser[sname]
                    rows.append({
                        "mode":"vectorized","reducer":rlabel,"serializer":sname,
                        "param_set": json.dumps(pset, sort_keys=True),
                        "run": run_id, "sensors":N, "timesteps":T,
                        "bytes": used_b, "baseline_bytes": base_b*N,
                        "reduction_pct": reduction_pct(used_b, base_b*N),
                        "rmse_mean": float(np.mean(rmses)),
                        "rmse_std": float(np.std(rmses, ddof=1)) if N>1 else 0.0,
                        "messages": int(sum(kept_msgs)),
                        "energy_proxy": energy_proxy(used_b, sum(kept_msgs)),
                    })

    return pd.DataFrame(rows)

# =========================
# Streaming (demo + send)
# =========================
def run_streaming(cfg, use_protocols=False, protocol="MQTT", receive_to_db=False):
    exp = cfg["experiment"]; st = exp["streaming"]
    N = int(st["sensors"]); steps = int(st["steps_per_sensor"])
    hz = float(st.get("sampling_hz", 1.0))
    seed = int(st.get("seed", 777))
    realtime = bool(st.get("realtime", False))
    reducers = exp["reducers"]; serializers = exp["serializers"]

    mqtt_handler = http_handler = receiver = None
    if use_protocols:
        if protocol.upper() == "MQTT":
            mqtt_handler = MQTTHandler(topic="iot/demo", qos=0); mqtt_handler.connect()
        elif protocol.upper() == "HTTP":
            http_handler = HTTPHandler(endpoint="http://localhost:8000/data")
    if receive_to_db:
        receiver = Receiver()

    base_cfg = StreamConfig(sampling_hz=hz, seed=seed)
    net = MultiSensorNetwork(N, base_cfg, seed=seed)

    series = [ [] for _ in range(N) ]
    for rec in net.stream_round_robin(n_steps=steps, realtime=realtime):
        sid = rec["sensor_id"]
        series[sid].append(np.nan if rec["temperature"] is None else float(rec["temperature"]))

        if use_protocols:
            payload = {**rec, "ts": rec["ts"].isoformat()}
            if mqtt_handler: mqtt_handler.publish(payload)
            elif http_handler: http_handler.post(payload)
        if receive_to_db and receiver:
            receiver.handle_message({**rec, "ts": rec["ts"].isoformat()})

    T = len(series[0])
    data = np.zeros((N, T), dtype=float)
    for i in range(N):
        arr = np.array(series[i], dtype=float)
        for k in range(T):
            if k>0 and (np.isnan(arr[k]) or np.isinf(arr[k])): arr[k]=arr[k-1]
        data[i] = arr

    baseline_bytes = {}
    base_idx = np.arange(T); base_vals = data[0]
    for sname in serializers:
        key, ser = get_serializer(sname)
        baseline_bytes[key] = total_bytes(base_idx, base_vals, ser)

    rows = []
    for rname in reducers:
        rlabel, reducer = build_reducer(rname, cfg)
        kept_msgs, rmses = [], []
        bytes_by_ser = {key: 0 for key in baseline_bytes.keys()}

        for s in range(N):
            idx, vals = reducer.run(data[s])
            recon = reconstruct_from_samples(T, idx, vals)
            rmses.append(rmse(data[s], recon))
            kept_msgs.append(len(idx))
            for sname in serializers:
                key, ser = get_serializer(sname)
                bytes_by_ser[key] += total_bytes(idx, vals, ser)

        for sname in serializers:
            base_b = baseline_bytes[sname]
            used_b = bytes_by_ser[sname]
            rows.append({
                "mode":"streaming","reducer":rlabel,"serializer":sname,
                "param_set":"{}", "run":0, "sensors":N, "timesteps":T,
                "bytes": used_b, "baseline_bytes": base_b*N,
                "reduction_pct": reduction_pct(used_b, base_b*N),
                "rmse_mean": float(np.mean(rmses)),
                "rmse_std": float(np.std(rmses, ddof=1)) if N>1 else 0.0,
                "messages": int(sum(kept_msgs)),
                "energy_proxy": energy_proxy(used_b, sum(kept_msgs)),
            })

    if mqtt_handler: mqtt_handler.close(); print("MQTT stats:", mqtt_handler.stats())
    if http_handler: print("HTTP stats:", http_handler.stats())
    if receiver: print("DB rows stored:", receiver.stats())

    return pd.DataFrame(rows)

# -------------
# Entry point
# -------------
if __name__ == "__main__":
    with open(os.path.join("data_generation", "config.yaml"), "r") as f:
        cfg = yaml.safe_load(f)

    mode = cfg["experiment"].get("mode", "vectorized").lower()
    use_protocols = bool(cfg["experiment"].get("use_protocols", False))
    protocol = str(cfg["experiment"].get("protocol", "MQTT"))
    receive_to_db = bool(cfg["experiment"].get("receive_to_db", False))

    os.makedirs("results", exist_ok=True)

    if mode == "vectorized":
        df = run_vectorized(cfg)
    elif mode == "streaming":
        df = run_streaming(cfg, use_protocols=use_protocols, protocol=protocol, receive_to_db=receive_to_db)
    else:
        raise ValueError("experiment.mode must be 'vectorized' or 'streaming'.")

    out_csv = os.path.join("results", f"results_{mode}.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved → {out_csv}")

    # ---- quick sanity printouts ----
    print("\n[Sanity] df rows:", len(df))
    print(df.head(3).to_string())

    diag = df[df["serializer"]=="JSON"].groupby("reducer").agg(
        avg_reduction=("reduction_pct","mean"),
        avg_rmse=("rmse_mean","mean"),
        avg_msgs=("messages","mean"),
        avg_bytes=("bytes","mean"),
        avg_baseline=("baseline_bytes","mean"),
    )
    print("\n[Sanity] Averages per reducer (JSON):")
    print(diag.to_string())

       # ----- Summarize (JSON only for clarity) -----
    g = df[df["serializer"]=="JSON"].groupby(["reducer","param_set"], as_index=False).agg(
        reduction_mean=("reduction_pct","mean"),
        reduction_ci=("reduction_pct", lambda x: ci95(x)[1]),
        rmse_mean=("rmse_mean","mean"),
        rmse_ci=("rmse_mean", lambda x: ci95(x)[1]),
        energy_mean=("energy_proxy","mean"),
        energy_ci=("energy_proxy", lambda x: ci95(x)[1]),
    )

    # ----- Plot with multiple points per reducer -----
    plt.figure()
    for reducer_name, sub in g.groupby("reducer"):
        sub = sub.sort_values("reduction_mean")
        x = sub["reduction_mean"].to_numpy()
        y = sub["rmse_mean"].to_numpy()
        xerr = sub["reduction_ci"].to_numpy()
        yerr = sub["rmse_ci"].to_numpy()
        plt.errorbar(x, y, xerr=xerr, yerr=yerr, fmt='o-', capsize=3, label=reducer_name)

    plt.xlabel("Reduction vs JSON baseline (%)")
    plt.ylabel("RMSE (mean across sensors)")
    plt.title(f"Trade-off ({mode}) — parameter sweep")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # >>> NEW: auto-save plot <<<
    fig_path = os.path.join("results", "fig_tradeoff.png")
    plt.savefig(fig_path, dpi=220, bbox_inches="tight")
    print(f"Saved plot → {fig_path}")

    # If you still want an interactive window, uncomment:
    # plt.show()

    # ----- CSV → LaTeX table export -----
    def _pretty_params(s: str) -> str:
        """
        s is a JSON string like '{"low_thresh": 0.03, "high_thresh": 0.25}'
        Return a compact 'low=0.03, high=0.25' for table display.
        """
        try:
            obj = json.loads(s) if isinstance(s, str) else (s or {})
        except Exception:
            return str(s)
        if not obj: return "default"
        parts = []
        for k in sorted(obj.keys()):
            v = obj[k]
            # trim floats nicely
            if isinstance(v, float):
                v = f"{v:.3g}"
            parts.append(f"{k.replace('_',' ')}={v}")
        return ", ".join(parts)

    table = g.copy()
    table["params"] = table["param_set"].apply(_pretty_params)
    table = table[[
        "reducer", "params",
        "reduction_mean", "reduction_ci",
        "rmse_mean", "rmse_ci",
        "energy_mean", "energy_ci",
    ]].rename(columns={
        "reducer":"Method",
        "params":"Parameters",
        "reduction_mean":"Reduction (%)",
        "reduction_ci":"±CI",
        "rmse_mean":"RMSE",
        "rmse_ci":"±CI (RMSE)",
        "energy_mean":"Energy proxy",
        "energy_ci":"±CI (Energy)"
    })

    # round numbers for readability
    table["Reduction (%)"] = table["Reduction (%)"].map(lambda x: f"{x:.1f}")
    table["±CI"]            = table["±CI"].map(lambda x: f"{x:.1f}")
    table["RMSE"]           = table["RMSE"].map(lambda x: f"{x:.4f}")
    table["±CI (RMSE)"]     = table["±CI (RMSE)"].map(lambda x: f"{x:.4f}")
    table["Energy proxy"]   = table["Energy proxy"].map(lambda x: f"{x:.0f}")
    table["±CI (Energy)"]   = table["±CI (Energy)"].map(lambda x: f"{x:.0f}")

    # save CSV + LaTeX
    csv_path = os.path.join("results", "summary_table.csv")
    tex_path = os.path.join("results", "summary_table.tex")
    table.to_csv(csv_path, index=False)
    print(f"Saved summary CSV → {csv_path}")

    latex = table.to_latex(index=False, escape=True, longtable=False, column_format="llrrrrr")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Auto-generated by main.py\n")
        f.write("\\begin{table}[ht]\n\\centering\n")
        f.write(latex.split("\\begin{tabular}")[1])  # keep the tabular env only
        f.write("\\caption{Trade-off summary (mean ±95\\% CI) for JSON baseline.}\n")
        f.write("\\label{tab:tradeoff}\n\\end{table}\n")
    print(f"Saved LaTeX table → {tex_path}")

