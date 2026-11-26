"""st-0007 Jegadeesh (1990) 1-month short-term reversal, S&P500 long-only
bounded version, literal rule implementation.

Entry (verbatim): 每月末对 S&P500 当前成分股（503 只快照）按过去 1 个月收益
（上月末至本月末，复权收盘）横截面排序，买入最低十分位（losers）；次月首个交易日
开盘建仓；只做多，不加杠杆。等权，单票上限 5%（st-0002 惯例）。
Formation: r_i(m) = me_close_i(m)/me_close_i(m-1) - 1 (no skip week; monthly
convention per entry). Losers = ascending sort, lowest ceil(n_valid*0.1).
Cohort formed at month-end m is held during month m+1 (K=1).
Timing (st-0002 precedent): bar k carries the portfolio for calendar month
period(k+1), which was formed at the last close of month period(k); the engine
1-bar delay + rebalance_mask=MS executes it at month m+1's first trading day
open. No output shift. SPY.US is a zero-weight benchmark carrier, excluded
from the ranking universe. Warmup: names without a finite formation return
are excluded; <10 valid names -> cash.
"""
import numpy as np
import pandas as pd

SINGLE_NAME_CAP = 0.05
MIN_VALID_NAMES = 10
EXCLUDE = {"SPY.US"}
DECILE = 0.1


class SignalEngine:
    def generate(self, data_map):
        codes = [c for c in data_map if c not in EXCLUDE]
        closes = pd.DataFrame({c: data_map[c]["close"].astype(float) for c in codes}).sort_index()
        me = closes.resample("ME").last()
        formation = me / me.shift(1) - 1.0
        monthly_weights = np.zeros((len(me), len(codes)))
        col = {c: j for j, c in enumerate(codes)}
        prev_losers = []
        for i in range(len(me)):
            w = np.zeros(len(codes))
            for c in prev_losers:
                w[col[c]] = 1.0 / len(prev_losers)
            monthly_weights[i] = np.minimum(w, SINGLE_NAME_CAP)
            row = formation.iloc[i]
            valid = row[np.isfinite(row) & (row > -1.0)]
            if len(valid) < MIN_VALID_NAMES:
                prev_losers = []
                continue
            n_dec = max(1, int(np.ceil(len(valid) * DECILE)))
            ordered = valid.sort_values(ascending=True, kind="mergesort")
            prev_losers = list(ordered.index[:n_dec])
        wmap = {p: monthly_weights[i] for i, p in enumerate(me.index.to_period("M"))}
        all_codes = list(data_map.keys())
        full = pd.DataFrame({c: data_map[c]["close"].astype(float) for c in all_codes}).sort_index()
        bar_periods = full.index.to_period("M")
        vals = np.zeros((len(full), len(all_codes)))
        zero = np.zeros(len(all_codes))
        jmap = {c: j for j, c in enumerate(all_codes)}
        for k in range(len(full)):
            p = bar_periods[k + 1] if k + 1 < len(full) else bar_periods[k]
            w = wmap.get(p, zero)
            for c in codes:
                vals[k, jmap[c]] = w[col[c]]
        return {c: pd.Series(vals[:, j], index=full.index, name=c) for j, c in enumerate(all_codes)}
