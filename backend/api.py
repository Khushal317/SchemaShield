from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.api_models import (
    AnalysisRequest,
    AnalysisResponse,
    BaselineCaptureRequest,
    BaselineCaptureResponse,
    HealthResponse,
)
from backend.baseline_store import capture_baseline, load_baseline
from backend.code_analyzer import scan_project
from backend.impact_analyzer import analyze_impacts
from backend.schema_comparator import compare_schemas
from backend.schema_extractor import extract_schema


app = FastAPI(title="SchemaShield API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/baseline/capture", response_model=BaselineCaptureResponse)
def capture_baseline_endpoint(
    request: BaselineCaptureRequest,
) -> BaselineCaptureResponse:
    baseline_path = Path(request.baseline_path).expanduser().resolve()
    try:
        schema = capture_baseline(
            request.database_url.get_secret_value(),
            baseline_path,
            request.schema_name,
        )
    except SQLAlchemyError:
        _raise_api_error(
            502,
            "database_error",
            "Could not connect to PostgreSQL or read schema metadata",
        )
    except OSError as error:
        _raise_api_error(400, "baseline_write_error", str(error))

    return BaselineCaptureResponse(
        schema_name=schema.schema_name,
        table_count=len(schema.tables),
        column_count=sum(len(table.columns) for table in schema.tables.values()),
        baseline_path=str(baseline_path),
    )


@app.post("/analysis/run", response_model=AnalysisResponse)
def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    started_at = perf_counter()
    project_path = Path(request.project_path).expanduser().resolve()
    baseline_path = Path(request.baseline_path).expanduser().resolve()
    if not project_path.is_dir():
        _raise_api_error(400, "invalid_project_path", "project_path must be a directory")

    try:
        baseline = load_baseline(baseline_path)
    except FileNotFoundError:
        _raise_api_error(404, "baseline_not_found", "Capture a baseline before analysis")
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        _raise_api_error(400, "invalid_baseline", str(error))
    except OSError as error:
        _raise_api_error(400, "baseline_read_error", str(error))

    if baseline.schema_name != request.schema_name:
        _raise_api_error(
            400,
            "schema_mismatch",
            "The baseline schema does not match schema_name",
        )

    try:
        current = extract_schema(
            request.database_url.get_secret_value(),
            request.schema_name,
        )
    except SQLAlchemyError:
        _raise_api_error(
            502,
            "database_error",
            "Could not connect to PostgreSQL or read schema metadata",
        )

    try:
        changes = compare_schemas(baseline, current)
        code_analysis = scan_project(project_path)
        impact_report = analyze_impacts(changes, code_analysis)
    except (OSError, UnicodeError, ValueError) as error:
        _raise_api_error(400, "analysis_error", str(error))

    return AnalysisResponse(
        schema_name=request.schema_name,
        change_count=len(changes),
        processing_time_ms=round((perf_counter() - started_at) * 1000, 3),
        changes=[change.to_dict() for change in changes],
        findings=[finding.to_dict() for finding in impact_report.findings],
        warnings=[warning.to_dict() for warning in impact_report.warnings],
    )


def _raise_api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
