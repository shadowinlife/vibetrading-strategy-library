"""st-0011 pair-trading ratio Z-score, literal implementation of BOTH semantics.

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

CODE_A = "KO.US"
CODE_B = "PEP.US"
SEMANTICS = "stateful"
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
