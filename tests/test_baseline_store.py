from backend import baseline_store
from backend.baseline_store import capture_baseline, load_baseline, save_baseline
from backend.schema_models import ColumnSchema, DatabaseSchema, TableSchema


def test_baseline_json_round_trip(tmp_path):
    schema = DatabaseSchema(
        schema_name="schemashield_demo",
        tables={
            "customers": TableSchema(
                name="customers",
                columns={
                    "id": ColumnSchema(
                        name="id",
                        ordinal_position=1,
                        data_type="integer",
                        numeric_precision=32,
                        numeric_scale=0,
                        is_nullable=False,
                        is_primary_key=True,
                    )
                },
            )
        },
    )
    path = tmp_path / "nested" / "baseline.json"

    saved_path = save_baseline(schema, path)

    assert saved_path == path
    assert load_baseline(path) == schema
    assert not path.with_suffix(".json.tmp").exists()


def test_capture_baseline_extracts_and_saves(monkeypatch, tmp_path):
    schema = DatabaseSchema(schema_name="schemashield_demo")
    monkeypatch.setattr(
        baseline_store,
        "extract_schema",
        lambda database_url, schema_name: schema,
    )
    path = tmp_path / "baseline.json"

    result = capture_baseline(
        "postgresql+psycopg://local/test",
        path,
        "schemashield_demo",
    )

    assert result == schema
    assert load_baseline(path) == schema
