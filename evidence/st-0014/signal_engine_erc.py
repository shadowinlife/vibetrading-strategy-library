"""st-0014 four-asset ETF risk parity (ERC), literal rule implementation.

Entry (verbatim): 每季度（2/5/8/11 月最后交易日收盘）用过去 60 个交易日日收益率
样本协方差矩阵求解等风险贡献（ERC）权重，次季度首个交易日（3/6/9/12 月）开盘按新
权重建仓/调仓；只做多，权重和=1，不加杠杆。单资产权重上限 60%（操作化默认，超限
截断后归一）；协方差窗口不足 60 日时沿用上次权重（暖机期等权 25% 起步）。
Solver: Spinu (2013) cyclical coordinate descent on the ERC fixed point
w_i <- (-b_i + sqrt(b_i^2 + 4 a_i * (w'Sigma w / n))) / (2 a_i), normalized each
sweep; convergence tolerance 1e-8 on max weight change (operational default).
Threshold rebalancing (|actual-target| >= 10pp -> next-open full re-pin) is
executed via the run's explicit rebalance_mask, computed by fixed-point
iteration on the engine's own positions.csv (see build_runs.py); the engine
itself only emits the quarterly target weights.
Timing: the quarter-signal bar (last trading day of Feb/May/Aug/Nov) carries the
new weights; engine 1-bar delay executes at the next bar open = first trading
day of Mar/Jun/Sep/Dec. No manual shift.
"""
import numpy as np
import pandas as pd

LOOKBACK = 60
CAP = 0.60
TOL = 1e-8
MAX_ITER = 10000
SIGNAL_MONTHS = (2, 5, 8, 11)
ASSETS = ['SPY.US', 'IEF.US', 'GLD.US', 'DBC.US']


def erc_weights(cov):
    """Long-only ERC via cyclical coordinate descent; returns (w, iters, delta)."""
    n = cov.shape[0]
    w = np.full(n, 1.0 / n)
    iters, delta = 0, float("inf")
    for it in range(MAX_ITER):
        iters = it + 1
        delta = 0.0
        for i in range(n):
            sw = cov @ w
            target = float(w @ sw) / n
            a = cov[i, i]
            b = float(sw[i]) - a * w[i]
            if a <= 0:
                continue
            disc = b * b + 4.0 * a * target
            w_new = (-b + np.sqrt(max(disc, 0.0))) / (2.0 * a)
            w_new = max(w_new, 1e-12)
            delta = max(delta, abs(w_new - w[i]))
            w[i] = w_new
        w = w / w.sum()
        if delta < TOL:
            break
    return w, iters, delta


def apply_cap(w, cap):
    w = w.copy()
    for _ in range(50):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = float((w[over] - cap).sum())
        w[over] = cap
        under = ~over
        if w[under].sum() <= 1e-12:
            break
        w[under] += excess * w[under] / w[under].sum()
    return w


class SignalEngine:
    def generate(self, data_map):
        closes = pd.DataFrame({c: data_map[c]["close"].astype(float) for c in ASSETS}).sort_index()
        idx = closes.index
        rets = closes.pct_change()
        last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
        sig_dates = [d for d in last_days if pd.Timestamp(d).month in SIGNAL_MONTHS]
        weights = np.full((len(idx), len(ASSETS)), 0.25)  # warmup equal weight
        current = np.full(len(ASSETS), 0.25)
        sig_ptr = 0
        for k in range(len(idx)):
            while sig_ptr < len(sig_dates) and idx[k] >= sig_dates[sig_ptr]:
                d = sig_dates[sig_ptr]
                loc = idx.get_loc(d)
                window = rets.iloc[loc - LOOKBACK + 1: loc + 1]
                if len(window) == LOOKBACK and window.notna().all().all():
                    cov = window.cov().to_numpy()
                    w, _, _ = erc_weights(cov)
                    current = apply_cap(w, CAP)
                # else: keep previous weights (entry warmup rule)
                sig_ptr += 1
            weights[k] = current
        return {c: pd.Series(weights[:, j], index=idx, name=c) for j, c in enumerate(ASSETS)}
