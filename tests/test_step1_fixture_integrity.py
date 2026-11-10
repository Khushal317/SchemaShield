import ast
import json
from pathlib import Path

import sqlglot


ROOT = Path(__file__).resolve().parents[1]
DATABASE_FIXTURES = ROOT / "samples" / "database"
PYTHON_FIXTURES = ROOT / "samples" / "python_project"


def test_ground_truth_covers_required_schema_changes():
    data = json.loads((DATABASE_FIXTURES / "expected_changes.json").read_text())
    change_types = {change["change_type"] for change in data["changes"]}

    assert change_types == {
        "table_added",
        "table_removed",
        "column_added",
        "column_removed",
        "column_renamed",
        "column_modified",
    }


def test_expected_impact_functions_exist_in_sample_python_project():
    expected = json.loads(
        (DATABASE_FIXTURES / "expected_impacts.json").read_text()
    )
    expected_functions = {
        function_name
        for impact in expected["impacts"]
        for function_name in impact["functions"]
    }
    expected_source_files = {
        source_file
        for impact in expected["impacts"]
        for source_file in impact["source_files"]
    }

    discovered_functions = set()
    for source_file in PYTHON_FIXTURES.glob("*.py"):
        tree = ast.parse(source_file.read_text(), filename=str(source_file))
        discovered_functions.update(
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        )

    assert expected_functions <= discovered_functions
    assert expected_source_files <= {
        path.name for path in PYTHON_FIXTURES.iterdir() if path.is_file()
    }


def test_sql_fixtures_use_the_controlled_schema():
    baseline = (DATABASE_FIXTURES / "baseline_schema.sql").read_text()
    modified = (DATABASE_FIXTURES / "modified_schema.sql").read_text()

    assert "CREATE SCHEMA schemashield_demo" in baseline
    assert "CREATE SCHEMA schemashield_demo" in modified
    assert "CREATE TABLE products" in baseline
    assert "CREATE TABLE products" not in modified
    assert "CREATE TABLE audit_logs" not in baseline
    assert "CREATE TABLE audit_logs" in modified

    assert len(sqlglot.parse(baseline, read="postgres")) == 6
    assert len(sqlglot.parse(modified, read="postgres")) == 6
