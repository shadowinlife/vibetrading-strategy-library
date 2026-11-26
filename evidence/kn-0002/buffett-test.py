"""kn-0002 empirical test: US market-cap/GDP ratio vs forward 10-year returns.

Data: World Bank CM.MKT.LCAP.CD (listed domestic companies, current US$, year-end)
and NY.GDP.MKTP.CD (nominal GDP), both fetched live from the public API.
Forward returns: S&P 500 Total Return (^SP500TR, 1988+) primary; S&P 500 price
(^GSPC, 1970+) secondary with the dividend omission stated.
"""
import json
import os
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.environ.get("VALIDATE_EVIDENCE_DIR", "/tmp/library-validate-001/evidence"))


def wb_series(country, indicator, date="1960:2024"):
    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
           f"?format=json&date={date}&per_page=200")
    with urllib.request.urlopen(url, timeout=60) as r:
        doc = json.loads(r.read().decode())
    rows = {int(x["date"]): float(x["value"]) for x in doc[1] if x["value"] is not None}
    return pd.Series(rows).sort_index(), doc[0].get("lastupdated")


def year_end_close(csv, sym):
    df = pd.read_csv(csv, index_col=0, parse_dates=True)
    col = "Close" if "Close" in df.columns else df.columns[0]
    s = df[col]
    return s.groupby(s.index.year).last()


mcap, lu1 = wb_series("USA", "CM.MKT.LCAP.CD", "1970:2024")
gdp, lu2 = wb_series("USA", "NY.GDP.MKTP.CD", "1960:2024")
ratio = (mcap / gdp * 100.0).dropna()
ratio.to_csv(OUT / "kn0002_us_buffett_ratio_annual.csv", header=["ratio_pct"])

tr = year_end_close(OUT / "index_SP500TR_history.csv", "^SP500TR")
px = year_end_close(OUT / "index_GSPC_history.csv", "^GSPC")


def forward_test(ratio, idx, horizon=10, label=""):
    rows = []
    for year, r in ratio.items():
        if year in idx.index and (year + horizon) in idx.index:
            fwd = (idx[year + horizon] / idx[year]) ** (1 / horizon) - 1.0
            rows.append({"year": int(year), "ratio_pct": float(r),
                         "fwd_10y_cagr": float(fwd)})
    df = pd.DataFrame(rows)
    if len(df) < 5:
        return {"label": label, "n": len(df), "error": "too few observations"}
    pear = float(np.corrcoef(df["ratio_pct"], df["fwd_10y_cagr"])[0, 1])
    spear = float(df["ratio_pct"].corr(df["fwd_10y_cagr"], method="spearman"))
    x = df["ratio_pct"].values
    y = df["fwd_10y_cagr"].values
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = np.sqrt(np.sum(resid**2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    df["quintile"] = pd.qcut(df["ratio_pct"], 5, labels=False, duplicates="drop") + 1
    buckets = df.groupby("quintile").agg(
        n=("year", "count"), ratio_min=("ratio_pct", "min"),
        ratio_max=("ratio_pct", "max"), mean_fwd_cagr=("fwd_10y_cagr", "mean"))
    return {
        "label": label, "n": len(df),
        "first_year": int(df["year"].min()), "last_year": int(df["year"].max()),
        "pearson_r": round(pear, 4), "spearman_r": round(spear, 4),
        "ols_slope_per_pct_point": round(float(slope), 6),
        "ols_slope_tstat": round(float(slope / se), 3) if se > 0 else None,
        "quintile_buckets": buckets.round(4).to_dict(orient="index"),
        "note": "overlapping 10y windows; naive t-stat inflated; research-level",
    }, df


res_tr, df_tr = forward_test(ratio, tr, label="SP500TR_total_return")
res_px, df_px = forward_test(ratio, px, label="GSPC_price_only")
df_tr.to_csv(OUT / "kn0002_forward_pairs_tr.csv", index=False)
df_px.to_csv(OUT / "kn0002_forward_pairs_px.csv", index=False)

summary = {
    "data_sources": {
        "market_cap": "World Bank CM.MKT.LCAP.CD, USA, listed domestic companies, current US$",
        "gdp": "World Bank NY.GDP.MKTP.CD, USA, current US$",
        "lastupdated": {"mcap": lu1, "gdp": lu2},
        "returns_primary": "yfinance ^SP500TR (S&P 500 Total Return), year-end closes",
        "returns_secondary": "yfinance ^GSPC (price only, dividends excluded)",
    },
    "ratio_range_pct": {"min": round(float(ratio.min()), 2), "max": round(float(ratio.max()), 2),
                        "y2024": round(float(ratio.loc[2024]), 2),
                        "y2000": round(float(ratio.loc[2000]), 2) if 2000 in ratio.index else None,
                        "y1980": round(float(ratio.loc[1980]), 2) if 1980 in ratio.index else None},
    "test_total_return": res_tr,
    "test_price_only": res_px,
}
(OUT / "kn0002_test_results.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))