"""Run all harvest-validate-b2 backtests sequentially via the official VT CLI.

python -m backtest.runner <run_dir>  (cwd=/opt/vibe-trading/agent)
Task-local loader cache env (no global config change) so the three 503-name
pool runs share one network fetch. Sequential to respect free-source rate
limits. st0014-erc already ran during build (threshold fixed point) and is
skipped. A failure is recorded and the rest continue.
"""
import json
import os
import subprocess
import time
from pathlib import Path

WORK = Path("/root/projects/harvest-validate-b2/work")
RUNS_ROOT = Path("/root/.vibe-trading/runs/harvest-validate-b2")
LOGS = WORK / "logs"
LOGS.mkdir(exist_ok=True)
PY = "/opt/vibe-trading/venv/bin/python"
AGENT = "/opt/vibe-trading/agent"
ENV = {**os.environ,
       "VIBE_TRADING_DATA_CACHE": "true",
       "VIBE_TRADING_DATA_CACHE_ROOT": str(WORK / "data-cache")}

manifest = json.loads((WORK / "run_manifest.json").read_text())
status = {}
for name in manifest:
    rd = RUNS_ROOT / name
    t0 = time.time()
    metrics = rd / "artifacts" / "metrics.csv"
    if metrics.exists():
        status[name] = {"ok": True, "returncode": 0, "seconds": 0.0,
                        "metrics": str(metrics), "note": "pre-run during build"}
        print(f"SKIP {name} (already has metrics)", flush=True)
        (WORK / "run_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        continue
    log = LOGS / f"{name}.log"
    try:
        with log.open("w") as fh:
            proc = subprocess.run([PY, "-m", "backtest.runner", str(rd)],
                                  cwd=AGENT, stdout=fh, stderr=subprocess.STDOUT,
                                  timeout=2400, env=ENV)
        ok = proc.returncode == 0 and metrics.exists()
        status[name] = {"ok": ok, "returncode": proc.returncode,
                        "seconds": round(time.time() - t0, 1),
                        "metrics": str(metrics) if metrics.exists() else None}
    except subprocess.TimeoutExpired:
        status[name] = {"ok": False, "returncode": None, "seconds": round(time.time() - t0, 1),
                        "error": "timeout 2400s"}
    print(f"{'OK ' if status[name]['ok'] else 'FAIL'} {name} ({status[name]['seconds']}s)", flush=True)
    (WORK / "run_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

n_ok = sum(1 for v in status.values() if v["ok"])
print(f"DONE {n_ok}/{len(manifest)} runs ok", flush=True)
