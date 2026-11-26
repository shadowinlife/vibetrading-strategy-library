"""st-0001 dual-MA trend following (20/60), literal rule implementation.

Entry rules (verbatim from library entry st-0001):
  20 日均线上穿 60 日均线（金叉）且收盘价站上 60 日均线，次日开盘入场做多；
  只做多，不做空。
Exit rules:
  20 日均线下穿 60 日均线（死叉），次日开盘平仓；可选硬止损 2xATR(20) 未启用
  （条目标注为可选；本次验证跑基础规则，未启用可选止损，见验证报告）。
Position sizing:
  单标的固定资金比例 10%-20%；本次取区间中值 15%，不加杠杆，不摊平亏损。

Timing contract: the VT daily engine executes a bar-close target at the NEXT
bar's open (backtest/signal_timing.py). So the state computed at bar t close
is filled at t+1 open, exactly matching "次日开盘入场/平仓". No shift here.
"""
import numpy as np
import pandas as pd

POSITION_WEIGHT = 0.15  # midpoint of the entry's 10%-20% fixed-fraction band


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            ma20 = close.rolling(20, min_periods=20).mean()
            ma60 = close.rolling(60, min_periods=60).mean()

            above = ma20 > ma60
            prev_above = above.shift(1).fillna(False)
            golden_cross = above & ~prev_above            # MA20 上穿 MA60
            death_cross = (~above) & prev_above           # MA20 下穿 MA60
            entry_signal = golden_cross & (close > ma60)  # 且收盘价站上 MA60

            # Long-only state machine: flat until entry signal; hold until
            # death cross. While holding, MA20 > MA60 persists by construction
            # (any flip to below IS a death cross), so no re-entry ambiguity.
            state = np.zeros(len(close), dtype=float)
            holding = False
            entry_arr = entry_signal.to_numpy()
            exit_arr = death_cross.to_numpy()
            for i in range(len(close)):
                if holding and exit_arr[i]:
                    holding = False
                elif not holding and entry_arr[i]:
                    holding = True
                state[i] = POSITION_WEIGHT if holding else 0.0

            targets[code] = pd.Series(state, index=df.index, name=code)
        return targets