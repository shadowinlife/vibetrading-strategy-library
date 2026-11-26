"""Run all harvest-validate-b1 backtests sequentially via the official VT CLI.

python -m backtest.runner <run_dir>  (cwd=/opt/vibe-trading/agent)
Logs per run; status JSON at the end. Sequential to respect free-source rate
limits. Each run is independent; a failure is recorded and the rest continue.
"""
import json
import subprocess
import time
from pathlib import Path

WORK = Path("/root/projects/harvest-validate-b1/work")
RUNS_ROOT = Path("/root/.vibe-trading/runs/harvest-validate-b1")
LOGS = WORK / "logs"
LOGS.mkdir(exist_ok=True)
PY = "/opt/vibe-trading/venv/bin/python"
AGENT = "/opt/vibe-trading/agent"

manifest = json.loads((WORK / "run_manifest.json").read_text())
status = {}
for name in manifest:
    rd = RUNS_ROOT / name
    t0 = time.time()
    metrics = rd / "artifacts" / "metrics.csv"
    if metrics.exists():
        status[name] = {"ok": True, "returncode": 0, "seconds": 0.0,
                        "metrics": str(metrics), "note": "pre-run in smoke test"}
        print(f"SKIP {name} (already has metrics)", flush=True)
        (WORK / "run_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        continue
    log = LOGS / f"{name}.log"
    with log.open("w") as fh:
        proc = subprocess.run([PY, "-m", "backtest.runner", str(rd)],
                              cwd=AGENT, stdout=fh, stderr=subprocess.STDOUT,
                              timeout=900)
    ok = proc.returncode == 0 and metrics.exists()
    status[name] = {"ok": ok, "returncode": proc.returncode,
                    "seconds": round(time.time() - t0, 1),
                    "metrics": str(metrics) if metrics.exists() else None}
    print(f"{'OK ' if ok else 'FAIL'} {name} ({status[name]['seconds']}s)", flush=True)
    (WORK / "run_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

n_ok = sum(1 for v in status.values() if v["ok"])
print(f"DONE {n_ok}/{len(manifest)} runs ok", flush=True)
