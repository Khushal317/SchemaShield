import json
from pathlib import Path

from backend.schema_comparator import compare_schemas
from backend.schema_models import ColumnSchema, DatabaseSchema, TableSchema


ROOT = Path(__file__).resolve().parents[1]


def column(
    name,
    position,
    data_type,
    *,
    length=None,
    precision=None,
    scale=None,
    nullable=True,
    default=None,
    primary_key=False,
    foreign_key=False,
    referenced_table=None,
    referenced_column=None,
):
    return ColumnSchema(
        name=name,
        ordinal_position=position,
        data_type=data_type,
        character_maximum_length=length,
        numeric_precision=precision,
        numeric_scale=scale,
        is_nullable=nullable,
        column_default=default,
        is_primary_key=primary_key,
        is_foreign_key=foreign_key,
        referenced_table=referenced_table,
        referenced_column=referenced_column,
    )


def table(name, *columns):
    return TableSchema(name=name, columns={item.name: item for item in columns})


def controlled_schemas():
    baseline = DatabaseSchema(
        schema_name="schemashield_demo",
        tables={
            "customers": table(
                "customers",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column("full_name", 2, "character varying", length=100, nullable=False),
                column("email", 3, "character varying", length=150, nullable=False),
                column("phone", 4, "character varying", length=20),
                column("created_at", 5, "timestamp with time zone", nullable=False, default="CURRENT_TIMESTAMP"),
            ),
            "orders": table(
                "orders",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column(
                    "customer_id",
                    2,
                    "integer",
                    precision=32,
                    scale=0,
                    nullable=False,
                    foreign_key=True,
                    referenced_table="customers",
                    referenced_column="id",
                ),
                column("order_total", 3, "numeric", precision=10, scale=2, nullable=False),
                column("status", 4, "character varying", length=20, nullable=False, default="pending"),
                column("created_at", 5, "timestamp with time zone", nullable=False, default="CURRENT_TIMESTAMP"),
            ),
            "products": table(
                "products",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column("name", 2, "character varying", length=120, nullable=False),
                column("price", 3, "numeric", precision=10, scale=2, nullable=False),
                column("stock_count", 4, "integer", precision=32, scale=0, nullable=False, default="0"),
            ),
        },
    )
    current = DatabaseSchema(
        schema_name="schemashield_demo",
        tables={
            "customers": table(
                "customers",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column("name", 2, "character varying", length=100, nullable=False),
                column("email", 3, "character varying", length=200, nullable=False),
                column("is_active", 4, "boolean", nullable=False, default="true"),
                column("created_at", 5, "timestamp with time zone", nullable=False, default="CURRENT_TIMESTAMP"),
            ),
            "orders": table(
                "orders",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column(
                    "customer_id",
                    2,
                    "integer",
                    precision=32,
                    scale=0,
                    nullable=False,
                    foreign_key=True,
                    referenced_table="customers",
                    referenced_column="id",
                ),
                column("total_amount", 3, "numeric", precision=10, scale=2, nullable=False),
                column("status", 4, "character varying", length=30, nullable=False, default="pending"),
                column("created_at", 5, "timestamp with time zone", nullable=False, default="CURRENT_TIMESTAMP"),
                column("updated_at", 6, "timestamp with time zone"),
            ),
            "audit_logs": table(
                "audit_logs",
                column("id", 1, "integer", precision=32, scale=0, nullable=False, primary_key=True),
                column("action", 2, "character varying", length=100, nullable=False),
                column("created_at", 3, "timestamp with time zone", nullable=False, default="CURRENT_TIMESTAMP"),
            ),
        },
    )
    return baseline, current


def test_comparison_matches_controlled_ground_truth():
    baseline, current = controlled_schemas()
    actual = {json.dumps(change.to_dict(), sort_keys=True) for change in compare_schemas(baseline, current)}
    expected_data = json.loads(
        (ROOT / "samples" / "database" / "expected_changes.json").read_text()
    )
    expected = {json.dumps(change, sort_keys=True) for change in expected_data["changes"]}

    assert actual == expected


def test_unchanged_schema_has_no_drift():
    baseline, _ = controlled_schemas()

    assert compare_schemas(baseline, baseline) == []


def test_unambiguous_table_rename_is_detected():
    old_table = table(
        "old_customers",
        column("id", 1, "integer", nullable=False, primary_key=True),
        column("email", 2, "character varying", length=150, nullable=False),
    )
    new_table = table(
        "customers",
        column("id", 1, "integer", nullable=False, primary_key=True),
        column("email", 2, "character varying", length=150, nullable=False),
    )
    baseline = DatabaseSchema("schemashield_demo", {old_table.name: old_table})
    current = DatabaseSchema("schemashield_demo", {new_table.name: new_table})

    assert [change.to_dict() for change in compare_schemas(baseline, current)] == [
        {
            "change_type": "table_renamed",
            "old_name": "old_customers",
            "new_name": "customers",
        }
    ]


def test_ambiguous_column_changes_are_not_guessed_as_renames():
    baseline = DatabaseSchema(
        "schemashield_demo",
        {
            "items": table(
                "items",
                column("old_a", 1, "integer"),
                column("old_b", 2, "integer"),
            )
        },
    )
    current = DatabaseSchema(
        "schemashield_demo",
        {
            "items": table(
                "items",
                column("new_a", 1, "integer"),
                column("new_b", 2, "integer"),
            )
        },
    )

    change_types = [change.change_type for change in compare_schemas(baseline, current)]

    assert change_types.count("column_removed") == 2
    assert change_types.count("column_added") == 2
    assert "column_renamed" not in change_types
