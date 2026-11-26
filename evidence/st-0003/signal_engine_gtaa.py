"""st-0003 Faber 10-month SMA GTAA, literal rule implementation.

Entry (verbatim): 五资产 ETF 池 SPY/EFA/IEF/GSG/VNQ 各 20% sleeve；每月最后一个
交易日收盘，任一资产收盘价 > 其 10 月 SMA（过去 10 个月末收盘均值）则该 sleeve
次月首个交易日开盘持有该资产，否则该 sleeve 转为现金；各资产独立判断，只做多。
Warmup: 前 10 个月末 SMA 未定义，该 sleeve 持现金。
Timing: VT daily engine fills a bar-close target at the NEXT bar open (built-in
1-bar delay), so the month-end decision executes at the next month's first
trading day open. No manual shift.
"""
import numpy as np
import pandas as pd

SLEEVE_WEIGHT = 0.2
SMA_MONTHS = 10


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            idx = close.index
            # actual last trading day of each calendar month
            last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
            me_close = close.loc[last_days]
            sma = me_close.rolling(SMA_MONTHS, min_periods=SMA_MONTHS).mean()
            state = (me_close > sma).astype(float)  # NaN SMA (warmup) -> False -> cash
            state.index = pd.DatetimeIndex(last_days)
            # month-end bar carries its own month's decision; earlier bars carry
            # the previous month-end decision (ffill). Engine shift executes the
            # month-end decision at the next bar open = next month first day.
            daily = state.reindex(idx, method="ffill").fillna(0.0)
            targets[code] = pd.Series(daily.to_numpy() * SLEEVE_WEIGHT, index=idx, name=code)
        return targets
