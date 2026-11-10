from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DetectionMetrics:
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    accuracy: float
    precision: float
    recall: float
    false_positive_rate: float
    processing_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactVerification:
    expected_links: int
    matched_links: int
    missing_links: tuple[str, ...]
    unexpected_links: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.missing_links and not self.unexpected_links

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "passed": self.passed,
        }


def evaluate_detection(
    predicted_changes: list[dict[str, Any]],
    expected_changes: list[dict[str, Any]],
    unchanged_checks: list[str],
    processing_time_ms: float,
) -> DetectionMetrics:
    """Calculate drift metrics using exact change records and explicit negatives."""
    predicted = {_canonical_json(change) for change in predicted_changes}
    expected = {_canonical_json(change) for change in expected_changes}

    true_positives = len(predicted & expected)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)
    predicted_objects = {_change_object(change) for change in predicted_changes}
    true_negatives = sum(
        unchanged_object not in predicted_objects
        for unchanged_object in unchanged_checks
    )

    total = true_positives + true_negatives + false_positives + false_negatives
    accuracy = _safe_divide(true_positives + true_negatives, total)
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    false_positive_rate = _safe_divide(
        false_positives,
        false_positives + true_negatives,
    )

    return DetectionMetrics(
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        false_positive_rate=round(false_positive_rate, 4),
        processing_time_ms=round(processing_time_ms, 3),
    )


def verify_impacts(
    predicted_findings: list[dict[str, Any]],
    expected_impacts: list[dict[str, Any]],
) -> ImpactVerification:
    """Verify affected source-file and function links against ground truth."""
    predicted_links = {
        _impact_link(
            finding["database_object"],
            affected["source_file"],
            affected.get("function_name"),
        )
        for finding in predicted_findings
        for affected in finding.get("affected_code", [])
    }
    expected_links = {
        _impact_link(
            impact["database_object"],
            reference["source_file"],
            reference.get("function_name"),
        )
        for impact in expected_impacts
        for reference in impact["references"]
    }
    return ImpactVerification(
        expected_links=len(expected_links),
        matched_links=len(predicted_links & expected_links),
        missing_links=tuple(sorted(expected_links - predicted_links)),
        unexpected_links=tuple(sorted(predicted_links - expected_links)),
    )


def build_evaluation_report(
    analysis_response: dict[str, Any],
    expected_change_data: dict[str, Any],
    expected_impact_data: dict[str, Any],
) -> dict[str, Any]:
    detection = evaluate_detection(
        analysis_response["changes"],
        expected_change_data["changes"],
        expected_change_data["unchanged_checks"],
        analysis_response["processing_time_ms"],
    )
    impacts = verify_impacts(
        analysis_response["findings"],
        expected_impact_data["impacts"],
    )
    passed = (
        detection.false_positives == 0
        and detection.false_negatives == 0
        and impacts.passed
    )
    return {
        "evaluation_passed": passed,
        "detection_metrics": detection.to_dict(),
        "impact_verification": impacts.to_dict(),
        "analysis_warnings": analysis_response.get("warnings", []),
        "metric_definitions": {
            "accuracy": "(true positives + true negatives) / all evaluated cases",
            "precision": "true positives / all detected changes",
            "recall": "true positives / all expected changes",
            "false_positive_rate": "false positives / all evaluated negative cases",
        },
    }


def save_evaluation_report(report: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _change_object(change: dict[str, Any]) -> str:
    change_type = change["change_type"]
    if change_type == "table_renamed":
        return change["old_name"]
    if change_type.startswith("table_"):
        return change["table"]
    column_name = (
        change["old_name"]
        if change_type == "column_renamed"
        else change["column"]
    )
    return f"{change['table']}.{column_name}"


def _impact_link(
    database_object: str,
    source_file: str,
    function_name: str | None,
) -> str:
    return f"{database_object}|{source_file}|{function_name or '<file>'}"


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0

