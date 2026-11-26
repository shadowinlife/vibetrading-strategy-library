"""Constant target weights (buy-and-hold / periodic-rebalance benchmark).

Weights are fixed per symbol; with position_adjustment='rebalance' and
rebalance_mask='MS' the book re-pins to these weights on the first trading day
of each month (monthly-rebalanced equal-weight benchmark). With 'hold' and a
single 1.0 weight it is plain buy-and-hold.
"""
import pandas as pd

WEIGHTS = {'SPY.US': 0.6, 'AGG.US': 0.4}


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            w = WEIGHTS[code]
            targets[code] = pd.Series(w, index=df.index, name=code)
        return targets
