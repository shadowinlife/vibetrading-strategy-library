"""kn-0003 empirical test: valuation percentile vs forward long-term returns.

Data: Shiller ie_data.xls (public, Yale), monthly 1871-2023.09: CAPE (P/E10)
and real total-return price index. Test: percentile of CAPE in its trailing
10-year window vs forward 5y/10y real total-return CAGR.

Scope note: this is the US aggregate market, not industry cross-sections.
It tests the general valuation mean-reversion mechanism the entry relies on
(Campbell-Shiller lineage); the industry-level claim itself is not directly
tested here and that gap is stated in the verdict.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))

raw = pd.read_excel(OUT / "shiller_ie_data.xls", sheet_name="Data", header=None)
data = raw.iloc[8:].copy()
data = data[pd.to_numeric(data[0], errors="coerce").notna()]
df = pd.DataFrame({
    "date_frac": pd.to_numeric(data[0]),
    "cape": pd.to_numeric(data[12], errors="coerce"),
    "real_tr": pd.to_numeric(data[9], errors="coerce"),
}).dropna().reset_index(drop=True)
df["year"] = df["date_frac"].astype(int)
df["month"] = ((df["date_frac"] % 1) * 12 + 0.5).astype(int).clip(1, 12)
df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
df = df.set_index("date").sort_index()
df.to_csv(OUT / "kn0003_shiller_cape_monthly.csv")

WINDOW = 120
pct = df["cape"].rolling(WINDOW, min_periods=WINDOW).apply(
    lambda w: float((w[:-1] < w[-1]).mean() * 100.0), raw=True)


def forward_test(horizon_months, label):
    fwd = (df["real_tr"].shift(-horizon_months) / df["real_tr"]) ** (12.0 / horizon_months) - 1.0
    pairs = pd.DataFrame({"percentile": pct, "fwd_cagr": fwd}).dropna()
    if len(pairs) < 20:
        return {"label": label, "n": len(pairs), "error": "too few"}
    pear = float(np.corrcoef(pairs["percentile"], pairs["fwd_cagr"])[0, 1])
    spear = float(pairs["percentile"].corr(pairs["fwd_cagr"], method="spearman"))
    x, y = pairs["percentile"].values, pairs["fwd_cagr"].values
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = np.sqrt(np.sum(resid**2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    pairs["quintile"] = pd.qcut(pairs["percentile"], 5, labels=False, duplicates="drop") + 1
    buckets = pairs.groupby("quintile").agg(
        n=("fwd_cagr", "count"), pct_min=("percentile", "min"),
        pct_max=("percentile", "max"), mean_fwd_cagr=("fwd_cagr", "mean"))
    return {
        "label": label, "n": len(pairs),
        "first": str(pairs.index[0].date()), "last": str(pairs.index[-1].date()),
        "pearson_r": round(pear, 4), "spearman_r": round(spear, 4),
        "ols_slope_per_pct_point": round(float(slope), 6),
        "ols_slope_tstat_naive": round(float(slope / se), 3) if se > 0 else None,
        "quintile_buckets": buckets.round(4).to_dict(orient="index"),
        "note": "overlapping windows inflate naive t-stat; aggregate US market, not industry cross-section",
    }, pairs


res5, pairs5 = forward_test(60, "forward_5y_real_TR")
res10, pairs10 = forward_test(120, "forward_10y_real_TR")
pairs5.to_csv(OUT / "kn0003_pairs_5y.csv")
pairs10.to_csv(OUT / "kn0003_pairs_10y.csv")
summary = {
    "source": "Shiller ie_data.xls (econ.yale.edu/~shiller/data/ie_data.xls), fetched 2026-11-26",
    "coverage": {"start": str(df.index[0].date()), "end": str(df.index[-1].date()),
                 "months": len(df)},
    "percentile_window_months": WINDOW,
    "test_5y": res5, "test_10y": res10,
}
(OUT / "kn0003_test_results.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2)[:2500])