"""Debug session logging (NDJSON). Remove after investigation."""
import json
import time
import uuid
from pathlib import Path

DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent / "pipelines" / "debug-702280.log"
SESSION_ID = "702280"


def agent_log(hypothesis_id, location, message, data=None, run_id="post-fix"):
    # region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "id": f"log_{uuid.uuid4().hex[:12]}",
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    # endregion
