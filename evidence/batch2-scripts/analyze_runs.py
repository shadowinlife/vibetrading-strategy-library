"""Cross-run analysis for harvest-validate-b2.

For every VT run: engine metrics + buy-and-hold benchmarks from the run's OWN
ohlcv artifacts (same data basis; B&H enters at first evaluation bar open,
marks to last close, zero costs), half-window subperiods, calendar years, and
entry-specific checks:
  st-0004: EW benchmark, ls research sensitivity, 2022, invested fraction, cap months
  st-0014: 60/40 + SPY benchmarks, 2022 stress subperiod (mandatory), claim
           checks, solver convergence + threshold fixed-point history
  st-0011: both semantics x both pairs, pair round-trip stats (sequential,
           non-overlapping), Engle-Granger cointegration (manual ADF), forced
           exits, state occupancy, prep-vs-artifact identity, fills-in-mask
  st-0007: losers-minus-winners monthly spread (non-overlapping by construction
           + Newey-West), January effect, EW pool + SPY benchmarks
  st-0008: low-minus-high quintile spread (non-overlapping + NW), GICS sector
           concentration, EW pool benchmark reuse (declared)
  st-0012: low-vs-high vol state forward-20d return separation (naive + NW +
           non-overlapping stride), jitter cost via zero-cost variants
Outputs JSON per entry under work/analysis/.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WORK = Path("/root/projects/harvest-validate-b2/work")
RUNS = Path("/root/.vibe-trading/runs/harvest-validate-b2")
OUT = WORK / "analysis"
OUT.mkdir(exist_ok=True)
ANN = {"us": 252, "crypto": 365}


def load_run(name):
    rd = RUNS / name
    m = pd.read_csv(rd / "artifacts" / "metrics.csv").iloc[0].to_dict()
    eq = pd.read_csv(rd / "artifacts" / "equity.csv", index_col=0, parse_dates=True)
    eqcol = "equity" if "equity" in eq.columns else eq.columns[0]
    equity = eq[eqcol]
    trades = pd.read_csv(rd / "artifacts" / "trades.csv")
    ohlcv = {}
    for p in (rd / "artifacts").glob("ohlcv_*.csv"):
        code = p.stem[len("ohlcv_"):]
        ohlcv[code] = pd.read_csv(p, index_col=0, parse_dates=True)
    cfg = json.loads((rd / "config.json").read_text())
    tp = pd.read_csv(rd / "artifacts" / "target_positions.csv", index_col=0, parse_dates=True)
    pos = pd.read_csv(rd / "artifacts" / "positions.csv", index_col=0, parse_dates=True)
    return {"metrics": m, "equity": equity, "trades": trades, "ohlcv": ohlcv,
            "cfg": cfg, "rd": rd, "targets": tp, "positions": pos}


def mdd(s):
    return float((s / s.cummax() - 1.0).min())


def perf(eq, ann):
    rets = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    total = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1.0) if years > 0 else 0.0
    sharpe = float(rets.mean() / rets.std() * np.sqrt(ann)) if rets.std() > 0 else 0.0
    return {"total_return": round(total, 6), "cagr": round(cagr, 6),
            "max_drawdown": round(mdd(eq), 6), "sharpe": round(sharpe, 4)}


def bh_equity(df, window, ann):
    o = df["open"].reindex(window)
    c = df["close"].reindex(window)
    first = o.first_valid_index()
    shares = 1_000_000.0 / float(o.loc[first])
    eq = (shares * c).loc[first:]
    return eq, perf(eq, ann)


def halves(eq, ann):
    mid = eq.index[0] + (eq.index[-1] - eq.index[0]) / 2
    out = {}
    for label, seg in (("first_half", eq.loc[:mid]), ("second_half", eq.loc[mid:])):
        if len(seg) > 2:
            out[label] = {"start": str(seg.index[0].date()), "end": str(seg.index[-1].date()),
                          **perf(seg, ann)}
    return out


def year_returns(eq):
    yr = eq.groupby(eq.index.year).last()
    first = eq.groupby(eq.index.year).first()
    return {int(y): round(float(yr[y] / first[y] - 1.0), 6) for y in yr.index}


def sub_window(eq, lo, hi, ann):
    seg = eq.loc[lo:hi]
    if len(seg) < 3:
        return None
    return {"start": str(seg.index[0].date()), "end": str(seg.index[-1].date()), **perf(seg, ann)}


def clean_metrics(m):
    keys = ["total_return", "annual_return", "max_drawdown", "sharpe", "calmar",
            "trade_count", "profit_factor", "win_rate", "avg_holding_days",
            "avg_turnover", "total_turnover", "benchmark_return",
            "rebalance_executed_bars", "dropped_target_adjustment_count",
            "position_adjustment", "rebalance_tolerance", "unfilled_plan_rejections"]
    out = {}
    for k in keys:
        if k in m:
            v = m[k]
            out[k] = float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v
    return out


def nw_mean_t(x, lag):
    """Newey-West (Bartlett HAC) t-stat for H0: mean(x)=0."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"n": n, "mean": None, "t_nw": None, "se_nw": None}
    e = x - x.mean()
    s = float(e @ e) / n
    for l in range(1, min(lag, n - 1) + 1):
        w = 1.0 - l / (lag + 1.0)
        s += 2.0 * w * float(e[l:] @ e[:-l]) / n
    s = max(s, 1e-18)
    se = float(np.sqrt(s / n))
    return {"n": n, "mean": round(float(x.mean()), 6),
            "t_nw": round(float(x.mean() / se), 4), "se_nw": round(se, 6)}


def adf_tstat(y, maxlag=4):
    """ADF regression t-stat on gamma in dY_t = gamma*Y_{t-1} + sum phi_i dY_{t-i} + c.
    Lag chosen by AIC over 0..maxlag. Returns (t, lag, nobs)."""
    y = np.asarray(y, dtype=float)
    dy = np.diff(y)
    best = None
    for lag in range(0, maxlag + 1):
        n = len(dy) - lag
        if n < 10:
            continue
        rows = []
        for t in range(lag, len(dy)):
            row = [1.0, y[t]]  # const, Y_{t-1} (y[t] is Y at index t, dy[t]=Y_{t+1}-Y_t)
            row += [dy[t - j] for j in range(1, lag + 1)]
            rows.append((row, dy[t]))
        X = np.array([r for r, _ in rows])
        Yv = np.array([v for _, v in rows])
        beta, res, _, _ = np.linalg.lstsq(X, Yv, rcond=None)
        resid = Yv - X @ beta
        sse = float(resid @ resid)
        k = X.shape[1]
        nn = len(Yv)
        aic = nn * np.log(sse / nn) + 2 * k
        se = np.sqrt(sse / (nn - k) * np.linalg.inv(X.T @ X)[1, 1])
        t = float(beta[1] / se)
        if best is None or aic < best[3]:
            best = (t, lag, nn, aic)
    return best[0], best[1], best[2]


def engle_granger(log_a, log_b):
    """OLS log_a = alpha + beta*log_b, ADF on residuals. EG critical values
    (n=2, constant in cointegrating regression, asymptotic MacKinnon):
    1% -3.337, 5% -2.782, 10% -2.486."""
    a = np.asarray(log_a, dtype=float)
    b = np.asarray(log_b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    X = np.column_stack([np.ones(len(b)), b])
    beta, _, _, _ = np.linalg.lstsq(X, a, rcond=None)
    resid = a - X @ beta
    t, lag, nobs = adf_tstat(resid)
    ss_res = float(resid @ resid)
    ss_tot = float(((a - a.mean()) ** 2).sum())
    return {"n_obs": int(len(a)), "hedge_beta": round(float(beta[1]), 6),
            "r_squared": round(1.0 - ss_res / ss_tot, 6),
            "adf_t_residual": round(t, 4), "adf_lag_aic": lag, "adf_nobs": nobs,
            "eg_critical_values": {"1pct": -3.337, "5pct": -2.782, "10pct": -2.486},
            "cointegrated_at_5pct": bool(t < -2.782),
            "note": "manual Engle-Granger; asymptotic EG critical values (2 vars, constant); statsmodels unavailable in venv"}


def base_report(name, mkt):
    r = load_run(name)
    ann = ANN[mkt]
    eq = r["equity"]
    rep = {
        "run": name,
        "evaluation_window": [str(eq.index[0].date()), str(eq.index[-1].date())],
        "engine_metrics": clean_metrics(r["metrics"]),
        "strategy_subperiods": halves(eq, ann),
        "strategy_year_returns": year_returns(eq),
        "benchmarks_buy_and_hold": {},
    }
    for code, df in r["ohlcv"].items():
        bh_eq, bh_perf = bh_equity(df, eq.index, ann)
        rep["benchmarks_buy_and_hold"][code] = {
            **bh_perf, "subperiods": halves(bh_eq, ann),
            "convention": "entry at first evaluation bar open, zero costs, same ohlcv artifact",
        }
    return rep, r


def fills_in_mask(r):
    fills = pd.read_json(r["rd"] / "artifacts" / "fills.jsonl", lines=True)
    fill_dates = set(pd.to_datetime(fills["timestamp"]).dt.strftime("%Y-%m-%d"))
    mask = set(r["cfg"]["rebalance_mask"]) if isinstance(r["cfg"]["rebalance_mask"], list) else set()
    last_day = str(r["equity"].index[-1].date())
    return sorted(fill_dates - mask - {last_day})


def data_identity(r, group):
    out = {}
    for code, art in r["ohlcv"].items():
        prep = pd.read_csv(WORK / "prep" / f"{group}_{code}.csv", index_col=0, parse_dates=True)
        common = prep.index.intersection(art.index)
        out[code] = bool(np.allclose(prep.loc[common, "close"].astype(float),
                                     art.loc[common, "close"].astype(float), rtol=1e-5, atol=1e-8))
    return out


def load_engine(name):
    rd = RUNS / name
    spec = importlib.util.spec_from_file_location("an_" + name.replace("-", "_"),
                                                  rd / "code" / "signal_engine.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flip_mask_match(name, code):
    """Recompute signal flips on the run's ARTIFACT data; compare execution
    dates against the configured mask (batch1 st-0009 decisive check)."""
    r = load_run(name)
    mod = load_engine(name)
    dm = {c: df for c, df in r["ohlcv"].items()}
    tgt = mod.SignalEngine().generate(dm)[code]
    idx = r["ohlcv"][code].index
    vals = tgt.reindex(idx).to_numpy()
    fe = None
    cfg = r["cfg"]
    if "warmup_bars" in cfg:
        fe = cfg["warmup_bars"]
    else:
        ev = pd.Timestamp(cfg["evaluation_start_date"])
        fe = int(idx.get_loc(idx[idx >= ev][0]))
    flips = {idx[i + 1].strftime("%Y-%m-%d") for i in range(1, len(vals))
             if abs(vals[i] - vals[i - 1]) > 1e-9 and i + 1 < len(vals)}
    expected = flips | {idx[fe].strftime("%Y-%m-%d")}
    return expected == set(cfg["rebalance_mask"]), len(flips)


def monthly_decile_spread(ohlcv, exclude, q, eval_start, ascending_low=True):
    """Research-grade zero-cost monthly quantile spread. Formation at month-end
    m on past-1m returns (reversal) -- caller passes formation matrix; here we
    compute formation = me/me.shift(1)-1 and forward = me.shift(-1)/me-1.
    Monthly formation + 1-month holding => forward windows NON-OVERLAPPING."""
    codes = [c for c in ohlcv if c not in exclude]
    closes = pd.DataFrame({c: ohlcv[c]["close"].astype(float) for c in codes}).sort_index()
    me = closes.resample("ME").last()
    formation = me / me.shift(1) - 1.0
    forward = me.shift(-1) / me - 1.0
    rows = []
    eval_period = pd.Period(eval_start[:7], freq="M")
    for i in range(len(me)):
        d = me.index[i]
        if (d.to_period("M") + 1) < eval_period:
            continue
        f = formation.iloc[i]
        valid = f[np.isfinite(f) & (f > -1.0)]
        if len(valid) < 50:
            continue
        n_q = max(1, int(np.ceil(len(valid) * q)))
        ordered = valid.sort_values(ascending=True, kind="mergesort")
        low = list(ordered.index[:n_q])
        high = list(ordered.index[-n_q:])
        fwd = forward.iloc[i]
        lo_ret = float(fwd[low].mean())
        hi_ret = float(fwd[high].mean())
        if not np.isfinite(lo_ret) or not np.isfinite(hi_ret):
            continue
        hold_month = (d.to_period("M") + 1)
        rows.append({"formation_month_end": str(d.date()), "holding_month": str(hold_month),
                     "n_valid": int(len(valid)), "n_per_leg": n_q,
                     "low_leg_fwd": lo_ret, "high_leg_fwd": hi_ret,
                     "low_minus_high": lo_ret - hi_ret})
    df = pd.DataFrame(rows)
    return df


def spread_stats(df, col):
    x = df[col].to_numpy()
    t_naive, p_naive = stats.ttest_1samp(x, 0.0)
    months = pd.PeriodIndex(df["holding_month"], freq="M")
    jan = x[months.month == 1]
    nonjan = x[months.month != 1]
    mid = len(x) // 2
    return {
        "n_months": int(len(x)),
        "mean_monthly": round(float(x.mean()), 6),
        "t_naive": round(float(t_naive), 4), "p_naive": round(float(p_naive), 6),
        "nw_lag1": nw_mean_t(x, 1), "nw_lag3": nw_mean_t(x, 3),
        "non_overlapping_note": "monthly formation, 1-month holding: forward windows disjoint by construction; NW guards residual serial correlation",
        "january_mean": round(float(jan.mean()), 6) if len(jan) else None,
        "january_n": int(len(jan)),
        "non_january_mean": round(float(nonjan.mean()), 6) if len(nonjan) else None,
        "first_half_mean": round(float(x[:mid].mean()), 6),
        "second_half_mean": round(float(x[mid:].mean()), 6),
        "last_month_partial": "final holding month ends at last data bar (2026-11-25), not a full calendar month",
    }


def main():
    reports = {}

    # ---------------- st-0004 ------------------------------------------------
    long_rep, rl = base_report("st0004-tsmom-long", "us")
    ls_rep, rls = base_report("st0004-tsmom-ls", "us")
    ew_rep, rew = base_report("st0004-bench-ew", "us")
    long_rep["benchmark_ew_monthly_rebalanced"] = {
        "engine_metrics": clean_metrics(rew["metrics"]),
        "subperiods": ew_rep["strategy_subperiods"],
        "year_returns": ew_rep["strategy_year_returns"],
    }
    long_rep["research_sensitivity_long_short"] = {
        "engine_metrics": clean_metrics(rls["metrics"]),
        "subperiods": ls_rep["strategy_subperiods"],
        "delta_total_return_vs_long_only": round(float(rls["metrics"]["total_return"] - rl["metrics"]["total_return"]), 6),
        "declaration": "research-grade sensitivity: short leg borrow cost/availability NOT modeled; not the entry's bounded version",
    }
    eq = rl["equity"]
    long_rep["window_2022"] = {
        "strategy_long": sub_window(eq, "2022-01-01", "2022-12-31", 252),
        "strategy_ls": sub_window(rls["equity"], "2022-01-01", "2022-12-31", 252),
        "ew_benchmark": sub_window(rew["equity"], "2022-01-01", "2022-12-31", 252),
        "bh_SPY": sub_window(bh_equity(rl["ohlcv"]["SPY.US"], eq.index, 252)[0],
                             "2022-01-01", "2022-12-31", 252),
    }
    tp = rl["targets"]
    invested = tp.sum(axis=1)
    long_rep["avg_target_invested_fraction"] = round(float(invested.mean()), 4)
    month_first = tp.groupby(tp.index.to_period("M")).first()
    cap_bound = ((month_first.max(axis=1) >= 0.2999) & (month_first.sum(axis=1) < 0.999))
    long_rep["cap_bound_months_with_cash_residual"] = int(cap_bound.sum())
    long_rep["cash_yield_assumption"] = 0.0
    long_rep["data_identity_prep_vs_artifact"] = data_identity(rl, "etf")
    reports["st-0004"] = long_rep

    # ---------------- st-0014 ------------------------------------------------
    erc_rep, re = base_report("st0014-erc", "us")
    b60_rep, r60 = base_report("st0014-bench-6040", "us")
    erc_rep["benchmark_6040_quarterly"] = {
        "engine_metrics": clean_metrics(r60["metrics"]),
        "subperiods": b60_rep["strategy_subperiods"],
        "year_returns": b60_rep["strategy_year_returns"],
    }
    eq = re["equity"]
    spy_bh_eq, spy_bh = bh_equity(re["ohlcv"]["SPY.US"], eq.index, 252)
    erc_rep["window_2022_stress"] = {
        "strategy_erc": sub_window(eq, "2022-01-01", "2022-12-31", 252),
        "benchmark_6040": sub_window(r60["equity"], "2022-01-01", "2022-12-31", 252),
        "bh_SPY": sub_window(spy_bh_eq, "2022-01-01", "2022-12-31", 252),
    }
    m_erc = clean_metrics(re["metrics"])
    m_60 = clean_metrics(r60["metrics"])
    erc_rep["claim_checks"] = {
        "claim": "ERC max drawdown below SPY and 60/40; Sharpe not below 60/40",
        "mdd_erc": m_erc["max_drawdown"], "mdd_6040": m_60["max_drawdown"],
        "mdd_spy_bh": spy_bh["max_drawdown"],
        "mdd_below_spy": bool(m_erc["max_drawdown"] > spy_bh["max_drawdown"]),
        "mdd_below_6040": bool(m_erc["max_drawdown"] > m_60["max_drawdown"]),
        "sharpe_erc": m_erc["sharpe"], "sharpe_6040": m_60["sharpe"],
        "sharpe_ge_6040": bool(m_erc["sharpe"] >= m_60["sharpe"]),
        "note": "drawdowns are negative; 'below' means less negative (smaller magnitude)",
    }
    erc_rep["solver_diagnostics"] = json.loads((WORK / "st0014_solver_diagnostics.json").read_text())
    erc_rep["threshold_fixed_point"] = json.loads((WORK / "st0014_threshold_iterations.json").read_text())
    erc_rep["fills_outside_mask_and_terminal"] = fills_in_mask(re)
    erc_rep["data_identity_prep_vs_artifact"] = data_identity(re, "etf")
    reports["st-0014"] = erc_rep

    # ---------------- st-0011 ------------------------------------------------
    st11 = {}
    for mkt, mname in (("us", "us"), ("crypto", "crypto")):
        for sem in ("stateful", "stateless"):
            name = f"st0011-{mname}-{sem}"
            rep, r = base_report(name, mkt)
            tr = r["trades"]
            exits = tr[tr["event"] == "exit"].copy()
            codes = r["cfg"]["codes"]
            a, b = codes
            ea = exits[exits["code"] == a].set_index("timestamp")
            eb = exits[exits["code"] == b].set_index("timestamp")
            common_ts = ea.index.intersection(eb.index)
            pair_ret = (pd.to_numeric(ea.loc[common_ts, "return_pct"]) +
                        pd.to_numeric(eb.loc[common_ts, "return_pct"])) / 200.0
            pair_ret = pair_ret.dropna()
            if len(pair_ret) > 2:
                t, p = stats.ttest_1samp(pair_ret, 0.0)
                rep["pair_roundtrip_stats"] = {
                    "n_roundtrips": int(len(pair_ret)),
                    "mean_pair_return": round(float(pair_ret.mean()), 6),
                    "t_vs_zero": round(float(t), 4), "p": round(float(p), 6),
                    "win_rate": round(float((pair_ret > 0).mean()), 4),
                    "note": "one pair position at a time -> roundtrips sequential and non-overlapping; pair return = mean of two leg returns (50/50); borrow/funding costs NOT included",
                }
            tp = r["targets"]
            sa = tp[a]
            rep["state_occupancy"] = {
                "long_pair_fraction": round(float((sa > 0.1).mean()), 4),
                "short_pair_fraction": round(float((sa < -0.1).mean()), 4),
                "flat_fraction": round(float((sa.abs() <= 0.1).mean()), 4),
            }
            rep["fills_outside_mask_and_terminal"] = fills_in_mask(r)
            rep["data_identity_prep_vs_artifact"] = data_identity(r, "etf" if mkt == "us" else "okx")
            match, nflips = flip_mask_match(name, a)
            rep["flip_dates_match_mask_on_artifact_data"] = match
            rep["n_signal_flips"] = nflips
            if sem == "stateful":
                mod = load_engine(name)
                dm = r["ohlcv"]
                ca = dm[a]["close"].astype(float)
                cb = dm[b]["close"].astype(float)
                common = ca.index.intersection(cb.index)
                ratio = ca.loc[common] / cb.loc[common]
                z = (ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std()
                zv = z.to_numpy()
                state, held, forced, exits_total = 0, 0, 0, 0
                for i in range(len(common)):
                    zi = zv[i]
                    if state != 0:
                        held += 1
                        if (np.isfinite(zi) and abs(zi) < 0.5) or held >= 60:
                            if held >= 60 and not (np.isfinite(zi) and abs(zi) < 0.5):
                                forced += 1
                            exits_total += 1
                            state, held = 0, 0
                    elif np.isfinite(zi):
                        if zi <= -2.0:
                            state, held = 1, 0
                        elif zi >= 2.0:
                            state, held = -1, 0
                rep["forced_exit_60bar_count"] = forced
                rep["total_exit_signals"] = exits_total
            st11[f"{mname}_{sem}"] = rep
    # cointegration on prep data (full common history) + evaluation window
    for mkt, a, b, group in (("us", "KO.US", "PEP.US", "etf"),
                             ("crypto", "BTC-USDT", "ETH-USDT", "okx")):
        da = pd.read_csv(WORK / "prep" / f"{group}_{a}.csv", index_col=0, parse_dates=True)
        db = pd.read_csv(WORK / "prep" / f"{group}_{b}.csv", index_col=0, parse_dates=True)
        common = da.index.intersection(db.index)
        la = np.log(da.loc[common, "close"].astype(float))
        lb = np.log(db.loc[common, "close"].astype(float))
        full = engle_granger(la, lb)
        full["window"] = [str(common[0].date()), str(common[-1].date())]
        ev_start = "2014-09-01" if mkt == "us" else "2018-01-30"
        mask = common >= pd.Timestamp(ev_start)
        ev = engle_granger(la[mask], lb[mask])
        ev["window"] = [str(common[mask][0].date()), str(common[mask][-1].date())]
        corr = float(da.loc[common, "close"].pct_change().corr(db.loc[common, "close"].pct_change()))
        st11[f"{mkt}_cointegration"] = {"full_history": full, "evaluation_window": ev,
                                        "daily_return_correlation": round(corr, 6),
                                        "declaration": "correlation != cointegration; ratio may drift structurally (entry limitation)"}
    us_sf = st11["us_stateful"]["engine_metrics"]
    us_ss = st11["us_stateless"]["engine_metrics"]
    cr_sf = st11["crypto_stateful"]["engine_metrics"]
    cr_ss = st11["crypto_stateless"]["engine_metrics"]
    st11["semantics_delta"] = {
        "us_total_return_stateful_minus_stateless": round(us_sf["total_return"] - us_ss["total_return"], 6),
        "us_trade_count_stateful": us_sf["trade_count"], "us_trade_count_stateless": us_ss["trade_count"],
        "crypto_total_return_stateful_minus_stateless": round(cr_sf["total_return"] - cr_ss["total_return"], 6),
        "crypto_trade_count_stateful": cr_sf["trade_count"], "crypto_trade_count_stateless": cr_ss["trade_count"],
        "declaration": "skill text state-machine vs example stateless code are different strategies; results not interchangeable",
    }
    reports["st-0011"] = st11

    # ---------------- st-0007 ------------------------------------------------
    rev_rep, rr = base_report("st0007-reversal", "us")
    ew_rep7, rew7 = base_report("st0007-bench-ew", "us")
    rev_rep["benchmark_ew_pool_monthly"] = {
        "engine_metrics": clean_metrics(rew7["metrics"]),
        "subperiods": ew_rep7["strategy_subperiods"],
        "year_returns": ew_rep7["strategy_year_returns"],
        "note": "503-name equal-weight monthly rebalance, same window/costs; also reused as st-0008 pool benchmark (declared)",
    }
    spread7 = monthly_decile_spread(rr["ohlcv"], {"SPY.US"}, 0.1, "2014-09-01")
    spread7.to_csv(WORK / "st0007_decile_monthly_spread.csv", index=False)
    rev_rep["research_spread_losers_minus_winners"] = spread_stats(spread7, "low_minus_high")
    rev_rep["research_spread_losers_only_fwd"] = spread_stats(spread7, "low_leg_fwd")
    rev_rep["research_spread_winners_only_fwd"] = spread_stats(spread7, "high_leg_fwd")
    eq = rr["equity"]
    rev_rep["window_2022"] = {
        "strategy": sub_window(eq, "2022-01-01", "2022-12-31", 252),
        "ew_pool": sub_window(rew7["equity"], "2022-01-01", "2022-12-31", 252),
        "bh_SPY": sub_window(bh_equity(rr["ohlcv"]["SPY.US"], eq.index, 252)[0],
                             "2022-01-01", "2022-12-31", 252),
    }
    rev_rep["survivorship_declaration"] = "current 503 constituent snapshot applied to full history (st-0002 precedent); late-IPO names enter when data exists; delisted names absent"
    reports["st-0007"] = rev_rep

    # ---------------- st-0008 ------------------------------------------------
    lv_rep, rv = base_report("st0008-lowvol", "us")
    lv_rep["benchmark_ew_pool_monthly_reused"] = {
        "run": "st0007-bench-ew",
        "engine_metrics": clean_metrics(rew7["metrics"]),
        "note": "identical pool/window/costs/data basis; reuse declared",
    }
    # quintile spread needs 20-day vol formation, not 1-month returns: rebuild
    codes = [c for c in rv["ohlcv"] if c != "SPY.US"]
    closes = pd.DataFrame({c: rv["ohlcv"][c]["close"].astype(float) for c in codes}).sort_index()
    rets = closes.pct_change(fill_method=None)
    vol = rets.rolling(20, min_periods=20).std() * np.sqrt(252.0)
    vol_me = vol.resample("ME").last()
    me = closes.resample("ME").last()
    forward = me.shift(-1) / me - 1.0
    rows = []
    sector_map = {}
    try:
        cons = pd.read_csv(WORK / "sp500_constituents.csv")
        sector_map = {r["Symbol"] + ".US": r["GICS Sector"] for _, r in cons.iterrows()}
    except Exception:
        pass
    sector_weights_sum = {}
    n_months = 0
    for i in range(len(vol_me)):
        d = vol_me.index[i]
        if d < pd.Timestamp("2014-08-01"):
            continue
        row = vol_me.iloc[i]
        valid = row[np.isfinite(row) & (row > 0)]
        if len(valid) < 50:
            continue
        n_q = max(1, int(np.ceil(len(valid) * 0.2)))
        ordered = valid.sort_values(ascending=True, kind="mergesort")
        low = list(ordered.index[:n_q])
        high = list(ordered.index[-n_q:])
        fwd = forward.iloc[i]
        lo_ret, hi_ret = float(fwd[low].mean()), float(fwd[high].mean())
        if not np.isfinite(lo_ret) or not np.isfinite(hi_ret):
            continue
        hold_month = d.to_period("M") + 1
        rows.append({"formation_month_end": str(d.date()), "holding_month": str(hold_month),
                     "n_valid": int(len(valid)), "n_per_leg": n_q,
                     "low_leg_fwd": lo_ret, "high_leg_fwd": hi_ret,
                     "low_minus_high": lo_ret - hi_ret})
        n_months += 1
        for c in low:
            s = sector_map.get(c, "Unknown")
            sector_weights_sum[s] = sector_weights_sum.get(s, 0.0) + 1.0 / len(low)
    spread8 = pd.DataFrame(rows)
    spread8.to_csv(WORK / "st0008_quintile_monthly_spread.csv", index=False)
    lv_rep["research_spread_low_minus_high"] = spread_stats(spread8, "low_minus_high")
    lv_rep["research_spread_low_only_fwd"] = spread_stats(spread8, "low_leg_fwd")
    if sector_weights_sum and n_months:
        avg = {s: w / n_months for s, w in sector_weights_sum.items()}
        tot = sum(avg.values())
        avg = {s: w / tot for s, w in avg.items()}
        top = sorted(avg.items(), key=lambda kv: -kv[1])
        pool_sector = {}
        for c in codes:
            s = sector_map.get(c, "Unknown")
            pool_sector[s] = pool_sector.get(s, 0.0) + 1.0 / len(codes)
        lv_rep["sector_concentration"] = {
            "low_vol_portfolio_avg_sector_weights": {s: round(w, 4) for s, w in top},
            "top3_sector_weight": round(sum(w for _, w in top[:3]), 4),
            "hhi": round(sum(w * w for w in avg.values()), 4),
            "pool_top3_sector_weight": round(sum(sorted(pool_sector.values(), reverse=True)[:3]), 4),
            "source": "GitHub datasets s-and-p-500-companies data/constituents.csv GICS Sector (fetched this task)",
            "note": "equal-weight cohort average over evaluation months; industry neutrality NOT modeled (entry limitation)",
        }
    eq = rv["equity"]
    lv_rep["window_2022"] = {
        "strategy": sub_window(eq, "2022-01-01", "2022-12-31", 252),
        "ew_pool": sub_window(rew7["equity"], "2022-01-01", "2022-12-31", 252),
        "bh_SPY": sub_window(bh_equity(rv["ohlcv"]["SPY.US"], eq.index, 252)[0],
                             "2022-01-01", "2022-12-31", 252),
    }
    lv_rep["proxy_declaration"] = "20-day TOTAL realized volatility proxy; paper signal is FF3 idiosyncratic volatility; Ken French upgrade optional, not performed"
    lv_rep["survivorship_declaration"] = "current 503 constituent snapshot applied to full history (st-0002 precedent)"
    reports["st-0008"] = lv_rep

    # ---------------- st-0012 ------------------------------------------------
    st12 = {}
    for mkt, mname in (("us", "us"), ("crypto", "crypto")):
        name = f"st0012-{mname}"
        rep, r = base_report(name, mkt)
        nocost_name = f"st0012-{mname}-nocost"
        nc = load_run(nocost_name)
        ann = ANN[mkt]
        rep["zero_cost_variant"] = {
            "engine_metrics": clean_metrics(nc["metrics"]),
            "jitter_cost_total_return_drag": round(float(nc["metrics"]["total_return"] - r["metrics"]["total_return"]), 6),
            "note": "same signal/mask; costs removed (US slippage 0; crypto commission+slippage 0)",
        }
        rep["n_signal_flips"] = len(r["cfg"]["rebalance_mask"]) - 1
        rep["fills_outside_mask_and_terminal"] = fills_in_mask(r)
        rep["data_identity_prep_vs_artifact"] = data_identity(r, "etf" if mkt == "us" else "okx")
        match, _ = flip_mask_match(name, r["cfg"]["codes"][0])
        rep["flip_dates_match_mask_on_artifact_data"] = match
        code = r["cfg"]["codes"][0]
        close = r["ohlcv"][code]["close"].astype(float)
        ret = close.pct_change(fill_method=None)
        hv = ret.rolling(20, min_periods=20).std() * np.sqrt(ann)
        pct = hv.rolling(120, min_periods=120).rank(pct=True) * 100.0
        fwd20 = close.shift(-20) / close - 1.0
        df = pd.DataFrame({"pct": pct, "fwd20": fwd20}).dropna()
        df = df.loc[df.index >= r["equity"].index[0]]
        low = df[df["pct"] < 20.0]["fwd20"]
        high = df[df["pct"] > 80.0]["fwd20"]
        mid = df[(df["pct"] >= 20.0) & (df["pct"] <= 80.0)]["fwd20"]
        stride = df.iloc[::20]
        sl = stride[stride["pct"] < 20.0]["fwd20"]
        sh = stride[stride["pct"] > 80.0]["fwd20"]
        welch_full = stats.ttest_ind(low, high, equal_var=False)
        welch_stride = stats.ttest_ind(sl, sh, equal_var=False) if len(sl) > 2 and len(sh) > 2 else None
        rep["forward_return_separation_fwd20"] = {
            "low_state": {"n": int(len(low)), "mean_fwd20": round(float(low.mean()), 6),
                          "nw_lag20": nw_mean_t(low.to_numpy(), 20)},
            "high_state": {"n": int(len(high)), "mean_fwd20": round(float(high.mean()), 6),
                           "nw_lag20": nw_mean_t(high.to_numpy(), 20)},
            "mid_state": {"n": int(len(mid)), "mean_fwd20": round(float(mid.mean()), 6)},
            "low_minus_high_mean": round(float(low.mean() - high.mean()), 6),
            "welch_t_full_overlap": round(float(welch_full.statistic), 4),
            "welch_p_full_overlap": round(float(welch_full.pvalue), 6),
            "non_overlapping_stride20": {
                "low_n": int(len(sl)), "high_n": int(len(sh)),
                "low_mean": round(float(sl.mean()), 6) if len(sl) else None,
                "high_mean": round(float(sh.mean()), 6) if len(sh) else None,
                "welch_t": round(float(welch_stride.statistic), 4) if welch_stride else None,
                "welch_p": round(float(welch_stride.pvalue), 6) if welch_stride else None,
                "note": "fixed 20-bar stride from evaluation start -> disjoint forward windows; state assignment at stride dates",
            },
            "state_day_fractions": {"low": round(float((df["pct"] < 20).mean()), 4),
                                     "high": round(float((df["pct"] > 80).mean()), 4)},
            "declaration": "directional claim weak by skill's own warning (volatility is not direction); overlapping naive t inflated, NW + stride reported",
        }
        if mkt == "us":
            rep["window_2022"] = {
                "strategy": sub_window(r["equity"], "2022-01-01", "2022-12-31", ann),
                "bh": sub_window(bh_equity(r["ohlcv"][code], r["equity"].index, ann)[0],
                                 "2022-01-01", "2022-12-31", ann),
            }
        st12[mname] = rep
    reports["st-0012"] = st12

    for key, rep in reports.items():
        (OUT / f"{key.replace('-', '')}_analysis.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("ANALYSIS WRITTEN:", sorted(p.name for p in OUT.glob("*_analysis.json")))


if __name__ == "__main__":
    main()
