"""in-0002 complete sample: market-cap/GDP (Buffett indicator), three markets.

Primary source: World Bank CM.MKT.LCAP.CD (listed domestic companies, current
US$) / NY.GDP.MKTP.CD (nominal GDP, current US$), year 2024, same-source USD
ratio (no FX conversion needed). Live cross-checks: S&P 500 pool mcap sum
(yfinance, in-0004 fetch) and full A-share mcap sum (tencent, in-0001 fetch).
"""
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))


def wb(country, indicator, date="2024:2024"):
    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
           f"?format=json&date={date}&per_page=50")
    with urllib.request.urlopen(url, timeout=60) as r:
        doc = json.loads(r.read().decode())
    rows = {x["date"]: x["value"] for x in doc[1] if x["value"] is not None}
    return rows, doc[0].get("lastupdated")


results = {"source": "World Bank public API, fetched 2026-11-26",
           "caliber": "listed domestic companies mcap / nominal GDP, both current US$, year-end 2024",
           "markets": {}}
for name, country in (("us", "USA"), ("ashare", "CHN"), ("hk", "HKG")):
    mc, lu1 = wb(country, "CM.MKT.LCAP.CD")
    gd, lu2 = wb(country, "NY.GDP.MKTP.CD")
    m, g = mc.get("2024"), gd.get("2024")
    results["markets"][name] = {
        "country": country,
        "mcap_2024_usd": m, "gdp_2024_usd": g,
        "ratio_pct": round(m / g * 100, 2) if m and g else None,
        "lastupdated": {"mcap": lu1, "gdp": lu2},
    }
    print(name, json.dumps(results["markets"][name]), flush=True)

us_pool = pd.read_csv(OUT / "in0004_us_mcaps.csv", index_col=0)
results["crosschecks"] = {
    "sp500_pool_mcap_usd": float(us_pool["market_cap"].sum()),
    "sp500_pool_vs_wb_us_pct": round(float(us_pool["market_cap"].sum()) / results["markets"]["us"]["mcap_2024_usd"] * 100, 2),
    "note": "S&P500 pool is a large-cap subset (not full market); ratio to WB total shows coverage; dates differ (live vs 2024 year-end)",
}
try:
    tx = pd.read_csv(OUT / "in0001_tencent_a_spot.csv")
    total_yi = pd.to_numeric(tx["zsz"], errors="coerce").sum()
    results["crosschecks"]["ashare_live_total_mcap_yi_yuan"] = round(float(total_yi), 2)
    results["crosschecks"]["ashare_live_total_mcap_wan_yi"] = round(float(total_yi) / 1e4, 4)
except FileNotFoundError:
    results["crosschecks"]["ashare_live"] = "tencent snapshot not yet written"

(OUT / "in0002_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE in0002_results.json")
print(json.dumps(results["crosschecks"], ensure_ascii=False))