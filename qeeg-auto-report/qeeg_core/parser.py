from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

EEG_COLUMNS = [
    "Fp1-A1", "Fp2-A2", "C3-A1", "C4-A2", "O1-A1", "O2-A2",
    "T3-A1", "T4-A2", "F7-A1", "F8-A2", "T5-A1", "T6-A2",
]
RENAME = {c: c.split("-")[0] for c in EEG_COLUMNS}

def read_m00(path: str | Path) -> tuple[pd.DataFrame, dict]:
    path = Path(path)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        meta_line = f.readline().strip()

    meta: dict[str, object] = {"source_filename": path.name}
    for key, value in re.findall(r"([^=\s]+)=([^\s]+)", meta_line):
        meta[key] = value

    sampling_ms = float(meta.get("SamplingInterval[ms]", 2.0))
    meta["sampling_rate_hz"] = 1000.0 / sampling_ms

    df = pd.read_csv(path, sep=r"\s+", skiprows=1, engine="python")
    missing = [c for c in EEG_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"必要なEEG列がありません: {', '.join(missing)}")

    eeg = df[EEG_COLUMNS].rename(columns=RENAME).apply(pd.to_numeric, errors="coerce")
    eeg = eeg.dropna(how="any")
    if eeg.empty:
        raise ValueError("有効なEEGデータ行がありません。")
    return eeg, meta
