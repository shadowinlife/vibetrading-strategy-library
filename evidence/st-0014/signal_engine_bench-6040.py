"""Constant target weights (buy-and-hold / periodic-rebalance benchmark).

With position_adjustment='rebalance' + rebalance_mask the book re-pins to these
weights on each mask date. Used for st-0004 eight-asset equal weight (MS) and
st-0007 503-name equal weight pool benchmark (MS).
"""
import pandas as pd

WEIGHTS = {'SPY.US': 0.6, 'IEF.US': 0.4}


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            w = WEIGHTS[code]
            targets[code] = pd.Series(w, index=df.index, name=code)
        return targets
