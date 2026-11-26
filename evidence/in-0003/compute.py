"""in-0003: A-share turnover concentration + margin divergence (free sources).

Turnover concentration: full A-share cross-section from sina spot (5580 names,
live snapshot 2026-11-26). Historical daily cross-sections are NOT available
from free sources here (push2 rate-limited, no ClickHouse/Tushare/baostock),
so concentration is a one-day sample, stated honestly.

Margin divergence: SSE margin aggregate history (akshare stock_margin_sse,
free, unit yuan) vs Shanghai Composite (sina). Scope = Shanghai market only;
SZSE aggregate history requires per-date calls (not fetched) and the
two-market aggregate endpoint failed; stated honestly.
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
results = {}

spot = pd.read_csv(OUT / "spot_a_sina.csv")
amt = pd.to_numeric(spot["成交额"], errors="coerce")
amt = amt[amt > 0].sort_values(ascending=False)
n = len(amt)
k5 = max(1, int(round(n * 0.05)))
total = float(amt.sum())
results["turnover_concentration"] = {
    "source": "sina stock_zh_a_spot (via akshare), live snapshot",
    "date": "2026-11-26",
    "n_names_with_amount": n,
    "total_amount_yuan": total,
    "total_amount_wan_yi": round(total / 1e12, 4),
    "top5pct_count": k5,
    "top5pct_amount_share": round(float(amt.iloc[:k5].sum() / total), 4),
    "top10_amount_share": round(float(amt.iloc[:10].sum() / total), 4),
    "top1pct_amount_share": round(float(amt.iloc[:max(1, n // 100)].sum() / total), 4),
    "caliber_note": "sina 成交额 unit=yuan; one-day sample; historical daily cross-section unavailable from free sources here",
}
print("CONCENTRATION", json.dumps(results["turnover_concentration"], ensure_ascii=False))

import akshare as ak

sse = ak.stock_margin_sse(start_date="20100101", end_date="20261126")
sse.to_csv(OUT / "in0003_sse_margin_history.csv", index=False)
sse["date"] = pd.to_datetime(sse["信用交易日期"], format="%Y%m%d")
sse = sse.set_index("date").sort_index()
rzye = pd.to_numeric(sse["融资余额"], errors="coerce")
results["sse_margin"] = {"rows": len(sse), "start": str(sse.index[0].date()),
                         "end": str(sse.index[-1].date()),
                         "latest_rzye_yuan": float(rzye.iloc[-1]),
                         "latest_rzye_wan_yi": round(float(rzye.iloc[-1]) / 1e12, 4)}
print("SSE_MARGIN", json.dumps(results["sse_margin"]))

idx = ak.index_zh_daily_sina(symbol="sh000001")
idx.to_csv(OUT / "in0003_sh_index_history.csv", index=False)
idx["date"] = pd.to_datetime(idx["date"])
idx = idx.set_index("date").sort_index()
close = pd.to_numeric(idx["close"], errors="coerce")

merged = pd.DataFrame({"margin": rzye, "index": close}).dropna()
W = 120
margin_hi = merged["margin"] >= merged["margin"].rolling(W, min_periods=60).max()
index_hi = merged["index"] >= merged["index"].rolling(W, min_periods=60).max()
divergence = margin_hi & ~index_hi
merged["margin_120d_new_high"] = margin_hi
merged["index_120d_new_high"] = index_hi
merged["divergence_flag"] = divergence
mg = merged["margin"].pct_change(20)
ig = merged["index"].pct_change(20)
merged["growth_gap_20d_pp"] = (mg - ig) * 100
merged.to_csv(OUT / "in0003_divergence_series.csv")
recent = merged.tail(10)
results["margin_divergence"] = {
    "scope": "Shanghai market only (SSE margin aggregate vs Shanghai Composite)",
    "window_days": W,
    "merged_days": len(merged),
    "start": str(merged.index[0].date()), "end": str(merged.index[-1].date()),
    "divergence_days_total": int(divergence.sum()),
    "divergence_days_last_250": int(divergence.tail(250).sum()),
    "latest_flag": bool(divergence.iloc[-1]),
    "latest_growth_gap_20d_pp": round(float(merged["growth_gap_20d_pp"].iloc[-1]), 3),
    "recent_10d": {str(k): v for k, v in recent[["margin", "index", "divergence_flag", "growth_gap_20d_pp"]].round(3).to_dict(orient="index").items()},
    "unit_note": "SSE rzye unit=yuan (akshare stock_margin_sse); index=Shanghai Composite close",
}
print("DIVERGENCE", json.dumps(results["margin_divergence"], ensure_ascii=False, default=str)[:600])

try:
    acc = ak.stock_margin_account_info()
    acc.to_csv(OUT / "in0003_margin_account_info.csv", index=False)
    results["two_market_aggregate"] = {"rows": len(acc), "columns": list(acc.columns),
                                       "tail": acc.tail(2).to_dict(orient="records")}
    print("TWO_MARKET OK", len(acc))
except Exception as exc:
    results["two_market_aggregate"] = {"error": str(exc)[:200]}
    print("TWO_MARKET FAIL", str(exc)[:150])

(OUT / "in0003_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print("WROTE in0003_results.json")