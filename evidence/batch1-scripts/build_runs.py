"""Build all VT backtest run dirs for harvest-validate-b1.

Each run dir gets config.json + code/signal_engine.py implementing the library
entry's rules VERBATIM (see per-engine docstrings quoting the entry). Two-state
1.0/0.5 strategies (st-0009, st-0010) use position_adjustment='rebalance' with
an explicit ISO-date rebalance_mask = the next trading day after each signal
flip (plus the first evaluation day for the initial build). This executes ONLY
signal-driven transitions: no drift re-pinning between flips, matching the
entries' two-state semantics. Mask dates are computed by importing the very
engine file the runner will load, on data fetched through the same VT loader
code path the runner uses.

Run with VT venv, cwd=/opt/vibe-trading/agent.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

RUNS_ROOT = Path("/root/.vibe-trading/runs/harvest-validate-b1")
WORK = Path("/root/projects/harvest-validate-b1/work")
PREP = WORK / "prep"
PREP.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Engine templates. @NAME@ placeholders are replaced with literal constants.
# ---------------------------------------------------------------------------

GTAA_ENGINE = '''"""st-0003 Faber 10-month SMA GTAA, literal rule implementation.

Entry (verbatim): 五资产 ETF 池 SPY/EFA/IEF/GSG/VNQ 各 20% sleeve；每月最后一个
交易日收盘，任一资产收盘价 > 其 10 月 SMA（过去 10 个月末收盘均值）则该 sleeve
次月首个交易日开盘持有该资产，否则该 sleeve 转为现金；各资产独立判断，只做多。
Warmup: 前 10 个月末 SMA 未定义，该 sleeve 持现金。
Timing: VT daily engine fills a bar-close target at the NEXT bar open (built-in
1-bar delay), so the month-end decision executes at the next month's first
trading day open. No manual shift.
"""
import numpy as np
import pandas as pd

SLEEVE_WEIGHT = @SLEEVE@
SMA_MONTHS = @SMA_MONTHS@


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            idx = close.index
            # actual last trading day of each calendar month
            last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
            me_close = close.loc[last_days]
            sma = me_close.rolling(SMA_MONTHS, min_periods=SMA_MONTHS).mean()
            state = (me_close > sma).astype(float)  # NaN SMA (warmup) -> False -> cash
            state.index = pd.DatetimeIndex(last_days)
            # month-end bar carries its own month's decision; earlier bars carry
            # the previous month-end decision (ffill). Engine shift executes the
            # month-end decision at the next bar open = next month first day.
            daily = state.reindex(idx, method="ffill").fillna(0.0)
            targets[code] = pd.Series(daily.to_numpy() * SLEEVE_WEIGHT, index=idx, name=code)
        return targets
'''

CONST_ENGINE = '''"""Constant target weights (buy-and-hold / periodic-rebalance benchmark).

Weights are fixed per symbol; with position_adjustment='rebalance' and
rebalance_mask='MS' the book re-pins to these weights on the first trading day
of each month (monthly-rebalanced equal-weight benchmark). With 'hold' and a
single 1.0 weight it is plain buy-and-hold.
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

GEM_ENGINE = '''"""st-0005 Antonacci dual momentum GEM, literal rule implementation.

Entry (verbatim): 每月末比较 SPY 与 ACWX 过去 12 个月总收益，取较高者为相对动量
赢家；若赢家 12 个月总收益 > BIL 同期收益（绝对动量为正），次月首个交易日开盘
满仓持有赢家；否则满仓持有 @FALLBACK@。只做多，不加杠杆，三选一。
Warmup: 前 12 个月信号未定义持现金。月度评估无跳月。
Tie-break (operational, declared): equal 12-month returns -> SPY wins.
Timing: engine built-in 1-bar delay executes month-end decision at next month
first trading day open. No manual shift.
"""
import numpy as np
import pandas as pd

LOOKBACK_MONTHS = @LOOKBACK@
FALLBACK = "@FALLBACK@"


class SignalEngine:
    def generate(self, data_map):
        ref = data_map["SPY.US"]["close"].astype(float)
        idx = ref.index
        last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
        me = {}
        for c, df in data_map.items():
            me[c] = df["close"].astype(float).reindex(last_days, method="ffill")
        r12 = {c: me[c] / me[c].shift(LOOKBACK_MONTHS) - 1.0 for c in me}
        decisions = []
        for d in last_days:
            r_spy = r12["SPY.US"].loc[d]
            r_acwx = r12["ACWX.US"].loc[d]
            r_bil = r12["BIL.US"].loc[d]
            if pd.isna(r_spy) or pd.isna(r_acwx) or pd.isna(r_bil):
                decisions.append(None)  # warmup -> cash
                continue
            winner = "SPY.US" if r_spy >= r_acwx else "ACWX.US"
            r_win = r12[winner].loc[d]
            decisions.append(winner if r_win > r_bil else FALLBACK)
        dec = pd.Series(decisions, index=pd.DatetimeIndex(last_days))
        daily = dec.reindex(idx, method="ffill")
        targets = {}
        for c in data_map:
            w = (daily == c).astype(float).fillna(0.0)
            targets[c] = pd.Series(w.to_numpy(), index=idx, name=c)
        return targets
'''

ATR_ENGINE = '''"""st-0009 joint ATR/RV expansion de-risk, literal rule implementation.

Signal (verbatim from entry signal_definition):
  TR_t = max(high-low, |high-prev_close|, |low-prev_close|)
  ATR20 = @SMOOTH@ smoothing of TR (SMA = operational default; Wilder/RMA variant)
  atr_pct_t = 100 * count(ATR20_{t-499..t} < ATR20_t) / 500   (strict-less fraction)
  RV_t = std(daily returns, 250) * sqrt(@ANN@)
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

ATR_N = @ATR_N@
ATR_WIN = @ATR_WIN@
RV_WIN = @RV_WIN@
VOL_WIN = @VOL_WIN@
PCT_THRESHOLD = @PCT@
SMOOTH = "@SMOOTH@"
ANN_FACTOR = @ANN@
W_NORMAL = @W_NORMAL@
W_EXPANSION = @W_EXPANSION@


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
'''

RSI2_ENGINE = '''"""st-0006 Connors RSI(2) mean reversion, literal rule implementation.

Entry (verbatim): 三 ETF 独立 sleeve（SPY/QQQ/IWM 各 1/3 资金）；收盘价 > 200 日
SMA（趋势过滤）且 RSI(2) < @THR@ 时，次日开盘该 sleeve 满仓买入；只做多。
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

ENTRY_THR = @THR@
EXIT_MODE = "@EXIT_MODE@"
USE_FILTER = @USE_FILTER@
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
'''

SEASONAL_ENGINE = '''"""st-0013 month-effect calendar timing (long-only), literal implementation.

Entry (verbatim): 每月最后一个交易日收盘按下一自然月的月份号确定目标权重——
下一月 ∈ bullish_months → 1.0，次月第一个交易日开盘建仓；看空月与中性月 → 0。
bullish_months = @BULLISH@ (VT seasonal skill default / Sell-in-May variant).
use_weekday=False. Long-only, no leverage, no intra-month stops.
Implementation: every bar carries its own month's weight EXCEPT the last
trading day of month m, which carries month m+1's weight; the engine's 1-bar
delay then executes exactly at month m+1's first trading day open.
"""
import numpy as np
import pandas as pd

BULLISH_MONTHS = @BULLISH@


class SignalEngine:
    def generate(self, data_map):
        targets = {}
        for code, df in data_map.items():
            close = df["close"].astype(float)
            idx = close.index
            w = np.isin(idx.month, BULLISH_MONTHS).astype(float)
            out = pd.Series(w, index=idx)
            last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().values
            for d in last_days:
                next_month = (pd.Timestamp(d) + pd.offsets.MonthBegin(1)).month
                out.loc[d] = 1.0 if next_month in BULLISH_MONTHS else 0.0
            targets[code] = pd.Series(out.to_numpy(), index=idx, name=code)
        return targets
'''

MARGIN_STATE_ENGINE = '''"""st-0010 margin-divergence de-risk applied to the 510050.SH ETF proxy.

The divergence signal itself is computed OUTSIDE the engine from the archived
Eastmoney SSE margin snapshot + sina Shanghai Composite (research series):
  divergence_t = (margin_t >= max(margin_{t-119..t})) AND
                 (close_t <  max(close_{t-119..t}))
State: 0.5 while divergence holds, else 1.0; before margin data / 120-day
warmup: 1.0. TRANSITIONS below are the literal (decision-date, new-weight)
pairs at whose CLOSE the state changes; the engine's 1-bar delay plus the
run's flip-date rebalance_mask execute each transition at the NEXT trading
day open, exactly per entry. No drift rebalancing between flips.
"""
import pandas as pd

TRANSITIONS = @TRANSITIONS@


class SignalEngine:
    def generate(self, data_map):
        dates = pd.DatetimeIndex([pd.Timestamp(d) for d, w in TRANSITIONS])
        vals = [w for d, w in TRANSITIONS]
        state = pd.Series(vals, index=dates)
        targets = {}
        for code, df in data_map.items():
            idx = df.index
            daily = state.reindex(idx, method="ffill").fillna(1.0)
            targets[code] = pd.Series(daily.to_numpy(), index=idx, name=code)
        return targets
'''

# ---------------------------------------------------------------------------
# Run specifications
# ---------------------------------------------------------------------------

US_COSTS = {"slippage_us": 0.0005}
HK_COSTS = {
    "hk_lot_sizes": {"0700.HK": 100},
    "slippage_hk": 0.001,
    "hk_stamp_tax": 0.001,
    "hk_commission": 0.00015,
    "hk_levy": 0.0000565,
    "hk_settlement": 0.00002,
}
CRYPTO_COSTS = {"commission": 0.001}
ETF_COSTS = {
    "commission_rate": 0.00025,
    "commission_min": 5.0,
    "stamp_tax": 0.0,        # exchange ETFs are stamp-tax exempt (entry note)
    "transfer_fee": 0.00001,
    "slippage": 0.001,
}

BASE = {"interval": "1D", "engine": "daily", "initial_cash": 1000000}
W5 = ["SPY.US", "EFA.US", "IEF.US", "GSG.US", "VNQ.US"]
W4 = ["SPY.US", "ACWX.US", "AGG.US", "BIL.US"]
W3 = ["SPY.US", "QQQ.US", "IWM.US"]

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


def gtaa(sleeve=0.2, months=10):
    return GTAA_ENGINE.replace("@SLEEVE@", repr(sleeve)).replace("@SMA_MONTHS@", repr(months))


def const(weights):
    return CONST_ENGINE.replace("@WEIGHTS@", repr(weights))


def gem(fallback):
    return GEM_ENGINE.replace("@LOOKBACK@", "12").replace("@FALLBACK@", fallback)


def atr(smooth, ann, w_normal=1.0, w_exp=0.5):
    return (ATR_ENGINE.replace("@ATR_N@", "20").replace("@ATR_WIN@", "500")
            .replace("@RV_WIN@", "250").replace("@VOL_WIN@", "250")
            .replace("@PCT@", "80.0").replace("@SMOOTH@", smooth)
            .replace("@ANN@", repr(float(ann))).replace("@W_NORMAL@", repr(w_normal))
            .replace("@W_EXPANSION@", repr(w_exp)))


def rsi2(thr, exit_mode, use_filter):
    return (RSI2_ENGINE.replace("@THR@", repr(float(thr)))
            .replace("@EXIT_MODE@", exit_mode).replace("@USE_FILTER@", repr(use_filter)))


def seasonal(bullish):
    return SEASONAL_ENGINE.replace("@BULLISH@", repr(tuple(bullish)))


EVAL_2014 = {"evaluation_start_date": "2014-09-01"}

# st-0003
add("st0003-gtaa", W5, "yfinance", "2013-06-01", "2026-11-26", gtaa(), US_COSTS, boundary=EVAL_2014)
add("st0003-bench-ew", W5, "yfinance", "2013-06-01", "2026-11-26",
    const({c: 0.2 for c in W5}), US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)
# st-0005
add("st0005-gem", W4, "yfinance", "2013-06-01", "2026-11-26", gem("AGG.US"), US_COSTS, boundary=EVAL_2014)
add("st0005-gem-bil", W4, "yfinance", "2013-06-01", "2026-11-26", gem("BIL.US"), US_COSTS, boundary=EVAL_2014)
add("st0005-bench-6040", ["SPY.US", "AGG.US"], "yfinance", "2013-06-01", "2026-11-26",
    const({"SPY.US": 0.6, "AGG.US": 0.4}), US_COSTS, adjustment="rebalance", mask="MS", boundary=EVAL_2014)
# st-0009 (masks computed below)
add("st0009-us-sma", ["SPY.US"], "yfinance", "2014-09-01", "2026-11-26", atr("sma", 250),
    US_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
add("st0009-us-wilder", ["SPY.US"], "yfinance", "2014-09-01", "2026-11-26", atr("wilder", 250),
    US_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
add("st0009-hk-sma", ["0700.HK"], "yfinance", "2014-09-01", "2026-11-26", atr("sma", 250),
    HK_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
add("st0009-hk-wilder", ["0700.HK"], "yfinance", "2014-09-01", "2026-11-26", atr("wilder", 250),
    HK_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
add("st0009-crypto-sma", ["BTC-USDT"], "okx", "2017-12-01", "2026-11-25", atr("sma", 365),
    CRYPTO_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
add("st0009-crypto-wilder", ["BTC-USDT"], "okx", "2017-12-01", "2026-11-25", atr("wilder", 365),
    CRYPTO_COSTS, adjustment="rebalance", mask="PENDING", boundary={"warmup_bars": 500})
# st-0006
add("st0006-main", W3, "yfinance", "2013-06-01", "2026-11-26", rsi2(10, "ma5", True), US_COSTS, boundary=EVAL_2014)
add("st0006-thr5", W3, "yfinance", "2013-06-01", "2026-11-26", rsi2(5, "ma5", True), US_COSTS, boundary=EVAL_2014)
add("st0006-exit90", W3, "yfinance", "2013-06-01", "2026-11-26", rsi2(10, "rsi90", True), US_COSTS, boundary=EVAL_2014)
add("st0006-nofilter", W3, "yfinance", "2013-06-01", "2026-11-26", rsi2(10, "ma5", False), US_COSTS, boundary=EVAL_2014)
add("st0006-main-10bps", W3, "yfinance", "2013-06-01", "2026-11-26", rsi2(10, "ma5", True),
    {"slippage_us": 0.001}, boundary=EVAL_2014)
# st-0013
add("st0013-main", ["SPY.US"], "yfinance", "2014-08-01", "2026-11-26",
    seasonal([1, 2, 3, 11, 12]), US_COSTS, boundary=EVAL_2014)
add("st0013-sellmay", ["SPY.US"], "yfinance", "2014-08-01", "2026-11-26",
    seasonal([11, 12, 1, 2, 3, 4]), US_COSTS, boundary=EVAL_2014)


# ---------------------------------------------------------------------------
# Mask computation for the two-state runs (fetch via the runner's loader path)
# ---------------------------------------------------------------------------

def fetch_via_vt(source, codes, start, end):
    from backtest.runner import _get_loader
    diagnostics = []
    loader = _get_loader(source, diagnostics=diagnostics)()
    data_map = loader.fetch(codes, start, end, interval="1D")
    missing = [c for c in codes if c not in data_map or data_map[c].empty]
    if missing:
        raise RuntimeError(f"loader {source} returned no data for {missing}")
    return data_map


def load_engine_module(path):
    spec = importlib.util.spec_from_file_location("sig_" + path.parent.parent.name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flip_exec_dates(state, idx, first_eval_date):
    """Next trading day after each state flip, plus the first evaluation day."""
    vals = state.to_numpy()
    dates = []
    for i in range(1, len(vals)):
        if abs(vals[i] - vals[i - 1]) > 1e-9 and i + 1 < len(vals):
            dates.append(idx[i + 1])
    out = {pd.Timestamp(first_eval_date).strftime("%Y-%m-%d")}
    for d in dates:
        out.add(pd.Timestamp(d).strftime("%Y-%m-%d"))
    return sorted(out)


def build_margin_transitions():
    """st-0010 divergence state from archived margin snapshot + sina index."""
    sse = pd.read_csv(WORK / "st0010_sse_margin_snapshot_20261126.csv")
    sse["date"] = pd.to_datetime(sse["信用交易日期"], format="%Y%m%d")
    sse = sse.set_index("date").sort_index()
    margin = pd.to_numeric(sse["融资余额"], errors="coerce")
    idx_df = pd.read_csv(WORK / "st0010_sh000001_sina_daily.csv", parse_dates=["date"])
    idx_df = idx_df.set_index("date").sort_index()
    iclose = pd.to_numeric(idx_df["close"], errors="coerce")
    df = pd.DataFrame({"margin": margin, "close": iclose.reindex(margin.index)}).dropna()
    m_max = df["margin"].rolling(120, min_periods=120).max()
    c_max = df["close"].rolling(120, min_periods=120).max()
    div = (df["margin"] >= m_max) & (df["close"] < c_max)
    state = pd.Series(1.0, index=df.index)
    state[div] = 0.5
    transitions = [("2018-08-24", 1.0)]
    prev = 1.0
    for d, w in state.items():
        if abs(w - prev) > 1e-9:
            transitions.append((d.strftime("%Y-%m-%d"), float(w)))
            prev = w
    info = {
        "margin_rows": int(len(df)),
        "window": [str(df.index[0].date()), str(df.index[-1].date())],
        "divergence_days": int(div.sum()),
        "first_defined": str(m_max.first_valid_index().date()),
        "transitions": len(transitions) - 1,
    }
    return transitions, state, df, info


def main():
    manifest = []
    # --- write non-mask runs ------------------------------------------------
    for run in RUNS:
        rd = RUNS_ROOT / run["name"]
        (rd / "code").mkdir(parents=True, exist_ok=True)
        (rd / "code" / "signal_engine.py").write_text(run["engine"], encoding="utf-8")
        if run["config"].get("rebalance_mask") != "PENDING":
            (rd / "config.json").write_text(json.dumps(run["config"], ensure_ascii=False, indent=2), encoding="utf-8")
            manifest.append(run["name"])

    # --- st-0009 masks -------------------------------------------------------
    for run in RUNS:
        if run["config"].get("rebalance_mask") != "PENDING":
            continue
        cfg = run["config"]
        rd = RUNS_ROOT / run["name"]
        data_map = fetch_via_vt(cfg["source"], cfg["codes"], cfg["start_date"], cfg["end_date"])
        for c, df in data_map.items():
            df.to_csv(PREP / f"{run['name']}_{c}.csv")
        mod = load_engine_module(rd / "code" / "signal_engine.py")
        targets = mod.SignalEngine().generate(data_map)
        code = cfg["codes"][0]
        idx = data_map[code].index
        warmup = cfg.get("warmup_bars", 0)
        first_eval = idx[warmup]
        mask = flip_exec_dates(targets[code], idx, first_eval)
        cfg["rebalance_mask"] = mask
        (rd / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append(run["name"])
        print(f"MASK {run['name']}: bars={len(idx)} first_eval={first_eval.date()} "
              f"last={idx[-1].date()} flips={len(mask)-1}", flush=True)

    # --- st-0010 ETF proxy run ----------------------------------------------
    transitions, state, mdf, info = build_margin_transitions()
    (WORK / "st0010_divergence_state.csv").write_text(
        pd.DataFrame({"state": state}).to_csv(), encoding="utf-8")
    (WORK / "st0010_signal_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MARGIN_SIGNAL", json.dumps(info, ensure_ascii=False), flush=True)
    etf_engine = MARGIN_STATE_ENGINE.replace("@TRANSITIONS@", repr(tuple(transitions)))
    cfg = dict(BASE)
    cfg.update({"source": "akshare", "codes": ["510050.SH"],
                "start_date": "2018-08-01", "end_date": "2026-11-26",
                "position_adjustment": "rebalance",
                "evaluation_start_date": "2018-08-24"})
    cfg.update(ETF_COSTS)
    rd = RUNS_ROOT / "st0010-etf-510050"
    (rd / "code").mkdir(parents=True, exist_ok=True)
    (rd / "code" / "signal_engine.py").write_text(etf_engine, encoding="utf-8")
    data_map = fetch_via_vt("akshare", ["510050.SH"], cfg["start_date"], cfg["end_date"])
    data_map["510050.SH"].to_csv(PREP / "st0010-etf-510050_510050.SH.csv")
    eidx = data_map["510050.SH"].index
    # transition decision dates -> next ETF trading day; plus first eval day
    exec_dates = set()
    first_eval = eidx[eidx >= pd.Timestamp("2018-08-24")][0]
    exec_dates.add(first_eval.strftime("%Y-%m-%d"))
    for d, w in transitions[1:]:
        td = pd.Timestamp(d)
        later = eidx[eidx > td]
        if len(later):
            exec_dates.add(later[0].strftime("%Y-%m-%d"))
    cfg["rebalance_mask"] = sorted(exec_dates)
    (rd / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest.append("st0010-etf-510050")
    print(f"MASK st0010-etf-510050: bars={len(eidx)} first_eval={first_eval.date()} "
          f"exec_dates={len(exec_dates)-1}", flush=True)

    (WORK / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("BUILT", len(manifest), "runs", flush=True)


if __name__ == "__main__":
    main()
