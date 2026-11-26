"""st-0010 research-grade index simulation + event study (harvest-validate-b1).

The Shanghai Composite is not tradable; per the entry this is a RESEARCH-grade
simulation (no T+1 / lot / price-limit constraints, index units), cost 0.05%
per side on traded notional (entry operational default), signal at close,
execution at NEXT day open (same timing contract as the VT engine).

Signal (verbatim entry): divergence_t = (margin_t >= max(margin_{t-119..t}))
AND (close_t < max(close_{t-119..t})); margin = Eastmoney SSE aggregate
(snapshot archived 2026-11-26), close = sina sh000001. State 0.5 on divergence,
else 1.0; before margin data / 120-day warmup: 1.0.

Event study: forward 20/60-day index returns after divergence days, with
(a) naive overlap-inflated t (labelled), (b) non-overlapping greedy-selected
events vs spaced controls, (c) Newey-West HAC t on the full daily panel
(Bartlett kernel, lag = horizon).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WORK = Path("/root/projects/harvest-validate-b1/work")
OUT = WORK / "analysis"
OUT.mkdir(exist_ok=True)
COST = 0.0005  # per side, entry operational default for research-grade index
ANN = 252


def load_signal():
    sse = pd.read_csv(WORK / "st0010_sse_margin_snapshot_20261126.csv")
    sse["date"] = pd.to_datetime(sse["信用交易日期"], format="%Y%m%d")
    sse = sse.set_index("date").sort_index()
    margin = pd.to_numeric(sse["融资余额"], errors="coerce")
    idx = pd.read_csv(WORK / "st0010_sh000001_sina_daily.csv", parse_dates=["date"])
    idx = idx.set_index("date").sort_index()
    for c in ("open", "high", "low", "close"):
        idx[c] = pd.to_numeric(idx[c], errors="coerce")
    df = pd.DataFrame({"margin": margin, "close": idx["close"].reindex(margin.index)}).dropna()
    m_max = df["margin"].rolling(120, min_periods=120).max()
    c_max = df["close"].rolling(120, min_periods=120).max()
    div = (df["margin"] >= m_max) & (df["close"] < c_max)
    state = pd.Series(1.0, index=df.index)
    state[div] = 0.5
    return idx, df, div, state, m_max


def max_drawdown(equity):
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def perf(equity, ann=ANN):
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1.0) if years > 0 else 0.0
    sharpe = float(rets.mean() / rets.std() * np.sqrt(ann)) if rets.std() > 0 else 0.0
    return {"total_return": round(total, 6), "cagr": round(cagr, 6),
            "max_drawdown": round(max_drawdown(equity), 6),
            "sharpe": round(sharpe, 4), "n_bars": len(equity)}


def simulate(idx, state):
    """Two-state simulation on the index calendar, next-open execution."""
    dates = idx.index[idx.index >= state.index[0]]
    o = idx["open"].reindex(dates)
    c = idx["close"].reindex(dates)
    s = state.reindex(dates).fillna(1.0)
    cash, shares = 1_000_000.0, 0.0
    equity, fees, n_trades = [], 0.0, 0
    prev_w = None
    for i, d in enumerate(dates):
        w = float(s.iloc[i - 1]) if i > 0 else 1.0  # decision at prev close
        if i == 0:
            w = 1.0  # initial build at first open (warmup state 1.0)
        if prev_w is None or abs(w - prev_w) > 1e-9:
            eq_open = cash + shares * o.iloc[i]
            target_val = w * eq_open
            trade_val = target_val - shares * o.iloc[i]
            fee = abs(trade_val) * COST
            shares += trade_val / o.iloc[i]
            cash -= trade_val + fee
            fees += fee
            n_trades += 1
            prev_w = w
        equity.append(cash + shares * c.iloc[i])
    # terminal liquidation at last close (VT engine convention), fee applied
    liq = shares * c.iloc[-1]
    fee = liq * COST
    equity[-1] = equity[-1] - fee
    fees += fee
    eq = pd.Series(equity, index=dates)
    return eq, {"fees_total": round(fees, 2), "transitions_executed": n_trades,
                "terminal_liquidation_fee": round(fee, 2)}


def bh(idx, dates):
    o = idx["open"].reindex(dates)
    c = idx["close"].reindex(dates)
    shares = 1_000_000.0 / o.iloc[0]
    return pd.Series(shares * c.values, index=dates)


def halves(eq):
    mid = eq.index[0] + (eq.index[-1] - eq.index[0]) / 2
    out = {}
    for label, seg in (("first_half", eq.loc[:mid]), ("second_half", eq.loc[mid:])):
        if len(seg) > 2:
            out[label] = {"start": str(seg.index[0].date()), "end": str(seg.index[-1].date()),
                          **perf(seg)}
    return out


def nw_tstat(y, x, lag):
    """OLS y = a + b*x with Newey-West HAC (Bartlett) t on b."""
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    S = np.zeros((2, 2))
    for t in range(n):
        xt = X[t][:, None]
        S += (e[t] ** 2) * (xt @ xt.T)
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        for t in range(l, n):
            xt, xl = X[t][:, None], X[t - l][:, None]
            S += w * e[t] * e[t - l] * (xt @ xl.T + xl @ xt.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    return float(beta[1]), float(beta[1] / se[1]), float(se[1])


def main():
    idx, mdf, div, state, m_max = load_signal()
    dates = idx.index[idx.index >= state.index[0]]
    eq, sim_info = simulate(idx, state)
    bh_eq = bh(idx, dates)
    results = {
        "entry": "st-0010",
        "grade": "research (index not tradable; no T+1/lots/limits; index units)",
        "cost_per_side": COST,
        "data": {
            "margin_snapshot": "st0010_sse_margin_snapshot_20261126.csv (archived 2026-11-26, 2000 rows)",
            "margin_window": [str(mdf.index[0].date()), str(mdf.index[-1].date())],
            "index_source": "sina sh000001 daily (akshare index_zh_daily_sina)",
            "signal_first_defined": str(m_max.first_valid_index().date()),
            "divergence_days": int(div.sum()),
        },
        "simulation": {
            "window": [str(dates[0].date()), str(dates[-1].date())],
            "strategy": perf(eq), **sim_info,
            "buy_and_hold_index": perf(bh_eq),
            "subperiods": halves(eq),
            "bh_subperiods": halves(bh_eq),
            "note": "strategy buys at first open 2018-08-24; B&H same entry, zero costs; terminal liquidation fee applied to strategy only",
        },
    }
    eq.to_csv(OUT / "st0010_index_sim_equity.csv", header=["equity"])
    bh_eq.to_csv(OUT / "st0010_index_bh_equity.csv", header=["equity"])
    pd.DataFrame({"state": state, "divergence": div.astype(int)}).to_csv(OUT / "st0010_divergence_series.csv")

    # ---------------- event study -------------------------------------------
    c = idx["close"]
    pos = {d: i for i, d in enumerate(idx.index)}
    trig = [d for d in div.index[div] if d in pos]
    rows = []
    for d in trig:
        i = pos[d]
        r20 = c.iloc[i + 20] / c.iloc[i] - 1.0 if i + 20 < len(c) else np.nan
        r60 = c.iloc[i + 60] / c.iloc[i] - 1.0 if i + 60 < len(c) else np.nan
        rows.append({"date": d, "fwd20": r20, "fwd60": r60})
    ev = pd.DataFrame(rows).set_index("date")
    # non-trigger baseline: all days with defined forward windows, excluding triggers
    all_rows = []
    for i in range(len(c) - 60):
        d = idx.index[i]
        if d < state.index[0]:
            continue
        all_rows.append({"date": d, "fwd20": c.iloc[i + 20] / c.iloc[i] - 1.0,
                         "fwd60": c.iloc[i + 60] / c.iloc[i] - 1.0,
                         "div": bool(div.get(d, False))})
    panel = pd.DataFrame(all_rows).set_index("date")
    base = panel[~panel["div"]]
    es = {}
    for h in ("fwd20", "fwd60"):
        e = ev[h].dropna()
        b = base[h].dropna()
        t_naive, p_naive = stats.ttest_ind(e, b, equal_var=False)
        # non-overlapping greedy selection (spacing >= 60 trading days)
        def greedy(dframe):
            picked, last_i = [], -10**9
            for d in dframe.index:
                i = pos[d]
                if i - last_i >= 60:
                    picked.append(d)
                    last_i = i
            return dframe.loc[picked]
        ev_no = greedy(ev.dropna(subset=[h]))
        base_no = greedy(base)
        t_no, p_no = stats.ttest_ind(ev_no[h], base_no[h], equal_var=False)
        # Newey-West on full panel (dummy regression), lag = horizon
        y = panel[h].to_numpy()
        x = panel["div"].to_numpy(dtype=float)
        lag = 20 if h == "fwd20" else 60
        beta, t_nw, se = nw_tstat(y, x, lag)
        es[h] = {
            "n_events": int(len(e)),
            "event_mean": round(float(e.mean()), 6),
            "baseline_mean_all_non_trigger": round(float(b.mean()), 6),
            "naive_welch_t": round(float(t_naive), 4),
            "naive_p": round(float(p_naive), 6),
            "naive_caveat": "overlapping forward windows inflate significance; not evidence on its own",
            "non_overlapping": {
                "n_events": int(len(ev_no)), "n_controls": int(len(base_no)),
                "event_mean": round(float(ev_no[h].mean()), 6),
                "control_mean": round(float(base_no[h].mean()), 6),
                "welch_t": round(float(t_no), 4), "p": round(float(p_no), 6),
                "spacing": ">=60 trading days between selected events (greedy)",
            },
            "newey_west": {
                "beta_div_dummy": round(beta, 6), "t": round(t_nw, 4),
                "se": round(se, 6), "lag": lag,
                "n_obs": int(len(panel)),
                "note": "OLS fwd-return ~ divergence dummy, Bartlett HAC, lag=horizon",
            },
        }
    results["event_study"] = es
    ev.to_csv(OUT / "st0010_event_forward_returns.csv")
    (OUT / "st0010_research_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
