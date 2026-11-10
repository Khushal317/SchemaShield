from fastapi.testclient import TestClient

from backend import api
from backend.code_models import CodeAnalysisResult
from backend.schema_models import ColumnSchema, DatabaseSchema, TableSchema


client = TestClient(api.app)
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost/test"


def schema_with_column(column_name):
    return DatabaseSchema(
        schema_name="schemashield_demo",
        tables={
            "customers": TableSchema(
                name="customers",
                columns={
                    column_name: ColumnSchema(
                        name=column_name,
                        ordinal_position=1,
                        data_type="character varying",
                        character_maximum_length=100,
                        is_nullable=False,
                    )
                },
            )
        },
    )


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capture_baseline_endpoint_returns_schema_summary(monkeypatch):
    schema = schema_with_column("full_name")
    monkeypatch.setattr(api, "capture_baseline", lambda *args: schema)

    response = client.post(
        "/baseline/capture",
        json={
            "database_url": DATABASE_URL,
            "schema_name": "schemashield_demo",
            "baseline_path": "baseline.json",
        },
    )

    assert response.status_code == 200
    assert response.json()["schema_name"] == "schemashield_demo"
    assert response.json()["table_count"] == 1
    assert response.json()["column_count"] == 1
    assert response.json()["baseline_path"].endswith("baseline.json")


def test_analysis_endpoint_runs_completed_pipeline(monkeypatch, tmp_path):
    baseline = schema_with_column("full_name")
    current = schema_with_column("name")
    monkeypatch.setattr(api, "load_baseline", lambda path: baseline)
    monkeypatch.setattr(api, "extract_schema", lambda *args: current)
    monkeypatch.setattr(api, "scan_project", lambda path: CodeAnalysisResult())

    response = client.post(
        "/analysis/run",
        json={
            "database_url": DATABASE_URL,
            "schema_name": "schemashield_demo",
            "baseline_path": "baseline.json",
            "project_path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_name"] == "schemashield_demo"
    assert body["change_count"] == 1
    assert body["changes"] == [
        {
            "change_type": "column_renamed",
            "table": "customers",
            "old_name": "full_name",
            "new_name": "name",
        }
    ]
    assert body["findings"][0]["severity"] == "low"
    assert body["processing_time_ms"] >= 0


def test_analysis_endpoint_returns_structured_missing_baseline_error(
    monkeypatch,
    tmp_path,
):
    def missing_baseline(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(api, "load_baseline", missing_baseline)

    response = client.post(
        "/analysis/run",
        json={
            "database_url": DATABASE_URL,
            "schema_name": "schemashield_demo",
            "baseline_path": "missing.json",
            "project_path": str(tmp_path),
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "baseline_not_found",
        "message": "Capture a baseline before analysis",
    }


def test_request_validation_rejects_non_postgresql_urls():
    response = client.post(
        "/baseline/capture",
        json={
            "database_url": "sqlite:///local.db",
            "schema_name": "public",
            "baseline_path": "baseline.json",
        },
    )

    assert response.status_code == 422

