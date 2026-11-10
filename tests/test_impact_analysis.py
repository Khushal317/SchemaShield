import json
from pathlib import Path

from backend.code_analyzer import scan_project
from backend.impact_analyzer import analyze_impacts, build_dependency_map
from backend.schema_comparator import SchemaChange


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROJECT = ROOT / "samples" / "python_project"


def controlled_changes():
    return [
        SchemaChange(change_type="table_added", table="audit_logs"),
        SchemaChange(change_type="table_removed", table="products"),
        SchemaChange(
            change_type="column_renamed",
            table="customers",
            old_name="full_name",
            new_name="name",
        ),
        SchemaChange(
            change_type="column_removed",
            table="customers",
            column="phone",
        ),
        SchemaChange(
            change_type="column_modified",
            table="customers",
            column="email",
            property="character_maximum_length",
            old_value=150,
            new_value=200,
        ),
        SchemaChange(
            change_type="column_added",
            table="customers",
            column="is_active",
        ),
        SchemaChange(
            change_type="column_renamed",
            table="orders",
            old_name="order_total",
            new_name="total_amount",
        ),
        SchemaChange(
            change_type="column_modified",
            table="orders",
            column="status",
            property="character_maximum_length",
            old_value=20,
            new_value=30,
        ),
        SchemaChange(
            change_type="column_added",
            table="orders",
            column="updated_at",
        ),
    ]


def test_dependency_map_indexes_tables_and_columns():
    dependencies = build_dependency_map(scan_project(SAMPLE_PROJECT))

    assert {query.source_file for query in dependencies.tables["products"]} == {
        "product_repository.py",
        "report_queries.sql",
    }
    assert {
        query.function_name for query in dependencies.columns["customers.phone"]
    } == {"get_customer_profile", "create_customer"}


def test_impacts_match_the_controlled_ground_truth():
    report = analyze_impacts(controlled_changes(), scan_project(SAMPLE_PROJECT))
    expected = json.loads(
        (ROOT / "samples" / "database" / "expected_impacts.json").read_text()
    )["impacts"]
    findings = {finding.database_object: finding for finding in report.findings}

    for expected_impact in expected:
        finding = findings[expected_impact["database_object"]]
        assert finding.change.change_type == expected_impact["change_type"]
        assert {item.source_file for item in finding.affected_code} == set(
            expected_impact["source_files"]
        )
        assert {
            item.function_name
            for item in finding.affected_code
            if item.function_name is not None
        } == set(expected_impact["functions"])


def test_severity_is_based_on_change_type_and_actual_dependencies():
    report = analyze_impacts(controlled_changes(), scan_project(SAMPLE_PROJECT))
    findings = {finding.database_object: finding for finding in report.findings}

    assert findings["products"].severity == "high"
    assert findings["customers.full_name"].severity == "high"
    assert findings["customers.email"].severity == "medium"
    assert findings["orders.status"].severity == "medium"
    assert findings["audit_logs"].severity == "low"
    assert findings["customers.is_active"].severity == "low"
    assert findings["audit_logs"].affected_code == ()

