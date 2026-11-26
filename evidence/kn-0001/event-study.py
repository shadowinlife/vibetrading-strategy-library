"""kn-0001 sub-signal event study: margin divergence -> forward index returns.

Uses the in-0003 divergence series (SSE margin vs Shanghai Composite, 120-day
new-high divergence). Tests whether divergence-flag days are followed by
weaker forward 20/60-day index returns than unconditional days.
Scope: one signal family, Shanghai market only — NOT the full escape-top
integration; kn-0001 remains research_only regardless of this result.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
df = pd.read_csv(OUT / "in0003_divergence_series.csv", index_col=0, parse_dates=True)
idx = df["index"]
flag = df["divergence_flag"].astype(bool)

results = {}
for h in (20, 60):
    fwd = idx.shift(-h) / idx - 1.0
    ev = fwd[flag].dropna()
    base = fwd[~flag].dropna()
    allf = fwd.dropna()
    results[f"forward_{h}d"] = {
        "n_event_days": len(ev), "n_nonevent_days": len(base),
        "event_mean_pct": round(float(ev.mean() * 100), 3),
        "nonevent_mean_pct": round(float(base.mean() * 100), 3),
        "all_mean_pct": round(float(allf.mean() * 100), 3),
        "event_median_pct": round(float(ev.median() * 100), 3),
        "event_negative_share_pct": round(float((ev < 0).mean() * 100), 2),
        "nonevent_negative_share_pct": round(float((base < 0).mean() * 100), 2),
        "diff_pp": round(float((ev.mean() - base.mean()) * 100), 3),
    }
results["scope"] = "Shanghai only; margin_divergence family only; overlapping events inflate significance; not the full integration"
results["sample"] = {"start": str(df.index[0].date()), "end": str(df.index[-1].date()),
                     "days": len(df), "flag_days": int(flag.sum())}
(OUT / "kn0001_event_study.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))