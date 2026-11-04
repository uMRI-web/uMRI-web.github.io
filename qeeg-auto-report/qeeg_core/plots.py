from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import Normalize
from scipy.interpolate import griddata

from .analysis import QEEGResult, ELECTRODES

CH_POS = {
    "Fp1": (1.5, 4.2), "Fp2": (2.5, 4.2),
    "C3": (0.95, 2.0), "C4": (3.05, 2.0),
    "O1": (1.5, 0.0), "O2": (2.5, 0.0),
    "T3": (-0.1, 2.0), "T4": (4.1, 2.0),
    "F7": (0.1, 3.0), "F8": (3.9, 3.0),
    "T5": (0.4, 0.4), "T6": (3.6, 0.4),
}

def _topomap(values: dict[str, float], title: str, out_path: Path) -> None:
    n = 300
    center = (2.0, 2.0)
    radius = 2.0
    x = np.array([CH_POS[e][0] for e in ELECTRODES], dtype=float)
    y = np.array([CH_POS[e][1] for e in ELECTRODES], dtype=float)
    z = np.array([values[e] for e in ELECTRODES], dtype=float)

    xi = np.linspace(-2, 6, n)
    yi = np.linspace(-2, 6, n)
    xx, yy = np.meshgrid(xi, yi)
    zi = griddata((x, y), z, (xx, yy), method="cubic")
    mask = np.sqrt((xx-center[0])**2 + (yy-center[1])**2) > radius
    zi[mask] = np.nan

    fig, ax = plt.subplots(figsize=(10, 8))
    dist = ax.contourf(xi, yi, zi, 60, cmap="bwr", norm=Normalize(vmin=-2.5, vmax=2.5))
    ax.contour(xi, yi, zi, 15, linewidths=0.5, colors="grey")
    fig.colorbar(dist, ax=ax, format="%.1f")
    ax.scatter(x, y, marker="o", c="b", s=15, zorder=3)
    ax.add_patch(patches.Circle(center, radius, edgecolor="k", facecolor="none", zorder=4))
    ax.add_patch(patches.Ellipse((0, 2), 0.4, 1.0, edgecolor="k", facecolor="w", zorder=0))
    ax.add_patch(patches.Ellipse((4, 2), 0.4, 1.0, edgecolor="k", facecolor="w", zorder=0))
    ax.add_patch(patches.Polygon([[1.6,3.6],[2,4.3],[2.4,3.6]], edgecolor="k", facecolor="w", zorder=0))
    for spine in ax.spines.values():
        spine.set_linewidth(0)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-0.5, 4.5); ax.set_ylim(-0.5, 4.5)
    ax.set_title(title)
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)

def save_topomaps(result: QEEGResult, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for band in ("theta", "alpha", "beta"):
        values = {e: result.electrodes[e].z[band] for e in ELECTRODES}
        p = out_dir / f"{band}_save_topomap.png"
        _topomap(values, f"{band}_topomap", p)
        paths[band] = p
    return paths

def save_psd_plots(result: QEEGResult, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for e in ELECTRODES:
        er = result.electrodes[e]
        fig, ax = plt.subplots()
        ax.plot(er.freqs, er.psd)
        ax.ticklabel_format(style="plain", axis="y", useOffset=False)
        ax.set_title("EEG-" + e)
        ax.set_xlabel("Frequency [Hz]")
        ax.set_ylabel("Power Spectral Density [uV^2/Hz]")
        ax.set_xlim(4, 30)
        p = out_dir / f"EEG-{e}.png"
        fig.savefig(p, dpi=100, bbox_inches="tight")
        plt.close(fig)
        paths[e] = p
    return paths
