"""Fit the abstention threshold on the synthetic eval set and write backend/fixtures/calibration.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.evaluation.runner import run_eval, calibrate_threshold  # noqa: E402

r = run_eval(threshold=0.0)
t = calibrate_threshold([{"cov": x["cov"], "answerable": x["answerable"]} for x in r["results"]])
out = Path(__file__).resolve().parents[1] / "backend/fixtures/calibration.json"
out.write_text(json.dumps({"relevance_threshold": t, "fit_on": "fixtures/eval_cases.json", "note": "in-sample; see leave_one_out"}, indent=1))
print("threshold", t)
