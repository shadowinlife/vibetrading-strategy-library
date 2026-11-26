"""st-0012 HV-percentile low-vol entry (VT volatility skill), long-only bounded
version, literal rule implementation.

Entry (verbatim): HV = 日收益率 20 日滚动标准差*sqrt(252)（crypto sqrt(365)）；
百分位 = HV 在过去 120 日（含当日）的滚动百分位排名*100（rolling(120).rank(pct=True)
口径）；空仓且百分位 < 20 时次日开盘建仓至 1.0；持仓且百分位 > 80 时次日开盘清仓；
20-80 中间区维持当前仓位（锁存）；暖机期百分位 NaN 空仓。仅多头，高波做空腿不采纳。
Two-state 1.0/0 with latch: flip-date rebalance_mask executes each transition at
the next trading day open; no drift re-pinning between flips (batch1 st-0009
convention). Engine 1-bar delay, no manual shift.
"""
import numpy as np
import pandas as pd

HV_WINDOW = 20
PCT_WINDOW = 120
LOW_PCT = 20.0
HIGH_PCT = 80.0
ANN = 252.0


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            ret = close.pct_change()
            hv = ret.rolling(HV_WINDOW, min_periods=HV_WINDOW).std() * np.sqrt(ANN)
            pct = hv.rolling(PCT_WINDOW, min_periods=PCT_WINDOW).rank(pct=True) * 100.0
            pv = pct.to_numpy()
            state = np.zeros(len(close))
            holding = False
            for i in range(len(close)):
                p = pv[i]
                if not np.isfinite(p):
                    holding = False
                elif holding and p > HIGH_PCT:
                    holding = False
                elif not holding and p < LOW_PCT:
                    holding = True
                state[i] = 1.0 if holding else 0.0
            targets[code] = pd.Series(state, index=close.index, name=code)
        return targets
