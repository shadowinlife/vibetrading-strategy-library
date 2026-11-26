"""st-0006 Connors RSI(2) mean reversion, literal rule implementation.

Entry (verbatim): 三 ETF 独立 sleeve（SPY/QQQ/IWM 各 1/3 资金）；收盘价 > 200 日
SMA（趋势过滤）且 RSI(2) < 10.0 时，次日开盘该 sleeve 满仓买入；只做多。
Exit: 持仓后收盘 > 5 日 SMA 次日开盘清仓（EXIT_MODE='ma5'）；或 RSI(2) > 90
次日开盘清仓（EXIT_MODE='rsi90'，简报变体）；失效退出：收盘跌破 200 日 SMA
次日开盘清仓（操作化默认，USE_FILTER=True 时）。无固定止损。
RSI(2) = Wilder 2-period RSI: ewm(alpha=1/2, adjust=False) reproduces the
classic seed (first 2 gains/losses averaged) and RMA recursion exactly.
Sleeve weight 1/3 each; state machine per sleeve; engine 1-bar delay executes
close signals at next open. No manual shift.
"""
import numpy as np
import pandas as pd

ENTRY_THR = 10.0
EXIT_MODE = "rsi90"
USE_FILTER = True
RSI_N = 2
MA_TREND = 200
MA_EXIT = 5
RSI_EXIT = 90.0


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        n = len(data_map)
        sleeve = 1.0 / n
        for code, df in data_map.items():
            close = df["close"].astype(float)
            delta = close.diff()
            gain = delta.clip(lower=0.0)
            loss = (-delta).clip(lower=0.0)
            avg_gain = gain.ewm(alpha=1.0 / RSI_N, adjust=False, min_periods=RSI_N).mean()
            avg_loss = loss.ewm(alpha=1.0 / RSI_N, adjust=False, min_periods=RSI_N).mean()
            rs = avg_gain / avg_loss
            rsi = 100.0 - 100.0 / (1.0 + rs)
            ma_trend = close.rolling(MA_TREND, min_periods=MA_TREND).mean()
            ma_exit = close.rolling(MA_EXIT, min_periods=MA_EXIT).mean()
            if USE_FILTER:
                entry = (close > ma_trend) & (rsi < ENTRY_THR)
                invalid = close < ma_trend
            else:
                entry = rsi < ENTRY_THR
                invalid = pd.Series(False, index=close.index)
            if EXIT_MODE == "ma5":
                exit_sig = (close > ma_exit) | invalid
            else:
                exit_sig = (rsi > RSI_EXIT) | invalid
            entry_arr = entry.fillna(False).to_numpy()
            exit_arr = exit_sig.fillna(False).to_numpy()
            state = np.zeros(len(close), dtype=float)
            holding = False
            for i in range(len(close)):
                if holding and exit_arr[i]:
                    holding = False
                elif not holding and entry_arr[i]:
                    holding = True
                state[i] = sleeve if holding else 0.0
            targets[code] = pd.Series(state, index=close.index, name=code)
        return targets
