"""Build all VT backtest run dirs for harvest-validate-b2.

Each run dir gets config.json + code/signal_engine.py implementing the library
draft's rules VERBATIM (per-engine docstrings quote the entry). Conventions
inherited from batch1 (evidence/README-batch1.md):
  - VT daily engine fills a bar-close target at the NEXT bar open (built-in
    1-bar delay); no manual shift.
  - Monthly strategies: position_adjustment='rebalance' + rebalance_mask='MS'
    (inverse-vol / decile weights resize every month; 'hold' would drop
    same-direction resizes).
  - Two-state / latch strategies (st-0011, st-0012): 'rebalance' + explicit
    ISO-date rebalance_mask = next trading day after each signal flip, plus
    the first evaluation day. No drift re-pinning between flips.
  - st-0014 threshold rebalancing: two-pass fixed-point iteration on the
    engine's OWN positions.csv actual weights (quarterly-only mask first,
    then add |actual-target| >= 10pp trigger execution dates until stable).

Data for mask computation is read from work/prep/ (archived VT-loader fetch,
fetch_data.py); the runner re-fetches through the same loader path and hits
the task-local loader cache (VIBE_TRADING_DATA_CACHE_ROOT inside work/), so
prep and artifact data are identical (verified in analysis, rtol 1e-5).

Run with VT venv, cwd=/opt/vibe-trading/agent.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WORK = Path("/root/projects/harvest-validate-b2/work")
RUNS_ROOT = Path("/root/.vibe-trading/runs/harvest-validate-b2")
PREP = WORK / "prep"
PY = "/opt/vibe-trading/venv/bin/python"
AGENT = "/opt/vibe-trading/agent"
ENV = {**os.environ,
       "VIBE_TRADING_DATA_CACHE": "true",
       "VIBE_TRADING_DATA_CACHE_ROOT": str(WORK / "data-cache")}

US_COSTS = {"slippage_us": 0.0005}
CRYPTO_COSTS = {"commission": 0.001}          # taker 0.1%/side + engine default slippage 0.05% (batch1 convention)
CRYPTO_NOCOST = {"commission": 0.0, "slippage": 0.0}
US_NOCOST = {"slippage_us": 0.0}
BASE = {"interval": "1D", "engine": "daily", "initial_cash": 1000000}
EVAL_2014 = {"evaluation_start_date": "2014-09-01"}
US_START = "2013-06-01"   # matches fetch_data etf group -> loader cache hit
US_END = "2026-11-25"
POOL_START = "2013-01-01"  # matches fetch_data pool group
CRYPTO_START = "2017-12-01"
CRYPTO_END = "2026-11-25"

W8 = ["SPY.US", "EFA.US", "EEM.US", "IEF.US", "GLD.US", "DBC.US", "VNQ.US", "UUP.US"]
W8_BIL = W8 + ["BIL.US"]
W4 = ["SPY.US", "IEF.US", "GLD.US", "DBC.US"]
POOLS = json.loads(Path("/opt/strategy-library/evidence/st-0002/pools.json").read_text())
POOL = [t + ".US" for t in POOLS["sp500"]["tickers"]]
assert len(POOL) == 503

# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

TSMOM_ENGINE = '''"""st-0004 time-series momentum 12-1 (Moskowitz-Ooi-Pedersen 2012),
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

MODE = "@MODE@"
CAP = 0.30
LOOKBACK_MONTHS = 12
VOL_WINDOW = 60
ANN = 252.0
ASSETS = @ASSETS@
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
'''

CONST_ENGINE = '''"""Constant target weights (buy-and-hold / periodic-rebalance benchmark).

With position_adjustment='rebalance' + rebalance_mask the book re-pins to these
weights on each mask date. Used for st-0004 eight-asset equal weight (MS) and
st-0007 503-name equal weight pool benchmark (MS).
"""
import pandas as pd

WEIGHTS = @WEIGHTS@


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            w = WEIGHTS[code]
            targets[code] = pd.Series(w, index=df.index, name=code)
        return targets
'''

ERC_ENGINE = '''"""st-0014 four-asset ETF risk parity (ERC), literal rule implementation.

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
ASSETS = @ASSETS@


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
'''

PAIR_ENGINE = '''"""st-0011 pair-trading ratio Z-score, literal implementation of BOTH semantics.

Entry (verbatim, stateful text version): ratio = close_A/close_B 的 60 日滚动
均值/标准差得 z；空仓状态下 z <= -2.0 时次日开盘做多 A 做空 B，z >= +2.0 时做空 A
做多 B；两腿各 50% 资金。持仓状态下 |z| < 0.5 时次日开盘两腿平仓；0.5 <= |z| < 2.0
维持持仓（状态机锁存）；单笔最大持有 60 个交易日强制平仓（操作化默认，计数自入场
信号 bar 起，第 60 个持仓信号 bar 发出平仓信号、次一开盘执行）。暖机期 z 为 NaN 空仓。
SEMANTICS='stateless' reproduces the skill example_signal_engine.py VERBATIM:
sig=0.5 where z < -2 (strict), -0.5 where z > +2 (strict), then 0 where |z| < 0.5
(inert overwrite); no latch, exit_z never binds. The two semantics are NOT
interchangeable (draft limitation).
Dates: inner join alignment; signals reindexed to each leg's own index fillna(0)
(example convention). Engine 1-bar delay executes close signals at next open;
flip-date rebalance_mask holds between flips (no drift re-pinning).
Short legs: US borrow cost / crypto perp funding NOT modeled (research grade).
"""
import numpy as np
import pandas as pd

CODE_A = "@CODE_A@"
CODE_B = "@CODE_B@"
SEMANTICS = "@SEMANTICS@"
LOOKBACK = 60
ENTRY_Z = 2.0
EXIT_Z = 0.5
MAX_HOLD = 60


class SignalEngine:
    def generate(self, data_map):
        df_a, df_b = data_map[CODE_A], data_map[CODE_B]
        common = df_a.index.intersection(df_b.index)
        close_a = df_a.loc[common, "close"].astype(float)
        close_b = df_b.loc[common, "close"].astype(float)
        ratio = close_a / close_b
        mean = ratio.rolling(LOOKBACK).mean()
        std = ratio.rolling(LOOKBACK).std()
        z = (ratio - mean) / std
        if SEMANTICS == "stateless":
            sig_a = pd.Series(0.0, index=common)
            sig_a[z < -ENTRY_Z] = 0.5
            sig_a[z > ENTRY_Z] = -0.5
            sig_a[z.abs() < EXIT_Z] = 0.0
            sig_a = sig_a.fillna(0.0)
        else:
            vals = np.zeros(len(common))
            state, held = 0, 0
            zv = z.to_numpy()
            for i in range(len(common)):
                zi = zv[i]
                if state != 0:
                    held += 1
                    if (np.isfinite(zi) and abs(zi) < EXIT_Z) or held >= MAX_HOLD:
                        state, held = 0, 0
                elif np.isfinite(zi):
                    if zi <= -ENTRY_Z:
                        state, held = 1, 0
                    elif zi >= ENTRY_Z:
                        state, held = -1, 0
                vals[i] = 0.5 * state
            sig_a = pd.Series(vals, index=common)
        sig_b = -sig_a
        return {
            CODE_A: sig_a.reindex(df_a.index).fillna(0.0),
            CODE_B: sig_b.reindex(df_b.index).fillna(0.0),
        }
'''

REVERSAL_ENGINE = '''"""st-0007 Jegadeesh (1990) 1-month short-term reversal, S&P500 long-only
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
'''

LOWVOL_ENGINE = '''"""st-0008 Ang et al. (2006) low-volatility anomaly, TOTAL-volatility proxy
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
'''

HV_ENGINE = '''"""st-0012 HV-percentile low-vol entry (VT volatility skill), long-only bounded
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
ANN = @ANN@


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
'''

# ---------------------------------------------------------------------------
# Run specs
# ---------------------------------------------------------------------------

RUNS = []


def add(name, codes, source, start, end, engine_src, costs,
        adjustment="hold", mask=None, boundary=None, extra=None):
    cfg = dict(BASE)
    cfg.update({"source": source, "codes": codes, "start_date": start,
                "end_date": end, "position_adjustment": adjustment})
    cfg.update(costs)
    if boundary:
        cfg.update(boundary)
    if mask is not None:
        cfg["rebalance_mask"] = mask
    if extra:
        cfg.update(extra)
    RUNS.append({"name": name, "config": cfg, "engine": engine_src})


def tsmom(mode):
    return TSMOM_ENGINE.replace("@MODE@", mode).replace("@ASSETS@", repr(W8))


def const(weights):
    return CONST_ENGINE.replace("@WEIGHTS@", repr(weights))


def erc():
    return ERC_ENGINE.replace("@ASSETS@", repr(W4))


def pair(a, b, semantics):
    return (PAIR_ENGINE.replace("@CODE_A@", a).replace("@CODE_B@", b)
            .replace("@SEMANTICS@", semantics))


def hv(ann):
    return HV_ENGINE.replace("@ANN@", repr(float(ann)))


# st-0004: TSMOM long-only + ls research sensitivity + EW benchmark
add("st0004-tsmom-long", W8_BIL, "yfinance", US_START, US_END, tsmom("long"),
    US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)
add("st0004-tsmom-ls", W8_BIL, "yfinance", US_START, US_END, tsmom("ls"),
    US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)
add("st0004-bench-ew", W8, "yfinance", US_START, US_END, const({c: 0.125 for c in W8}),
    US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)

# st-0014: ERC (mask PENDING -> quarterly + threshold fixed point) + 60/40 quarterly
add("st0014-erc", W4, "yfinance", US_START, US_END, erc(), US_COSTS,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})
add("st0014-bench-6040", ["SPY.US", "IEF.US"], "yfinance", US_START, US_END,
    const({"SPY.US": 0.6, "IEF.US": 0.4}), US_COSTS,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})

# st-0011: two pairs x two semantics (masks PENDING)
add("st0011-us-stateful", ["KO.US", "PEP.US"], "yfinance", US_START, US_END,
    pair("KO.US", "PEP.US", "stateful"), US_COSTS,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})
add("st0011-us-stateless", ["KO.US", "PEP.US"], "yfinance", US_START, US_END,
    pair("KO.US", "PEP.US", "stateless"), US_COSTS,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})
add("st0011-crypto-stateful", ["BTC-USDT", "ETH-USDT"], "okx", CRYPTO_START, CRYPTO_END,
    pair("BTC-USDT", "ETH-USDT", "stateful"), CRYPTO_COSTS,
    adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 60},
    extra={"rebalance_tolerance": 0.0})
add("st0011-crypto-stateless", ["BTC-USDT", "ETH-USDT"], "okx", CRYPTO_START, CRYPTO_END,
    pair("BTC-USDT", "ETH-USDT", "stateless"), CRYPTO_COSTS,
    adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 60},
    extra={"rebalance_tolerance": 0.0})

# st-0007: reversal + equal-weight pool benchmark (SPY carrier in strategy run)
add("st0007-reversal", POOL + ["SPY.US"], "yfinance", POOL_START, US_END,
    REVERSAL_ENGINE, US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)
add("st0007-bench-ew", POOL, "yfinance", POOL_START, US_END,
    const({c: 1.0 / len(POOL) for c in POOL}), US_COSTS,
    adjustment="rebalance", mask="MS", boundary=EVAL_2014)

# st-0008: low-vol (pool EW benchmark reused from st0007-bench-ew, declared)
add("st0008-lowvol", POOL + ["SPY.US"], "yfinance", POOL_START, US_END,
    LOWVOL_ENGINE, US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)

# st-0012: HV regime US/crypto + zero-cost jitter variants (masks PENDING)
add("st0012-us", ["SPY.US"], "yfinance", US_START, US_END, hv(252), US_COSTS,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})
add("st0012-us-nocost", ["SPY.US"], "yfinance", US_START, US_END, hv(252), US_NOCOST,
    adjustment="rebalance", mask="PENDING", boundary=EVAL_2014,
    extra={"rebalance_tolerance": 0.0})
add("st0012-crypto", ["BTC-USDT"], "okx", CRYPTO_START, CRYPTO_END, hv(365), CRYPTO_COSTS,
    adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 140},
    extra={"rebalance_tolerance": 0.0})
add("st0012-crypto-nocost", ["BTC-USDT"], "okx", CRYPTO_START, CRYPTO_END, hv(365), CRYPTO_NOCOST,
    adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 140},
    extra={"rebalance_tolerance": 0.0})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prep_data(group, code):
    df = pd.read_csv(PREP / f"{group}_{code}.csv", index_col=0, parse_dates=True)
    return df


def data_map_for(cfg):
    group = "okx" if cfg["source"] == "okx" else ("pool" if len(cfg["codes"]) > 20 else "etf")
    return {c: prep_data(group, c) for c in cfg["codes"]}


def load_engine_module(path):
    spec = importlib.util.spec_from_file_location("sig_" + path.parent.parent.name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def first_eval_index(cfg, idx):
    if "warmup_bars" in cfg:
        return cfg["warmup_bars"]
    ev = pd.Timestamp(cfg["evaluation_start_date"])
    later = idx[idx >= ev]
    return int(idx.get_loc(later[0]))


def flip_exec_dates(state, idx, first_eval_i):
    vals = state.to_numpy()
    dates = {pd.Timestamp(idx[first_eval_i]).strftime("%Y-%m-%d")}
    for i in range(1, len(vals)):
        if abs(vals[i] - vals[i - 1]) > 1e-9 and i + 1 < len(vals):
            dates.add(pd.Timestamp(idx[i + 1]).strftime("%Y-%m-%d"))
    return sorted(dates)


def quarter_exec_dates(idx, first_eval_i):
    """First trading day of Mar/Jun/Sep/Dec within the evaluation window."""
    out = []
    eval_idx = idx[first_eval_i:]
    periods = eval_idx.to_period("M")
    for p in periods.unique():
        if p.month in (3, 6, 9, 12):
            out.append(str(eval_idx[periods == p][0].date()))
    return out


def write_run(run):
    rd = RUNS_ROOT / run["name"]
    (rd / "code").mkdir(parents=True, exist_ok=True)
    (rd / "code" / "signal_engine.py").write_text(run["engine"], encoding="utf-8")
    (rd / "config.json").write_text(json.dumps(run["config"], ensure_ascii=False, indent=2),
                                    encoding="utf-8")


def run_runner(rd, timeout=1800):
    log = WORK / "logs" / f"build_{rd.name}.log"
    with log.open("w") as fh:
        proc = subprocess.run([PY, "-m", "backtest.runner", str(rd)],
                              cwd=AGENT, stdout=fh, stderr=subprocess.STDOUT,
                              timeout=timeout, env=ENV)
    ok = proc.returncode == 0 and (rd / "artifacts" / "metrics.csv").exists()
    if not ok:
        raise RuntimeError(f"runner failed for {rd.name} rc={proc.returncode}; see {log}")
    return ok


def st0014_threshold_fixed_point(run):
    """Iterate: quarterly mask -> run -> read actual weights -> add >=10pp
    trigger execution dates -> rerun, until the mask is stable."""
    rd = RUNS_ROOT / run["name"]
    cfg = run["config"]
    dm = data_map_for(cfg)
    idx = dm[cfg["codes"][0]].index
    fe = first_eval_index(cfg, idx)
    mask = quarter_exec_dates(idx, fe)
    history = []
    for it in range(8):
        cfg["rebalance_mask"] = mask
        write_run(run)
        run_runner(rd)
        pos = pd.read_csv(rd / "artifacts" / "positions.csv", index_col=0, parse_dates=True)
        tgt = pd.read_csv(rd / "artifacts" / "target_positions.csv", index_col=0, parse_dates=True)
        pos = pos.loc[tgt.index]
        dev = (pos - tgt).abs().max(axis=1)
        # Exclude the terminal bar (engine force-liquidates at the last close,
        # so actual weights collapse to 0 against a still-live target) and
        # quarter-signal days whose target changes next bar (the scheduled
        # quarterly rebalance already executes that change next open).
        eligible = dev.index[:-1]
        tgt_next = tgt.shift(-1)
        signal_days = [d for d in eligible
                       if not np.allclose(tgt.loc[d].to_numpy(),
                                          tgt_next.loc[d].to_numpy(), atol=1e-12)]
        cand = dev.loc[eligible].drop(index=signal_days)
        triggers = cand[cand >= 0.10 - 1e-12]
        exec_dates = set()
        for d in triggers.index:
            later = idx[idx > d]
            if len(later):
                exec_dates.add(str(later[0].date()))
        new_mask = sorted(set(mask) | exec_dates)
        history.append({"iteration": it + 1, "mask_dates": len(mask),
                        "trigger_days": int(len(triggers)),
                        "new_exec_dates": len(exec_dates - set(mask)),
                        "signal_days_excluded": len(signal_days),
                        "max_deviation_excl_terminal_and_signal": round(float(cand.max()), 6)})
        print(f"ST0014 iter{it + 1}: mask={len(mask)} triggers={len(triggers)} "
              f"new={len(exec_dates - set(mask))} maxdev_excl={cand.max():.4f}", flush=True)
        if new_mask == mask:
            break
        mask = new_mask
    cfg["rebalance_mask"] = mask
    write_run(run)
    (WORK / "st0014_threshold_iterations.json").write_text(
        json.dumps({"history": history, "final_mask_dates": len(mask),
                    "converged": new_mask == mask}, ensure_ascii=False, indent=2))
    return mask


def st0014_solver_diagnostics():
    """Re-run the ERC solver on prep data to record convergence + cap binding."""
    rd = RUNS_ROOT / "st0014-erc"
    mod = load_engine_module(rd / "code" / "signal_engine.py")
    dm = data_map_for({"source": "yfinance", "codes": W4})
    closes = pd.DataFrame({c: dm[c]["close"].astype(float) for c in W4}).sort_index()
    rets = closes.pct_change()
    idx = closes.index
    last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
    sig_dates = [d for d in last_days if pd.Timestamp(d).month in (2, 5, 8, 11)]
    diag = []
    for d in sig_dates:
        loc = idx.get_loc(d)
        window = rets.iloc[loc - 59: loc + 1]
        if len(window) != 60 or not window.notna().all().all():
            continue
        cov = window.cov().to_numpy()
        w, iters, delta = mod.erc_weights(cov)
        wc = mod.apply_cap(w, 0.60)
        sw = cov @ wc
        rc = wc * sw
        rc_share = rc / rc.sum()
        diag.append({"signal_date": str(pd.Timestamp(d).date()),
                     "iterations": iters, "final_delta": float(delta),
                     "weights_raw": {c: round(float(x), 6) for c, x in zip(W4, w)},
                     "weights_capped": {c: round(float(x), 6) for c, x in zip(W4, wc)},
                     "cap_bound": bool((w > 0.60 + 1e-12).any()),
                     "max_rc_share_deviation_from_025": round(float(np.abs(rc_share - 0.25).max()), 8)})
    (WORK / "st0014_solver_diagnostics.json").write_text(
        json.dumps(diag, ensure_ascii=False, indent=2))
    n_cap = sum(1 for d in diag if d["cap_bound"])
    print(f"ST0014 solver: {len(diag)} quarterly solves, cap bound {n_cap}, "
          f"max iters {max(d['iterations'] for d in diag)}", flush=True)


def main():
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    (WORK / "logs").mkdir(exist_ok=True)
    manifest = []

    # 1. runs with static masks
    for run in RUNS:
        if run["config"].get("rebalance_mask") != "PENDING":
            write_run(run)
            manifest.append(run["name"])

    # 2. st-0014 quarterly + threshold fixed point (runs the engine itself)
    erc_run = next(r for r in RUNS if r["name"] == "st0014-erc")
    st0014_threshold_fixed_point(erc_run)
    manifest.append("st0014-erc")
    st0014_solver_diagnostics()
    # 60/40 benchmark: same quarterly execution calendar
    b60 = next(r for r in RUNS if r["name"] == "st0014-bench-6040")
    dm = data_map_for(b60["config"])
    idx = dm["SPY.US"].index
    fe = first_eval_index(b60["config"], idx)
    b60["config"]["rebalance_mask"] = quarter_exec_dates(idx, fe)
    write_run(b60)
    manifest.append("st0014-bench-6040")

    # 3. flip-mask runs (st-0011 x4, st-0012 x4)
    for run in RUNS:
        if run["config"].get("rebalance_mask") != "PENDING":
            continue
        cfg = run["config"]
        rd = RUNS_ROOT / run["name"]
        write_run(run)
        dm = data_map_for(cfg)
        mod = load_engine_module(rd / "code" / "signal_engine.py")
        targets = mod.SignalEngine().generate(dm)
        code = cfg["codes"][0]
        idx = dm[code].index
        fe = first_eval_index(cfg, idx)
        mask = flip_exec_dates(targets[code], idx, fe)
        cfg["rebalance_mask"] = mask
        write_run(run)
        manifest.append(run["name"])
        print(f"MASK {run['name']}: bars={len(idx)} first_eval={idx[fe].date()} "
              f"flips={len(mask) - 1}", flush=True)

    (WORK / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("BUILT", len(manifest), "runs", flush=True)


if __name__ == "__main__":
    main()
