"""st-0004 time-series momentum 12-1 (Moskowitz-Ooi-Pedersen 2012),
ETF long-only bounded version, literal rule implementation.

Entry (verbatim): 八资产 ETF 池 SPY/EFA/EEM/IEF/GLD/DBC/VNQ/UUP；每月末计算各资产
过去 12 个月总收益减 BIL 同期收益的超额收益；超额 > 0 的资产进入多头候选，按 60 日
已实现波动率倒数分配权重（次月首个交易日开盘建仓）；超额 <= 0 的资产持现金。
只做多，不加杠杆。MODE='ls' 为研究级多空敏感性（sign<0 做空，借券成本未建模）。
Position sizing (verbatim): w_i = (1/sigma_i)/sum(1/sigma_j)，sigma_i = 过去 60 个
交易日日收益率标准差*sqrt(252)；单资产上限 30%（超限截断后归一，迭代水填；候选不足
4 只时上限约束使权重和 <1，余额持现金，不加杠杆）。
Warmup: 前 12 个月信号未定义持现金；60 日波动率未定义的资产剔除出候选。
Timing: month-end bar carries its own month-end decision; engine built-in 1-bar
delay executes it at the next month's first trading day open. rebalance_mask=MS.
BIL.US is signal-only (target weight always 0; cash yield assumed 0).
"""
import numpy as np
import pandas as pd

MODE = "long"
CAP = 0.30
LOOKBACK_MONTHS = 12
VOL_WINDOW = 60
ANN = 252.0
ASSETS = ['SPY.US', 'EFA.US', 'EEM.US', 'IEF.US', 'GLD.US', 'DBC.US', 'VNQ.US', 'UUP.US']
BIL = "BIL.US"


def capped_invvol(raw_w, cap):
    """Iterative truncate-and-renormalize (water-filling) onto the cap.

    Returns weights with each <= cap; if every name is capped the sum stays
    below 1 (residual is cash, no leverage). Sign-preserving for the ls mode.
    """
    signs = np.sign(raw_w)
    w = np.abs(raw_w)
    if w.sum() <= 0:
        return raw_w
    w = w / w.sum()
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
    return signs * w


class SignalEngine:
    def generate(self, data_map):
        ref = data_map["SPY.US"]["close"].astype(float)
        idx = ref.index
        last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
        me = {}
        vol_me = {}
        for c in data_map:
            close = data_map[c]["close"].astype(float)
            me[c] = close.reindex(last_days, method="ffill")
            ret = close.pct_change()
            vol = ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(ANN)
            vol_me[c] = vol.reindex(last_days, method="ffill")
        r12 = {c: me[c] / me[c].shift(LOOKBACK_MONTHS) - 1.0 for c in me}
        excess = {c: r12[c] - r12[BIL] for c in ASSETS}

        decisions = {c: np.zeros(len(last_days)) for c in data_map}
        for i in range(len(last_days)):
            longs, shorts, vols = [], [], []
            for c in ASSETS:
                e = excess[c].iloc[i]
                v = vol_me[c].iloc[i]
                if not np.isfinite(e) or not np.isfinite(v) or v <= 0:
                    continue
                if e > 0:
                    longs.append(c); vols.append(v)
                elif MODE == "ls" and e < 0:
                    shorts.append(c); vols.append(v)
            cands = longs + shorts
            if not cands:
                continue
            inv = 1.0 / np.array(vols)
            raw = inv / inv.sum()
            signed = np.array([1.0 if c in longs else -1.0 for c in cands])
            w = capped_invvol(raw * signed, CAP)
            for c, wi in zip(cands, w):
                decisions[c][i] = float(wi)
        targets = {}
        for c in data_map:
            s = pd.Series(decisions[c], index=pd.DatetimeIndex(last_days))
            daily = s.reindex(idx, method="ffill").fillna(0.0)
            targets[c] = pd.Series(daily.to_numpy(), index=idx, name=c)
        return targets
