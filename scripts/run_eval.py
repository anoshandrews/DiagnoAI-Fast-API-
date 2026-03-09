#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.schemas import ChatMessage
from backend.app.services.report_generator import generate_medical_report


def load_cases(fixtures_path: Path) -> list[dict[str, Any]]:
    with fixtures_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def score_case(case: dict[str, Any]) -> dict[str, Any]:
    history = [ChatMessage.model_validate(message) for message in case["chat_history"]]
    report = generate_medical_report(history)

    summary = report.patient_summary.lower()
    markdown_red_flags = " ".join(report.red_flags).lower()
    markdown_steps = " ".join(report.recommended_next_steps).lower()
    disclaimer = report.disclaimer.lower()

    summary_hits = [
        phrase for phrase in case.get("expected_summary_contains", [])
        if phrase.lower() in summary
    ]
    urgent_needed = case.get("requires_urgent_language", False)
    urgent_hit = any(
        token in f"{markdown_red_flags} {markdown_steps}"
        for token in ("urgent", "emergency", "seek", "911")
    )

    checks = {
        "summary_coverage": len(summary_hits) == len(case.get("expected_summary_contains", [])),
        "disclaimer_present": "not a diagnosis" in disclaimer,
        "timeline_present": bool(report.symptom_timeline),
        "red_flags_present": bool(report.red_flags),
        "recommendations_present": bool(report.recommended_next_steps),
        "urgent_language": (not urgent_needed) or urgent_hit,
    }
    passed = sum(checks.values())

    return {
        "id": case["id"],
        "score": passed,
        "max_score": len(checks),
        "checks": checks,
        "patient_summary": report.patient_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight golden-case evals.")
    parser.add_argument(
        "--fixtures",
        default="evals/fixtures/golden_cases.json",
        help="Path to the golden eval fixture file.",
    )
    parser.add_argument(
        "--output",
        default="evals/results/latest.json",
        help="Path to write the eval results JSON.",
    )
    args = parser.parse_args()

    fixtures_path = Path(args.fixtures)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cases = load_cases(fixtures_path)
    results = [score_case(case) for case in cases]
    summary = {
        "cases": results,
        "passed_checks": sum(item["score"] for item in results),
        "total_checks": sum(item["max_score"] for item in results),
        "fixtures": str(fixtures_path),
    }

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
