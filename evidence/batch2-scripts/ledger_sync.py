"""Ledger sync for harvest-validate-b2 via the official in-process SDM code path.

All 6 batch-2 entries registered through SdmRegisterTool().execute() (sdm_register
is not exposed over MCP). validation_status mapping (honest): library validated ->
SDM validated; library research_only -> SDM unvalidated (SDM has no research_only
value); library rejected -> SDM rejected. Fields taken verbatim from the updated
library frontmatter. Run with VT venv, cwd=/opt/vibe-trading/agent, AFTER the
verification commit so source_url pins the committed blob.
"""
import json
import sys
from pathlib import Path

import yaml

from src.tools.sdm_register_tool import SdmRegisterTool

LIB = Path("/opt/strategy-library")
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
REPO = "https://github.com/shadowinlife/vibetrading-strategy-library/blob/" + COMMIT
DATE = "2026-11-26"
TASK = Path("/root/projects/harvest-validate-b2")

ENTRY_PATHS = {
    "st-0004": "strategies/st-0004-tsmom-12month.md",
    "st-0007": "strategies/st-0007-jegadeesh-short-term-reversal.md",
    "st-0008": "strategies/st-0008-ang-low-volatility.md",
    "st-0011": "strategies/st-0011-pair-trading-zscore.md",
    "st-0012": "strategies/st-0012-hv-percentile-regime.md",
    "st-0014": "strategies/st-0014-risk-parity-etf.md",
}


def fm(entry_id):
    raw = (LIB / ENTRY_PATHS[entry_id]).read_text(encoding="utf-8")
    parts = raw.split("\n")
    end = next(i for i in range(1, len(parts)) if parts[i].strip() == "---")
    return yaml.safe_load("\n".join(parts[1:end]))


def sdm_status(lib_status):
    if lib_status == "validated":
        return "validated"
    if lib_status == "rejected":
        return "rejected"
    return "unvalidated"


results = {}
tool = SdmRegisterTool()
for entry_id, rel in ENTRY_PATHS.items():
    f = fm(entry_id)
    params = {
        "artifact_type": "strategy",
        "name": f"{entry_id} {f['title']}",
        "universe": ",".join(f["markets"]),
        "source_paper": f["sources"][0]["title"],
        "source_url": REPO + "/" + rel,
        "intended_use": f["intended_use"],
        "limitations": f["limitations"],
        "validation_status": sdm_status(f["status"]),
        "signal_definition": f.get("signal_definition"),
        "entry_rules": f.get("entry_rules"),
        "exit_rules": f.get("exit_rules"),
        "position_sizing": f.get("position_sizing"),
    }
    if f["status"] in ("validated", "rejected"):
        params["validation_date"] = DATE
        params["validator"] = "harvest-validate-b2 (worker, independent backtest validation)"
    out = tool.execute(**params)
    doc = json.loads(out)
    if doc.get("status") == "ok":
        a = doc["artifact"]
        results[entry_id] = {"action": "register", "id": a["id"],
                             "validation_status": a["validation_status"],
                             "library_status": f["status"]}
    else:
        results[entry_id] = {"action": "register", "error": doc.get("error"),
                             "library_status": f["status"]}

print(json.dumps(results, ensure_ascii=False, indent=2))
(TASK / "ledger_sync.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
ok = all("error" not in v for v in results.values())
sys.exit(0 if ok else 1)
