from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.integrate import simpson

from .parser import read_m00
from .norms import ELECTRODE_BAND_NORMS, FRONTAL_NORMS

ELECTRODES = ["Fp1", "Fp2", "C3", "C4", "O1", "O2", "T3", "T4", "F7", "F8", "T5", "T6"]
BANDS = {"theta": (4.0, 8.0), "alpha": (8.0, 12.0), "beta": (12.0, 30.0)}

@dataclass
class ElectrodeResult:
    electrode: str
    freqs: np.ndarray
    psd: np.ndarray
    absolute: dict[str, float]
    relative: dict[str, float]
    z: dict[str, float]

@dataclass
class QEEGResult:
    source_filename: str
    sampling_rate_hz: float
    electrodes: dict[str, ElectrodeResult]
    frontal: dict[str, float]
    metadata: dict

def _z(value: float, mean: float, sd: float) -> float:
    return (value - mean) / sd

def analyze_m00(path: str | Path) -> QEEGResult:
    df, meta = read_m00(path)
    sf = float(meta["sampling_rate_hz"])
    nperseg = int(4 * sf)

    results: dict[str, ElectrodeResult] = {}
    for electrode in ELECTRODES:
        values = df[electrode].to_numpy(dtype=float)
        freqs, psd = signal.welch(values, fs=sf, nperseg=nperseg)
        freq_res = float(freqs[1] - freqs[0])

        absolute: dict[str, float] = {}
        for band, (lo, hi) in BANDS.items():
            idx = np.logical_and(freqs >= lo, freqs <= hi)
            absolute[band] = float(simpson(psd[idx], dx=freq_res))

        total = absolute["theta"] + absolute["alpha"] + absolute["beta"]
        if total <= 0:
            raise ValueError(f"{electrode}: 4–30 Hzの帯域パワーが0以下です。")
        relative = {band: absolute[band] / total for band in ("alpha", "beta", "theta")}

        zscores: dict[str, float] = {}
        for band in ("alpha", "beta", "theta"):
            mean, sd = ELECTRODE_BAND_NORMS[electrode][band]
            zscores[band] = _z(relative[band], mean, sd)

        results[electrode] = ElectrodeResult(electrode, freqs, psd, absolute, relative, zscores)

    fp1 = results["Fp1"]
    fp2 = results["Fp2"]

    alpha_abs_diff = float(np.log(fp2.absolute["alpha"]) - np.log(fp1.absolute["alpha"]))
    alpha_rel_diff = float(np.log(fp2.relative["alpha"]) - np.log(fp1.relative["alpha"]))
    am, asd = FRONTAL_NORMS["alpha_rel_diff"]

    btr_fp1 = fp1.absolute["beta"] / fp1.absolute["theta"]
    btr_fp2 = fp2.absolute["beta"] / fp2.absolute["theta"]
    btr_diff = btr_fp2 - btr_fp1

    m1, s1 = FRONTAL_NORMS["beta_theta_fp1"]
    m2, s2 = FRONTAL_NORMS["beta_theta_fp2"]
    md, sd = FRONTAL_NORMS["beta_theta_diff_fp2_minus_fp1"]

    frontal = {
        "alpha_abs_diff": alpha_abs_diff,
        "alpha_rel_diff": alpha_rel_diff,
        "z_alpha_rel_diff": _z(alpha_rel_diff, am, asd),
        "beta_theta_fp1_left": btr_fp1,
        "beta_theta_fp2_right": btr_fp2,
        "z_beta_theta_fp1_left": _z(btr_fp1, m1, s1),
        "z_beta_theta_fp2_right": _z(btr_fp2, m2, s2),
        "beta_theta_diff_right_minus_left": btr_diff,
        "z_beta_theta_diff_right_minus_left": _z(btr_diff, md, sd),
    }

    return QEEGResult(
        source_filename=Path(path).name,
        sampling_rate_hz=sf,
        electrodes=results,
        frontal=frontal,
        metadata=meta,
    )
