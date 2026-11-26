"""in-0001 complete sample: banking industry valuation (aggregate method).

Sources (all free, live):
- Tencent full A-share spot: total mcap (zsz, 亿元), PE_TTM, price per name.
- Bank pool = every A-share whose name contains 银行 (from the full snapshot).
- Sina financial indicators: latest 每股净资产 per bank -> aggregate PB.
- Sina dividend detail: trailing-12m implemented cash dividends -> yield.
- cninfo (official) industry static PE for 货币金融服务: cross-check + monthly
  history grid (2023-12 onward, source depth limit) for the current percentile.
Caliber: aggregate method (整体法) = sum(mcap)/sum(earnings or net assets);
loss-making names excluded from PE per entry. Units documented per source.
"""
import json
import os
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))
results = {}


def tencent_full_spot():
    url = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList"
    rows, offset, total = [], 0, None
    while True:
        params = {"_appver": "11.17.0", "board_code": "aStock", "sort_type": "price",
                  "direct": "down", "offset": str(offset), "count": "200"}
        d = requests.get(url, params=params, timeout=30).json()
        data = d["data"]
        total = int(data["total"])
        batch = data["rank_list"]
        rows.extend(batch)
        offset += len(batch)
        if not batch or offset >= total:
            break
        time.sleep(0.4)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "in0001_tencent_a_spot.csv", index=False)
    return df, total


spot, total = tencent_full_spot()
for c in ("zsz", "pe_ttm", "zxj", "turnover"):
    spot[c] = pd.to_numeric(spot[c], errors="coerce")
results["tencent_spot"] = {"rows": len(spot), "total_reported": total,
                           "total_mcap_yi_yuan": round(float(spot["zsz"].sum()), 2),
                           "total_mcap_wan_yi": round(float(spot["zsz"].sum()) / 1e4, 4)}
print("TENCENT", json.dumps(results["tencent_spot"]), flush=True)

banks = spot[spot["name"].astype(str).str.contains("银行", na=False)].copy()
banks["code6"] = banks["code"].str.extract(r"(\d{6})")
results["bank_pool"] = {"n": len(banks), "codes": banks["code6"].tolist()}
print("BANK_POOL", len(banks), flush=True)

import akshare as ak

bps_rows, div_rows, fails = [], [], []
for i, (_, b) in enumerate(banks.iterrows()):
    code = b["code6"]
    try:
        fi = ak.stock_financial_analysis_indicator(symbol=code, start_year="2024")
        col = "每股净资产_调整前(元)"
        fi = fi[pd.to_numeric(fi[col], errors="coerce").notna()]
        latest = fi.iloc[-1]
        bps_rows.append({"code": code, "name": b["name"], "report_date": str(latest["日期"]),
                         "bps_yuan": float(latest[col])})
    except Exception as exc:
        fails.append({"code": code, "stage": "bps", "error": str(exc)[:100]})
    try:
        dv = ak.stock_history_dividend_detail(symbol=code, indicator="分红")
        dv["除权除息日"] = pd.to_datetime(dv["除权除息日"], errors="coerce")
        lo = pd.Timestamp("2025-11-26")
        hi = pd.Timestamp("2026-11-26")
        sel = dv[(dv["除权除息日"] >= lo) & (dv["除权除息日"] <= hi)
                 & (dv["进度"].astype(str) == "实施")]
        per_share = pd.to_numeric(sel["派息"], errors="coerce").fillna(0).sum() / 10.0
        div_rows.append({"code": code, "name": b["name"],
                         "dividend_per_share_12m": float(per_share),
                         "n_events": len(sel)})
    except Exception as exc:
        fails.append({"code": code, "stage": "div", "error": str(exc)[:100]})
    if i % 10 == 9:
        time.sleep(1)
        print(f"  banks {i+1}/{len(banks)}", flush=True)

bps = pd.DataFrame(bps_rows).set_index("code")
divs = pd.DataFrame(div_rows).set_index("code")
banks = banks.set_index("code6")
banks["mcap_yi"] = banks["zsz"]
banks["price"] = banks["zxj"]
banks["shares_yi"] = banks["mcap_yi"] / banks["price"]
banks["bps"] = bps["bps_yuan"]
banks["net_assets_yi"] = banks["shares_yi"] * banks["bps"]
banks["earnings_ttm_yi"] = banks["mcap_yi"] / banks["pe_ttm"]
banks["div_per_share"] = divs["dividend_per_share_12m"]
banks["div_total_yi"] = banks["div_per_share"] * banks["shares_yi"]
banks.to_csv(OUT / "in0001_bank_constituents.csv")

pe_valid = banks[banks["pe_ttm"] > 0]
pb_valid = banks[banks["net_assets_yi"] > 0]
agg = {
    "n_banks": len(banks),
    "n_pe_valid": len(pe_valid),
    "n_pb_valid": len(pb_valid),
    "total_mcap_yi_yuan": round(float(banks["mcap_yi"].sum()), 2),
    "pe_ttm_aggregate": round(float(pe_valid["mcap_yi"].sum() / pe_valid["earnings_ttm_yi"].sum()), 4),
    "pb_aggregate": round(float(pb_valid["mcap_yi"].sum() / pb_valid["net_assets_yi"].sum()), 4),
    "dividend_yield_pct": round(float(banks["div_total_yi"].sum() / banks["mcap_yi"].sum() * 100), 4),
    "bps_report_dates": sorted(bps["report_date"].unique().tolist()),
    "fetch_failures": fails,
    "caliber": "aggregate method; mcap unit 亿元 (tencent zsz); PE excludes pe_ttm<=0; PB uses latest 每股净资产_调整前 x shares; dividends = implemented ex-date in trailing 12m",
}
results["bank_aggregates"] = agg
print("AGG", json.dumps(agg, ensure_ascii=False)[:500], flush=True)

cninfo_latest = ak.stock_industry_pe_ratio_cninfo(symbol="证监会行业分类", date="20261125")
cninfo_latest.to_csv(OUT / "in0001_cninfo_industry_pe_20261125.csv", index=False)
bank_row = cninfo_latest[cninfo_latest["行业名称"] == "货币金融服务"].iloc[0]
check = {
    "cninfo_static_pe_weighted": float(bank_row["静态市盈率-加权平均"]),
    "cninfo_total_mcap_yi": float(bank_row["总市值-静态"]),
    "cninfo_net_profit_yi": float(bank_row["净利润-静态"]),
    "formula_check_pe": round(float(bank_row["总市值-静态"]) / float(bank_row["净利润-静态"]), 4),
    "n_companies": int(bank_row["公司数量"]),
    "n_included": int(bank_row["纳入计算公司数量"]),
}
results["cninfo_crosscheck"] = check
print("CNINFO", json.dumps(check), flush=True)

hist = []
months = pd.period_range("2023-12", "2026-11", freq="M")
for p in months:
    candidates = pd.date_range(p.end_time.normalize() - pd.Timedelta(days=6),
                               p.end_time.normalize(), freq="B")[-4:]
    got = None
    for d in reversed(candidates):
        ds = d.strftime("%Y%m%d")
        try:
            df = ak.stock_industry_pe_ratio_cninfo(symbol="证监会行业分类", date=ds)
            row = df[df["行业名称"] == "货币金融服务"]
            if len(row):
                got = {"date": d.strftime("%Y-%m-%d"),
                       "pe_static": float(row["静态市盈率-加权平均"].iloc[0])}
                break
        except Exception:
            continue
    if got:
        hist.append(got)
    time.sleep(0.3)
hist_df = pd.DataFrame(hist)
hist_df.to_csv(OUT / "in0001_bank_pe_history_cninfo.csv", index=False)
current_pe = check["cninfo_static_pe_weighted"]
series = hist_df["pe_static"]
pctile = float((series < current_pe).mean() * 100)
results["percentile"] = {
    "current_pe_static": current_pe,
    "history_points": len(hist_df),
    "history_start": hist_df["date"].iloc[0] if len(hist_df) else None,
    "history_end": hist_df["date"].iloc[-1] if len(hist_df) else None,
    "current_percentile_in_window": round(pctile, 2),
    "window_note": "cninfo free history depth ~2023-12 onward, monthly sampled; NOT the 10y daily window the entry suggests",
}
print("PCTILE", json.dumps(results["percentile"]), flush=True)

(OUT / "in0001_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE in0001_results.json", flush=True)