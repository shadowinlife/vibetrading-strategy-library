"""st-0010 data acquisition (harvest-validate-b1).

1. Archive the Eastmoney SSE margin aggregate snapshot IMMEDIATELY (2000-row
   endpoint cap makes the history start drift over time; brief requires a
   same-day archive).
2. Fetch Shanghai Composite daily (sina sh000001) via akshare.
3. Probe 510050 / 510300 ETF daily bars: eastmoney fund_etf_hist_em first,
   tencent kline fallback. Record availability honestly.

Outputs land in WORK (task dir); evidence copies are assembled later.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

WORK = Path("/root/projects/harvest-validate-b1/work")
WORK.mkdir(parents=True, exist_ok=True)
results = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S %Z")}

import akshare as ak

# --- 1. SSE margin snapshot (time-critical archive) -------------------------
try:
    sse = ak.stock_margin_sse(start_date="20100101", end_date="20261126")
    sse.to_csv(WORK / "st0010_sse_margin_snapshot_20261126.csv", index=False)
    d = pd.to_datetime(sse["信用交易日期"], format="%Y%m%d")
    results["sse_margin"] = {
        "ok": True, "rows": len(sse),
        "start": str(d.min().date()), "end": str(d.max().date()),
        "columns": list(sse.columns),
        "file": "st0010_sse_margin_snapshot_20261126.csv",
    }
except Exception as exc:
    results["sse_margin"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    traceback.print_exc()
print("SSE_MARGIN", json.dumps(results["sse_margin"], ensure_ascii=False), flush=True)

# --- 2. Shanghai Composite daily (sina) -------------------------------------
try:
    idx = ak.index_zh_daily_sina(symbol="sh000001")
    idx.to_csv(WORK / "st0010_sh000001_sina_daily.csv", index=False)
    d = pd.to_datetime(idx["date"])
    results["sh_index"] = {
        "ok": True, "rows": len(idx),
        "start": str(d.min().date()), "end": str(d.max().date()),
        "columns": list(idx.columns),
        "file": "st0010_sh000001_sina_daily.csv",
    }
except Exception as exc:
    results["sh_index"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    traceback.print_exc()
print("SH_INDEX", json.dumps(results["sh_index"], ensure_ascii=False), flush=True)

# --- 3. ETF proxy probes -----------------------------------------------------
def probe_em(symbol):
    df = ak.fund_etf_hist_em(symbol=symbol, period="daily",
                             start_date="20180101", end_date="20261126", adjust="")
    return df

def probe_tencent(symbol):
    # tencent kline API: sh510050 / sh510300, daily, unadjusted
    import requests
    market = "sh" + symbol
    url = ("https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
           f"?param={market},day,2018-01-01,2026-11-26,2000,qfq")
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    doc = r.json()
    data = doc["data"][market]
    rows = data.get("qfqday") or data.get("day")
    df = pd.DataFrame([x[:6] for x in rows],
                      columns=["date", "open", "close", "high", "low", "volume"])
    return df

for sym in ("510050", "510300"):
    entry = {}
    for name, fn in (("eastmoney_fund_etf_hist_em", probe_em),
                     ("tencent_kline_qfq", probe_tencent)):
        try:
            df = fn(sym)
            if df is None or len(df) == 0:
                entry[name] = {"ok": False, "error": "empty frame"}
                continue
            fname = f"st0010_etf_{sym}_{name.split('_')[0]}.csv"
            df.to_csv(WORK / fname, index=False)
            dates = pd.to_datetime(df.iloc[:, 0].astype(str))
            entry[name] = {"ok": True, "rows": len(df),
                           "start": str(dates.min().date()),
                           "end": str(dates.max().date()),
                           "columns": list(df.columns), "file": fname}
            break  # first successful source wins; record which one
        except Exception as exc:
            entry[name] = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
        time.sleep(2)
    results[f"etf_{sym}"] = entry
    print(f"ETF_{sym}", json.dumps(entry, ensure_ascii=False), flush=True)

(WORK / "st0010_fetch_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("DONE", flush=True)
