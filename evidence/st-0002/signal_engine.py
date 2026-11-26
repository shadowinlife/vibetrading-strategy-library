"""st-0002 cross-sectional momentum (12-1), literal rule implementation.

Entry rules (verbatim): 每月末按过去 12 个月累计收益（跳过最近 1 个月，即
t-12 至 t-2 月）对股票池排序，买入最高十分位（winners）。
Exit rules: 持有 K 个月（K=6 经典）后平仓；每月滚动换仓，重叠组合：任一月份
持有最近 K 个月形成的 K 个子组合，每月平掉最旧一期。
Position sizing: 十分位组合内等权；单票权重上限 5%。

Variant choice (documented): long-only winners decile. The entry offers
"做空最低十分位（losers）或仅多头低配 losers"; the short leg is not modeled
(no borrow-cost data in this environment), so the long-only winners variant
is run. Losers-decile forward returns are computed separately in the analysis
script to test the winners>losers claim directly.

Formation (entry formula): formation_return = prod(1+r_m) - 1, m in [t-12, t-2]
= month_end_close[t-2] / month_end_close[t-13] - 1.

Timing: the VT engine shifts signals 1 bar (next-open execution) and the
rebalance_mask="MS" executes on the first bar of each month, reading the
signal from the previous bar. Therefore the signal on the LAST bar of month
m-1 carries the holding-month-m portfolio (cohorts formed at month-ends
m-6..m-1, all known at that close). No output shift is applied; the month
lookup below is a state computation, not a signal shift.
"""
import numpy as np
import pandas as pd

K = 6
SINGLE_NAME_CAP = 0.05
MIN_VALID_NAMES = 10


class SignalEngine:
    def generate(self, data_map):
        codes = list(data_map.keys())
        closes = pd.DataFrame({c: data_map[c]["close"].astype(float) for c in codes}).sort_index()
        me = closes.resample("ME").last()
        formation = me.shift(2) / me.shift(13) - 1.0

        cohort_winners = {}
        for i in range(len(me)):
            row = formation.iloc[i]
            valid = row[np.isfinite(row) & (row > -1.0)]
            if len(valid) < MIN_VALID_NAMES:
                cohort_winners[i] = []
                continue
            n_win = max(1, int(np.ceil(len(valid) * 0.1)))
            ordered = valid.sort_values(ascending=False, kind="mergesort")
            cohort_winners[i] = list(ordered.index[:n_win])

        monthly_weights = np.zeros((len(me), len(codes)))
        col = {c: j for j, c in enumerate(codes)}
        for i in range(len(me)):
            w = np.zeros(len(codes))
            for j in range(i - K, i):
                if j < 0:
                    continue
                win = cohort_winners.get(j) or []
                if not win:
                    continue
                per_name = (1.0 / K) / len(win)
                for c in win:
                    w[col[c]] += per_name
            monthly_weights[i] = np.minimum(w, SINGLE_NAME_CAP)

        wmap = {p: monthly_weights[i] for i, p in enumerate(me.index.to_period("M"))}
        bar_periods = closes.index.to_period("M")
        n_bars = len(closes)
        vals = np.zeros((n_bars, len(codes)))
        zero = np.zeros(len(codes))
        for k in range(n_bars):
            p = bar_periods[k + 1] if k + 1 < n_bars else bar_periods[k]
            vals[k] = wmap.get(p, zero)

        return {c: pd.Series(vals[:, j], index=closes.index, name=c) for j, c in enumerate(codes)}