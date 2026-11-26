"""st-0001 subperiod robustness: split each market's evaluation window in half.

Reads VT backtest artifacts (equity.csv, trades.csv) and computes per-half
return / annualized / max drawdown / Sharpe / trade count, plus per-calendar-
year returns. All numbers derive from the archived engine outputs.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

RUNS = Path(os.environ.get("VALIDATE_RUNS_DIR", str(Path.home() / ".vibe-trading/runs/library-validate-001")))
OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
MARKETS = {"us": "st0001-us", "hk": "st0001-hk", "crypto": "st0001-crypto"}
ANN = {"us": 252, "hk": 252, "crypto": 365}


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def sharpe(returns: pd.Series, ann: int) -> float:
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(ann))


def half_stats(eq: pd.Series, trades: pd.DataFrame, ann: int, lo, hi) -> dict:
    seg = eq.loc[lo:hi]
    if len(seg) < 2:
        return {}
    rets = seg.pct_change().dropna()
    total = float(seg.iloc[-1] / seg.iloc[0] - 1.0)
    years = (seg.index[-1] - seg.index[0]).days / 365.25
    cagr = float((seg.iloc[-1] / seg.iloc[0]) ** (1 / years) - 1.0) if years > 0 else 0.0
    # trades.csv is a fill log; count only entry fills opened within the half
    tt = pd.to_datetime(trades["timestamp"])
    mask = (tt >= lo) & (tt <= hi)
    if "event" in trades.columns:
        mask &= trades["event"] == "entry"
    n = int(mask.sum())
    return {
        "start": str(seg.index[0].date()), "end": str(seg.index[-1].date()),
        "total_return": round(total, 6), "cagr": round(cagr, 6),
        "max_drawdown": round(max_drawdown(seg), 6),
        "sharpe": round(sharpe(rets, ann), 4), "trades_opened": n,
    }


results = {}
for mkt, run in MARKETS.items():
    eq = pd.read_csv(RUNS / run / "artifacts" / "equity.csv", index_col=0, parse_dates=True)
    eqcol = "equity" if "equity" in eq.columns else eq.columns[0]
    equity = eq[eqcol]
    trades = pd.read_csv(RUNS / run / "artifacts" / "trades.csv")
    mid = equity.index[0] + (equity.index[-1] - equity.index[0]) / 2
    ann = ANN[mkt]
    yearly = {}
    for year, seg in equity.groupby(equity.index.year):
        if len(seg) > 1:
            yearly[str(year)] = round(float(seg.iloc[-1] / seg.iloc[0] - 1.0), 6)
    results[mkt] = {
        "run_dir": str(RUNS / run),
        "evaluation_start": str(equity.index[0].date()),
        "evaluation_end": str(equity.index[-1].date()),
        "full": half_stats(equity, trades, ann, equity.index[0], equity.index[-1]),
        "first_half": half_stats(equity, trades, ann, equity.index[0], mid),
        "second_half": half_stats(equity, trades, ann, mid, equity.index[-1]),
        "calendar_year_returns": yearly,
        "trade_columns": list(trades.columns),
    }

with open(OUT / "st0001_subperiod_analysis.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(json.dumps(results, ensure_ascii=False, indent=2))