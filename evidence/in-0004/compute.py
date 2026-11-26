"""in-0004: HK/US activity concentration on documented pools.

Pools: S&P 500 constituents (503, US) and Hang Seng Index constituents (85, HK),
snapshots fetched 2026-11-26 (see st0002_pools.json). NOT full-market coverage.
Turnover amount ~= volume x close (estimation caliber per entry).
Turnover concentration: daily series from archived adjusted OHLCV (st-0002 runs).
Market-cap concentration: current snapshot via yfinance fast_info (historical
market-cap series not available from free sources; stated as a limitation).
"""
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
RUNS = Path(os.environ.get("VALIDATE_RUNS_DIR", str(Path.home() / ".vibe-trading/runs/library-validate-001")))
POOLS = json.load(open(OUT / "st0002_pools.json"))


def load_panel(run):
    closes, volumes = {}, {}
    for f in sorted((RUNS / run / "artifacts").glob("ohlcv_*.csv")):
        code = f.stem.replace("ohlcv_", "")
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        closes[code] = df["close"]
        volumes[code] = df["volume"]
    return pd.DataFrame(closes).sort_index(), pd.DataFrame(volumes).sort_index()


def concentration_series(amount):
    shares = []
    top10 = []
    dates = []
    for ts, row in amount.iterrows():
        v = row.dropna()
        v = v[v > 0]
        if len(v) < 20:
            continue
        s = v.sort_values(ascending=False)
        k5 = max(1, int(round(len(s) * 0.05)))
        shares.append(float(s.iloc[:k5].sum() / s.sum()))
        top10.append(float(s.iloc[:10].sum() / s.sum()))
        dates.append(ts)
    return pd.DataFrame({"date": dates, "top5pct_amount_share": shares,
                         "top10_amount_share": top10}).set_index("date")


def fetch_mcaps(tickers, market):
    out, fails = {}, []
    for i, t in enumerate(tickers):
        sym = t if market == "hk" else t.replace(".US", "")
        try:
            fi = yf.Ticker(sym).fast_info
            mc = getattr(fi, "market_cap", None)
            if mc and mc > 0:
                out[t] = float(mc)
            else:
                fails.append(t)
        except Exception:
            fails.append(t)
        if i % 50 == 49:
            time.sleep(2)
    return out, fails


results = {}
for mkt, run, pool_key in (("us", "st0002-us", "sp500"), ("hk", "st0002-hk", "hsi")):
    close, volume = load_panel(run)
    amount = close * volume
    cs = concentration_series(amount)
    cs.to_csv(OUT / f"in0004_{mkt}_turnover_concentration.csv")
    mcaps, fails = fetch_mcaps(POOLS[pool_key]["tickers"], mkt)
    ms = pd.Series(mcaps).sort_values(ascending=False)
    k5 = max(1, int(round(len(ms) * 0.05)))
    results[mkt] = {
        "pool": pool_key, "pool_size": len(POOLS[pool_key]["tickers"]),
        "n_with_price_data": int(close.shape[1]),
        "turnover_series_start": str(cs.index[0].date()),
        "turnover_series_end": str(cs.index[-1].date()),
        "turnover_days": len(cs),
        "top5pct_amount_share_latest": round(float(cs["top5pct_amount_share"].iloc[-1]), 4),
        "top5pct_amount_share_mean": round(float(cs["top5pct_amount_share"].mean()), 4),
        "top5pct_amount_share_min": round(float(cs["top5pct_amount_share"].min()), 4),
        "top5pct_amount_share_max": round(float(cs["top5pct_amount_share"].max()), 4),
        "top10_amount_share_latest": round(float(cs["top10_amount_share"].iloc[-1]), 4),
        "mcap_n_fetched": len(mcaps), "mcap_fetch_failures": fails,
        "top5pct_mcap_share_current": round(float(ms.iloc[:k5].sum() / ms.sum()), 4),
        "top10_mcap_share_current": round(float(ms.iloc[:10].sum() / ms.sum()), 4),
        "total_pool_mcap": float(ms.sum()),
        "caliber": "amount=volume*close (estimate); pool not full market; mcap=current snapshot only",
    }
    pd.Series(mcaps).to_csv(OUT / f"in0004_{mkt}_mcaps.csv", header=["market_cap"])
    print(mkt, json.dumps(results[mkt], ensure_ascii=False)[:400], flush=True)

(OUT / "in0004_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE in0004_results.json")