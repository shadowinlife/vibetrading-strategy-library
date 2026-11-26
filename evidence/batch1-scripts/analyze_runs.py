"""Cross-run analysis for harvest-validate-b1.

For every VT run: engine metrics + buy-and-hold benchmarks computed from the
run's OWN ohlcv artifacts (same data basis; B&H enters at the first evaluation
bar open, marks to last close, zero costs), half-window subperiods, calendar
year returns, and entry-specific checks:
  st-0003: 2022 subperiod, invested fraction
  st-0005: SPY B&H / 60-40 comparison, winner switches, fallback delta
  st-0006: trade-level t, cost drag 5bps vs 10bps, variant table
  st-0009: mask-execution verification, prep-vs-artifact data identity,
           SMA vs Wilder delta, B&H drawdown comparison, 2022 subperiod
  st-0013: monthly bull/bear statistics (naive t, low power declared)
Outputs JSON per entry under work/analysis/.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WORK = Path("/root/projects/harvest-validate-b1/work")
RUNS = Path("/root/.vibe-trading/runs/harvest-validate-b1")
OUT = WORK / "analysis"
OUT.mkdir(exist_ok=True)
ANN = {"us": 252, "hk": 252, "crypto": 365, "ashare": 252}


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
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        ohlcv[code] = df
    cfg = json.loads((rd / "config.json").read_text())
    return {"metrics": m, "equity": equity, "trades": trades, "ohlcv": ohlcv, "cfg": cfg, "rd": rd}


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
    """Buy at first evaluation bar open, hold to last close, zero costs."""
    o = df["open"].reindex(window)
    c = df["close"].reindex(window)
    first = o.first_valid_index()
    shares = 1_000_000.0 / float(o.loc[first])
    eq = shares * c
    eq = eq.loc[first:]
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
            "benchmark_return", "benchmark_kind", "benchmark_label",
            "rebalance_executed_bars", "dropped_target_adjustment_count",
            "position_adjustment", "rebalance_tolerance"]
    out = {}
    for k in keys:
        if k in m:
            v = m[k]
            out[k] = float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v
    return out


def market_of(name):
    if "crypto" in name:
        return "crypto"
    if "hk" in name:
        return "hk"
    if "st0010" in name:
        return "ashare"
    return "us"


def base_report(name):
    r = load_run(name)
    mkt = market_of(name)
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


def main():
    reports = {}

    # ---------------- st-0003 ------------------------------------------------
    gtaa, rg = base_report("st0003-gtaa")
    ew, re_ = base_report("st0003-bench-ew")
    gtaa["benchmark_ew_monthly_rebalanced"] = {
        "engine_metrics": clean_metrics(re_["metrics"]),
        "subperiods": ew["strategy_subperiods"],
        "year_returns": ew["strategy_year_returns"],
    }
    eq = rg["equity"]
    gtaa["window_2022"] = {
        "strategy": sub_window(eq, "2022-01-01", "2022-12-31", 252),
        "ew_benchmark": sub_window(re_["equity"], "2022-01-01", "2022-12-31", 252),
    }
    for code, df in rg["ohlcv"].items():
        gtaa["window_2022"][f"bh_{code}"] = sub_window(
            bh_equity(df, eq.index, 252)[0], "2022-01-01", "2022-12-31", 252)
    # invested fraction from target positions
    tp = pd.read_csv(rg["rd"] / "artifacts" / "target_positions.csv", index_col=0, parse_dates=True)
    gtaa["avg_target_invested_fraction"] = round(float(tp.sum(axis=1).mean()), 4)
    gtaa["cash_yield_assumption"] = 0.0
    reports["st-0003"] = gtaa

    # ---------------- st-0005 ------------------------------------------------
    gem, rgm = base_report("st0005-gem")
    bil, rbm = base_report("st0005-gem-bil")
    b6040, r60 = base_report("st0005-bench-6040")
    gem["variant_fallback_bil"] = {
        "engine_metrics": clean_metrics(rbm["metrics"]),
        "delta_total_return_vs_agg": round(float(rbm["metrics"]["total_return"] - rgm["metrics"]["total_return"]), 6),
        "note": "paper T-bill fallback variant; AGG is the book-GEM bounded default",
    }
    gem["benchmark_6040_monthly"] = {
        "engine_metrics": clean_metrics(r60["metrics"]),
        "subperiods": b6040["strategy_subperiods"],
    }
    # winner switches from target positions
    tp = pd.read_csv(rgm["rd"] / "artifacts" / "target_positions.csv", index_col=0, parse_dates=True)
    held = tp.idxmax(axis=1)
    switches = int((held != held.shift(1)).sum() - 1)
    gem["target_switches"] = switches
    gem["time_in_asset_fraction"] = {c: round(float((held == c).mean()), 4) for c in tp.columns}
    reports["st-0005"] = gem

    # ---------------- st-0006 ------------------------------------------------
    variants = {}
    for name in ("st0006-main", "st0006-thr5", "st0006-exit90", "st0006-nofilter", "st0006-main-10bps"):
        rep, r = base_report(name)
        variants[name] = rep
    main_rep = variants["st0006-main"]
    tr = load_run("st0006-main")["trades"]
    exits = tr[tr["event"] == "exit"]
    rets = pd.to_numeric(exits["return_pct"], errors="coerce").dropna() / 100.0
    t_stat, p_val = stats.ttest_1samp(rets, 0.0)
    main_rep["trade_level_stats"] = {
        "n_closed_trades": int(len(rets)),
        "mean_trade_return": round(float(rets.mean()), 6),
        "t_vs_zero": round(float(t_stat), 4),
        "p": round(float(p_val), 6),
        "caveat": "trade returns overlap in calendar time across sleeves; naive t",
    }
    m5 = load_run("st0006-main")["metrics"]
    m10 = load_run("st0006-main-10bps")["metrics"]
    main_rep["cost_sensitivity"] = {
        "slippage_5bps_total_return": round(float(m5["total_return"]), 6),
        "slippage_10bps_total_return": round(float(m10["total_return"]), 6),
        "drag_5bps_to_10bps": round(float(m5["total_return"] - m10["total_return"]), 6),
        "note": "zero-commission convention; 10bps/side doubles the round-1 cost assumption",
    }
    reports["st-0006"] = {"variants": variants, "headline": main_rep}

    # ---------------- st-0009 ------------------------------------------------
    st9 = {}
    for mkt in ("us", "hk", "crypto"):
        sma_name, wild_name = f"st0009-{mkt}-sma", f"st0009-{mkt}-wilder"
        sma, rs = base_report(sma_name)
        wild, rw = base_report(wild_name)
        ann = ANN[mkt]
        code = rs["cfg"]["codes"][0]
        cfg = rs["cfg"]
        # data identity: prep fetch vs run artifact
        prep = pd.read_csv(WORK / "prep" / f"{sma_name}_{code}.csv", index_col=0, parse_dates=True)
        art = rs["ohlcv"][code]
        common = prep.index.intersection(art.index)
        identical = bool(np.allclose(prep.loc[common, "close"].astype(float),
                                     art.loc[common, "close"].astype(float), rtol=1e-5, atol=1e-8))
        # decisive check: recompute the signal on the ARTIFACT data and compare
        # flip execution dates against the configured mask
        import importlib.util
        spec = importlib.util.spec_from_file_location("m_" + sma_name.replace("-", "_"),
                                                      rs["rd"] / "code" / "signal_engine.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tgt = mod.SignalEngine().generate({code: art})[code]
        aidx = art.index
        vals = tgt.to_numpy()
        flips = {aidx[i + 1].strftime("%Y-%m-%d") for i in range(1, len(vals))
                 if abs(vals[i] - vals[i - 1]) > 1e-9 and i + 1 < len(vals)}
        expected = flips | {aidx[cfg.get("warmup_bars", 0)].strftime("%Y-%m-%d")}
        mask_match = expected == set(cfg["rebalance_mask"])
        # mask execution verification
        cfg = rs["cfg"]
        mask = set(cfg["rebalance_mask"])
        fills = pd.read_json(rs["rd"] / "artifacts" / "fills.jsonl", lines=True)
        fill_dates = set(pd.to_datetime(fills["timestamp"]).dt.strftime("%Y-%m-%d"))
        last_day = str(rs["equity"].index[-1].date())
        outside = sorted(fill_dates - mask - {last_day})
        # signal activity: fraction of evaluation bars in expansion (target 0.5)
        tp = pd.read_csv(rs["rd"] / "artifacts" / "target_positions.csv", index_col=0, parse_dates=True)
        exp_frac = float((tp[code] < 0.9).mean())
        bh = sma["benchmarks_buy_and_hold"][code]
        st9[mkt] = {
            "sma": sma, "wilder": wild,
            "sma_vs_wilder_delta_total_return": round(float(rs["metrics"]["total_return"] - rw["metrics"]["total_return"]), 6),
            "data_identity_prep_vs_artifact": identical,
            "flip_dates_match_mask_on_artifact_data": mask_match,
            "fills_outside_mask_and_terminal": outside,
            "expansion_fraction_of_eval_bars": round(exp_frac, 4),
            "drawdown_strategy_vs_bh": {
                "strategy_sma": sma["engine_metrics"]["max_drawdown"],
                "strategy_wilder": wild["engine_metrics"]["max_drawdown"],
                "buy_and_hold": bh["max_drawdown"],
            },
            "window_2022": {
                "strategy_sma": sub_window(rs["equity"], "2022-01-01", "2022-12-31", ann),
                "bh": sub_window(bh_equity(rs["ohlcv"][code], rs["equity"].index, ann)[0],
                                 "2022-01-01", "2022-12-31", ann),
            },
            "warmup_note": "warmup_bars=500 deducted; ATR percentile needs 500 defined ATR20 values (first defined bar 519); undefined-signal bars hold 1.0 per entry",
        }
    reports["st-0009"] = st9

    # ---------------- st-0013 ------------------------------------------------
    main13, r13 = base_report("st0013-main")
    sell, rsm = base_report("st0013-sellmay")
    main13["variant_sell_in_may"] = {
        "engine_metrics": clean_metrics(rsm["metrics"]),
        "subperiods": sell["strategy_subperiods"],
        "months_held": [11, 12, 1, 2, 3, 4],
    }
    # monthly statistics from SPY ohlcv (month-end to month-end)
    spy = r13["ohlcv"]["SPY.US"]["close"]
    me = spy.groupby(spy.index.to_period("M")).last()
    mret = me.pct_change().dropna()
    mret = mret.loc[mret.index >= pd.Period("2014-09", "M")]
    bull = [1, 2, 3, 11, 12]
    months = mret.index.month
    b = mret[np.isin(months, bull)]
    s = mret[~np.isin(months, bull)]
    t_m, p_m = stats.ttest_ind(b, s, equal_var=False)
    main13["month_effect_stats"] = {
        "n_months": int(len(mret)),
        "bull_months_mean": round(float(b.mean()), 6),
        "other_months_mean": round(float(s.mean()), 6),
        "bull_n": int(len(b)), "other_n": int(len(s)),
        "welch_t": round(float(t_m), 4), "p": round(float(p_m), 6),
        "caveat": "~144 monthly observations, low power; calendar months overlap across years; naive t; skill default months have no literature anchor",
        "by_month_mean": {int(m): round(float(mret[months == m].mean()), 6) for m in range(1, 13)},
    }
    reports["st-0013"] = main13

    # ---------------- st-0010 ETF proxy --------------------------------------
    etf, retf = base_report("st0010-etf-510050")
    etf["note"] = ("510050.SH live-proxy comparison, VT china_a engine (T+1, 100-share lots, "
                   "commission 0.025% min 5 CNY, transfer fee 0.001%, ETF stamp-tax exempt, "
                   "slippage 0.1%/side); sina ETF daily UNADJUSTED (dividends excluded, declared); "
                   "signal from archived SSE margin snapshot + sina index, flip-date mask execution")
    reports["st-0010-etf"] = etf

    for key, rep in reports.items():
        (OUT / f"{key.replace('-', '')}_analysis.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("ANALYSIS WRITTEN:", sorted(p.name for p in OUT.glob("*_analysis.json")))


if __name__ == "__main__":
    main()
