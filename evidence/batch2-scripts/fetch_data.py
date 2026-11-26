"""Data acquisition for harvest-validate-b2 via the official VT loader path.

Groups:
  etf   - 11 US ETFs (st-0004 pool+BIL, st-0011 KO/PEP, st-0014 subset, st-0012 SPY)
  okx   - BTC-USDT / ETH-USDT daily (st-0011 crypto pair, st-0012 crypto);
          ETH depth probe from 2017-01-01 recorded honestly.
  pool  - S&P500 503 snapshot (st-0002 pools.json precedent) + SPY.US benchmark
          carrier, 2013-01-01 -> 2026-11-25 (st-0007 / st-0008).

Cache: VIBE_TRADING_DATA_CACHE=true with cache root INSIDE the task work dir
(per-process env, no global config change) so the three 503-name pool runs
share one network fetch. end_date=2026-11-25 (last settled bar; today's US
session is still open at fetch time and crypto daily bar is forming).

Run: /opt/vibe-trading/venv/bin/python, cwd=/opt/vibe-trading/agent.
"""
import json
import os
import sys
import time
from pathlib import Path

WORK = Path("/root/projects/harvest-validate-b2/work")
os.environ["VIBE_TRADING_DATA_CACHE"] = "true"
os.environ["VIBE_TRADING_DATA_CACHE_ROOT"] = str(WORK / "data-cache")

import pandas as pd  # noqa: E402

PREP = WORK / "prep"
PREP.mkdir(parents=True, exist_ok=True)
END = "2026-11-25"

POOLS = json.loads(Path("/opt/strategy-library/evidence/st-0002/pools.json").read_text())
SP500 = POOLS["sp500"]["tickers"]
assert len(SP500) == 503, len(SP500)

ETF_CODES = [c + ".US" for c in
             ["SPY", "EFA", "EEM", "IEF", "GLD", "DBC", "VNQ", "UUP", "BIL", "KO", "PEP"]]
POOL_CODES = [t + ".US" for t in SP500] + ["SPY.US"]


def fetch_via_vt(source, codes, start, end):
    from backtest.runner import _get_loader
    diagnostics = []
    loader = _get_loader(source, diagnostics=diagnostics)()
    data_map = loader.fetch(codes, start, end, interval="1D")
    return data_map


def fetch_group(name, source, codes, start, end, attempts=4):
    """Fetch with retry+backoff (batch1 rate-limit lesson); archive every symbol."""
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            t0 = time.time()
            dm = fetch_via_vt(source, codes, start, end)
            missing = [c for c in codes if c not in dm or dm[c].empty]
            if missing and len(missing) > max(2, int(0.02 * len(codes))):
                raise RuntimeError(f"too many missing: {len(missing)} {missing[:10]}")
            info = {"group": name, "source": source, "requested": len(codes),
                    "fetched": len(dm), "missing": missing,
                    "start": start, "end": end, "attempt": attempt,
                    "seconds": round(time.time() - t0, 1), "symbols": {}}
            for c, df in dm.items():
                df.to_csv(PREP / f"{name}_{c}.csv")
                info["symbols"][c] = {"rows": int(len(df)),
                                      "first": str(df.index[0].date()),
                                      "last": str(df.index[-1].date())}
            (WORK / f"fetch_{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
            print(f"FETCH {name}: {len(dm)}/{len(codes)} in {info['seconds']}s "
                  f"(attempt {attempt}), missing={missing}", flush=True)
            return dm, info
        except Exception as exc:  # noqa: BLE001 - retry boundary
            last_err = str(exc)
            wait = 30 * attempt
            print(f"FETCH {name} attempt {attempt} FAILED: {last_err}; sleep {wait}s", flush=True)
            time.sleep(wait)
    (WORK / f"fetch_{name}.json").write_text(json.dumps(
        {"group": name, "error": last_err, "requested": len(codes)}, ensure_ascii=False, indent=2))
    print(f"FETCH {name} GAVE UP: {last_err}", flush=True)
    return None, {"error": last_err}


def main():
    results = {}

    # ETH depth probe (brief: probe ETH-USDT OKX history depth first)
    probe = {}
    try:
        dm = fetch_via_vt("okx", ["ETH-USDT"], "2017-01-01", "2017-12-31")
        if "ETH-USDT" in dm and not dm["ETH-USDT"].empty:
            df = dm["ETH-USDT"]
            probe = {"ok": True, "first_bar": str(df.index[0].date()),
                     "last_bar": str(df.index[-1].date()), "rows": int(len(df))}
        else:
            probe = {"ok": False, "note": "no ETH-USDT bars in 2017-01-01..2017-12-31"}
    except Exception as exc:  # noqa: BLE001
        probe = {"ok": False, "error": str(exc)}
    print("ETH_PROBE", json.dumps(probe), flush=True)
    results["eth_probe_2017"] = probe

    _, results["etf"] = fetch_group("etf", "yfinance", ETF_CODES, "2013-06-01", END)
    _, results["okx"] = fetch_group("okx", "okx", ["BTC-USDT", "ETH-USDT"], "2017-12-01", END)
    _, results["pool"] = fetch_group("pool", "yfinance", POOL_CODES, "2013-01-01", END)

    # GICS sectors for st-0008 concentration report (same GitHub datasets source
    # as the st-0002 constituent snapshot).
    try:
        import requests
        url = ("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
               "main/constituents.csv")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        (WORK / "sp500_constituents.csv").write_text(r.text, encoding="utf-8")
        results["sectors"] = {"ok": True, "rows": len(r.text.splitlines()) - 1}
    except Exception as exc:  # noqa: BLE001
        results["sectors"] = {"ok": False, "error": str(exc)}
    print("SECTORS", json.dumps(results["sectors"]), flush=True)

    (WORK / "fetch_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    ok = all("error" not in results.get(g, {"error": "missing"}) for g in ("etf", "okx", "pool"))
    print("FETCH_ALL_OK" if ok else "FETCH_INCOMPLETE", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
