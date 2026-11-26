"""st-0013 month-effect calendar timing (long-only), literal implementation.

Entry (verbatim): 每月最后一个交易日收盘按下一自然月的月份号确定目标权重——
下一月 ∈ bullish_months → 1.0，次月第一个交易日开盘建仓；看空月与中性月 → 0。
bullish_months = (11, 12, 1, 2, 3, 4) (VT seasonal skill default / Sell-in-May variant).
use_weekday=False. Long-only, no leverage, no intra-month stops.
Implementation: every bar carries its own month's weight EXCEPT the last
trading day of month m, which carries month m+1's weight; the engine's 1-bar
delay then executes exactly at month m+1's first trading day open.
"""
import numpy as np
import pandas as pd

BULLISH_MONTHS = (11, 12, 1, 2, 3, 4)


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            idx = close.index
            w = np.isin(idx.month, BULLISH_MONTHS).astype(float)
            out = pd.Series(w, index=idx)
            last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
            for d in last_days:
                next_month = (pd.Timestamp(d) + pd.offsets.MonthBegin(1)).month
                out.loc[d] = 1.0 if next_month in BULLISH_MONTHS else 0.0
            targets[code] = pd.Series(out.to_numpy(), index=idx, name=code)
        return targets
