"""st-0009 joint ATR/RV expansion de-risk, literal rule implementation.

Signal (verbatim from entry signal_definition):
  TR_t = max(high-low, |high-prev_close|, |low-prev_close|)
  ATR20 = wilder smoothing of TR (SMA = operational default; Wilder/RMA variant)
  atr_pct_t = 100 * count(ATR20_{t-499..t} < ATR20_t) / 500   (strict-less fraction)
  RV_t = std(daily returns, 250) * sqrt(250.0)
  vol_pct_t = 100 * count(RV_{t-249..t} < RV_t) / 250
  expansion = (atr_pct >= 80) AND (vol_pct >= 80)
Positions: two-state target weight 1.0 (normal) / 0.5 (expansion); warmup
(undefined percentiles) holds 1.0. Transitions execute at next-bar open via the
engine's built-in 1-bar delay; the run's rebalance_mask lists exactly the
flip execution dates so no drift rebalancing happens between flips.
Percentile note: rolling.rank(method='min') = 1 + count(strictly less), so
(rank-1)/n*100 is the entry's strict-less percentage exactly.
"""
import numpy as np
import pandas as pd

ATR_N = 20
ATR_WIN = 500
RV_WIN = 250
VOL_WIN = 250
PCT_THRESHOLD = 80.0
SMOOTH = "wilder"
ANN_FACTOR = 250.0
W_NORMAL = 1.0
W_EXPANSION = 0.5


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            high = df["high"].astype(float)
            low = df["low"].astype(float)
            close = df["close"].astype(float)
            prev_close = close.shift(1)
            tr = pd.concat(
                [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
                axis=1,
            ).max(axis=1)  # first bar: prev_close NaN -> TR = high-low
            if SMOOTH == "sma":
                atr = tr.rolling(ATR_N, min_periods=ATR_N).mean()
            else:
                # Wilder RMA seeded with the SMA of the first ATR_N TRs
                trv = tr.to_numpy()
                av = np.full(len(trv), np.nan)
                if len(trv) >= ATR_N:
                    av[ATR_N - 1] = np.mean(trv[:ATR_N])
                    for i in range(ATR_N, len(trv)):
                        av[i] = (av[i - 1] * (ATR_N - 1) + trv[i]) / ATR_N
                atr = pd.Series(av, index=close.index)
            atr_pct = (atr.rolling(ATR_WIN, min_periods=ATR_WIN).rank(method="min") - 1.0) / ATR_WIN * 100.0
            ret = close.pct_change()
            rv = ret.rolling(RV_WIN, min_periods=RV_WIN).std() * np.sqrt(ANN_FACTOR)
            vol_pct = (rv.rolling(VOL_WIN, min_periods=VOL_WIN).rank(method="min") - 1.0) / VOL_WIN * 100.0
            defined = atr_pct.notna() & vol_pct.notna()
            expansion = (atr_pct >= PCT_THRESHOLD) & (vol_pct >= PCT_THRESHOLD)
            state = np.where(expansion.to_numpy(), W_EXPANSION, W_NORMAL)
            state = np.where(defined.to_numpy(), state, W_NORMAL)  # warmup holds 1.0
            targets[code] = pd.Series(state, index=close.index, name=code)
        return targets
