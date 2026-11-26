"""st-0005 Antonacci dual momentum GEM, literal rule implementation.

Entry (verbatim): 每月末比较 SPY 与 ACWX 过去 12 个月总收益，取较高者为相对动量
赢家；若赢家 12 个月总收益 > BIL 同期收益（绝对动量为正），次月首个交易日开盘
满仓持有赢家；否则满仓持有 AGG.US。只做多，不加杠杆，三选一。
Warmup: 前 12 个月信号未定义持现金。月度评估无跳月。
Tie-break (operational, declared): equal 12-month returns -> SPY wins.
Timing: engine built-in 1-bar delay executes month-end decision at next month
first trading day open. No manual shift.
"""
import numpy as np
import pandas as pd

LOOKBACK_MONTHS = 12
FALLBACK = "AGG.US"


class SignalEngine:
    def generate(self, data_map):
        ref = data_map["SPY.US"]["close"].astype(float)
        idx = ref.index
        last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
        me = {}
        for c, df in data_map.items():
            me[c] = df["close"].astype(float).reindex(last_days, method="ffill")
        r12 = {c: me[c] / me[c].shift(LOOKBACK_MONTHS) - 1.0 for c in me}
        decisions = []
        for d in last_days:
            r_spy = r12["SPY.US"].loc[d]
            r_acwx = r12["ACWX.US"].loc[d]
            r_bil = r12["BIL.US"].loc[d]
            if pd.isna(r_spy) or pd.isna(r_acwx) or pd.isna(r_bil):
                decisions.append(None)  # warmup -> cash
                continue
            winner = "SPY.US" if r_spy >= r_acwx else "ACWX.US"
            r_win = r12[winner].loc[d]
            decisions.append(winner if r_win > r_bil else FALLBACK)
        dec = pd.Series(decisions, index=pd.DatetimeIndex(last_days))
        daily = dec.reindex(idx, method="ffill")
        targets = {}
        for c in data_map:
            w = (daily == c).astype(float).fillna(0.0)
            targets[c] = pd.Series(w.to_numpy(), index=idx, name=c)
        return targets
