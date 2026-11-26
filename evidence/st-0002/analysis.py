"""st-0002 analysis: subperiod robustness + direct winners-vs-losers decile test.

Part 1: split each run's equity curve in half (same method as st-0001).
Part 2: rebuild month-end formation (12-1) from the archived adjusted OHLCV,
rank deciles at each month-end, and compute next-month equal-weight decile
returns. The winners-minus-losers spread directly tests the entry's core
claim. Raw spread (no costs) is a research-level signal test; the traded
long-only backtest above carries the execution costs.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

RUNS = Path(os.environ.get("VALIDATE_RUNS_DIR", str(Path.home() / ".vibe-trading/runs/library-validate-001")))
OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
ANN = {"us": 252, "hk": 252}


def max_drawdown(eq):
    return float((eq / eq.cummax() - 1.0).min())


def sharpe(r, ann):
    return float(r.mean() / r.std() * np.sqrt(ann)) if r.std() > 0 else 0.0


def half_stats(eq, lo, hi, ann):
    seg = eq.loc[lo:hi]
    rets = seg.pct_change().dropna()
    years = (seg.index[-1] - seg.index[0]).days / 365.25
    total = float(seg.iloc[-1] / seg.iloc[0] - 1.0)
    return {
        "start": str(seg.index[0].date()), "end": str(seg.index[-1].date()),
        "total_return": round(total, 6),
        "cagr": round(float((1 + total) ** (1 / years) - 1), 6),
        "max_drawdown": round(max_drawdown(seg), 6),
        "sharpe": round(sharpe(rets, ann), 4),
    }


def load_panel(run):
    files = sorted((RUNS / run / "artifacts").glob("ohlcv_*.csv"))
    closes = {}
    for f in files:
        code = f.stem.replace("ohlcv_", "")
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        closes[code] = df["close"]
    return pd.DataFrame(closes).sort_index()


def decile_spread(panel, horizon=1):
    me = panel.resample("ME").last()
    formation = me.shift(2) / me.shift(13) - 1.0
    fwd = me.shift(-horizon) / me - 1.0
    rows = []
    for i in range(len(me)):
        f = formation.iloc[i]
        valid = f[np.isfinite(f) & (f > -1.0)]
        if len(valid) < 50:
            continue
        r = fwd.iloc[i].reindex(valid.index)
        ok = np.isfinite(r)
        valid, r = valid[ok], r[ok]
        if len(valid) < 50:
            continue
        n = len(valid)
        k = max(1, n // 10)
        order = valid.sort_values(ascending=False, kind="mergesort")
        win = r.reindex(order.index[:k]).mean()
        los = r.reindex(order.index[-k:]).mean()
        rows.append({"month": str(me.index[i].date()), "n": n,
                     "winners": float(win), "losers": float(los),
                     "spread": float(win - los)})
    df = pd.DataFrame(rows)
    s = df["spread"]
    tstat = float(s.mean() / (s.std() / np.sqrt(len(s)))) if s.std() > 0 else 0.0
    mid = len(df) // 2
    return {
        "months": len(df),
        "first_month": df["month"].iloc[0], "last_month": df["month"].iloc[-1],
        "mean_monthly_winners": round(float(df["winners"].mean()), 6),
        "mean_monthly_losers": round(float(df["losers"].mean()), 6),
        "mean_monthly_spread": round(float(s.mean()), 6),
        "spread_tstat_naive": round(tstat, 3),
        "spread_positive_months_pct": round(float((s > 0).mean() * 100), 2),
        "first_half_mean_spread": round(float(s.iloc[:mid].mean()), 6),
        "second_half_mean_spread": round(float(s.iloc[mid:].mean()), 6),
        "note": "naive t-stat ignores overlap/autocorrelation; research-level signal test, no costs",
    }, df


results = {}
for mkt, run in (("us", "st0002-us"), ("hk", "st0002-hk")):
    eq = pd.read_csv(RUNS / run / "artifacts" / "equity.csv", index_col=0, parse_dates=True)["equity"]
    mid = eq.index[0] + (eq.index[-1] - eq.index[0]) / 2
    panel = load_panel(run)
    spread, monthly = decile_spread(panel, horizon=1)
    monthly.to_csv(OUT / f"st0002_{mkt}_decile_monthly.csv", index=False)
    spread6, monthly6 = decile_spread(panel, horizon=6)
    monthly6.to_csv(OUT / f"st0002_{mkt}_decile_monthly_h6.csv", index=False)
    yearly = {str(y): round(float(seg.iloc[-1] / seg.iloc[0] - 1), 6)
              for y, seg in eq.groupby(eq.index.year) if len(seg) > 1}
    results[mkt] = {
        "run_dir": str(RUNS / run),
        "n_codes_with_data": panel.shape[1],
        "evaluation_start": str(eq.index[0].date()),
        "evaluation_end": str(eq.index[-1].date()),
        "full": half_stats(eq, eq.index[0], eq.index[-1], ANN[mkt]),
        "first_half": half_stats(eq, eq.index[0], mid, ANN[mkt]),
        "second_half": half_stats(eq, mid, eq.index[-1], ANN[mkt]),
        "calendar_year_returns": yearly,
        "decile_spread_test": spread,
        "decile_spread_test_h6": spread6,
    }

with open(OUT / "st0002_analysis.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
for mkt, v in results.items():
    print(mkt, "codes:", v["n_codes_with_data"], v["evaluation_start"], "->", v["evaluation_end"])
    for k in ("full", "first_half", "second_half"):
        s = v[k]
        print(" ", k, "ret", s["total_return"], "cagr", s["cagr"], "dd", s["max_drawdown"], "sharpe", s["sharpe"])
    print("  spread_h1:", json.dumps(v["decile_spread_test"]))
    print("  spread_h6:", json.dumps(v["decile_spread_test_h6"]))