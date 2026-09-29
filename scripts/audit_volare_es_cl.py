"""Run the ES/CL evidence and calendar audit without modifying modelling data."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from volare_data import quality_flags, validate_source
from volare_review import reconcile_reviews, weekday_calendar_audit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / "datasets/realized_variance_futures.csv"
    ledger_path = ROOT / "datasets/volare_review_decisions.csv"
    source_hash = digest(source)
    data = validate_source(pd.read_csv(source))
    flags = quality_flags(data)
    ledger = pd.read_csv(ledger_path, keep_default_na=False)
    reviewed = reconcile_reviews(flags, ledger, source_hash)
    reviewed = reviewed.loc[reviewed.symbol.isin(["ES", "CL"])].sort_values(["date", "symbol"])
    calendar = weekday_calendar_audit(data)
    gaps = calendar.loc[calendar.observed_count.lt(2)]
    destination = ROOT / "reports/volare"
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, frame in [("es_cl_flag_evidence", reviewed), ("es_cl_calendar_audit", calendar),
                        ("es_cl_calendar_gaps", gaps)]:
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False, date_format="%Y-%m-%d", float_format="%.17g")
        outputs[path.name] = digest(path)
    summary = {
        "source_sha256": source_hash,
        "ledger_sha256": digest(ledger_path),
        "code_sha256": {p.name: digest(p) for p in (Path(__file__), ROOT / "volare_review.py", ROOT / "volare_data.py")},
        "output_sha256": outputs,
        "flagged_es_cl_records": len(reviewed),
        "review_counts": reviewed.decision.value_counts().to_dict(),
        "weekdays_both_absent": int(((calendar.date.dt.dayofweek < 5) & calendar.observed_count.eq(0)).sum()),
        "dates_only_one_observed": int(calendar.observed_count.eq(1).sum()),
        "observed_weekend_dates": int((calendar.date.dt.dayofweek >= 5).sum()),
        "joint_missing_without_holiday_candidate": int((calendar.observed_count.eq(0) & calendar.candidate_holiday.eq("")).sum()),
        "calendar_verified": False, "cleaning_applied": False,
    }
    if digest(source) != source_hash:
        raise RuntimeError("Source changed during audit; rerun from a fixed snapshot")
    (destination / "es_cl_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if "sha256" not in k}, indent=2))


if __name__ == "__main__":
    main()
