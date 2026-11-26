"""st-0008 Ang et al. (2006) low-volatility anomaly, TOTAL-volatility proxy
bounded version, literal rule implementation.

Entry (verbatim): 每月末对 S&P500 当前成分股（503 只快照）计算过去 20 个交易日
日收益率标准差（总已实现波动率，年化*sqrt(252)），横截面升序排序取最低五分位；
次月首个交易日开盘等权买入；只做多，不加杠杆。单票上限 5%。
Proxy declaration: the paper's signal is FF3 IDIOSYNCRATIC volatility; this
bounded version uses 20-day total realized volatility (entry limitation kept).
Cohort formed at month-end m is held during month m+1; bar-mapping and timing
identical to st-0007 (st-0002 precedent). SPY.US zero-weight benchmark carrier.
"""
import numpy as np
import pandas as pd

SINGLE_NAME_CAP = 0.05
MIN_VALID_NAMES = 10
EXCLUDE = {"SPY.US"}
VOL_WINDOW = 20
ANN = 252.0
QUINTILE = 0.2


class SignalEngine:
    def generate(self, data_map):
        codes = [c for c in data_map if c not in EXCLUDE]
        closes = pd.DataFrame({c: data_map[c]["close"].astype(float) for c in codes}).sort_index()
        rets = closes.pct_change()
        vol = rets.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(ANN)
        vol_me = vol.resample("ME").last()
        monthly_weights = np.zeros((len(vol_me), len(codes)))
        col = {c: j for j, c in enumerate(codes)}
        prev_low = []
        for i in range(len(vol_me)):
            w = np.zeros(len(codes))
            for c in prev_low:
                w[col[c]] = 1.0 / len(prev_low)
            monthly_weights[i] = np.minimum(w, SINGLE_NAME_CAP)
            row = vol_me.iloc[i]
            valid = row[np.isfinite(row) & (row > 0)]
            if len(valid) < MIN_VALID_NAMES:
                prev_low = []
                continue
            n_q = max(1, int(np.ceil(len(valid) * QUINTILE)))
            ordered = valid.sort_values(ascending=True, kind="mergesort")
            prev_low = list(ordered.index[:n_q])
        wmap = {p: monthly_weights[i] for i, p in enumerate(vol_me.index.to_period("M"))}
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
