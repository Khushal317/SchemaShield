from pathlib import Path

from backend.code_analyzer import scan_project


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROJECT = ROOT / "samples" / "python_project"


def test_sample_project_queries_are_found_without_execution():
    result = scan_project(SAMPLE_PROJECT)

    assert len(result.queries) == 7
    assert result.warnings == ()
    assert {query.function_name for query in result.queries} == {
        None,
        "get_customer_profile",
        "create_customer",
        "list_customer_orders",
        "mark_order_complete",
        "list_available_products",
    }
    assert {query.source_file for query in result.queries} == {
        "customer_repository.py",
        "order_repository.py",
        "product_repository.py",
        "report_queries.sql",
    }


def test_insert_target_columns_are_detected():
    result = scan_project(SAMPLE_PROJECT)
    create_customer = next(
        query for query in result.queries if query.function_name == "create_customer"
    )

    assert {column.qualified_name for column in create_customer.columns} >= {
        "schemashield_demo.customers.full_name",
        "schemashield_demo.customers.email",
        "schemashield_demo.customers.phone",
    }


def test_qualified_join_columns_resolve_to_the_correct_tables():
    result = scan_project(SAMPLE_PROJECT)
    report_query = next(
        query for query in result.queries if query.query_id == "report_queries.sql#1"
    )

    assert {column.qualified_name for column in report_query.columns} >= {
        "schemashield_demo.customers.full_name",
        "schemashield_demo.customers.email",
        "schemashield_demo.orders.order_total",
        "schemashield_demo.orders.status",
    }


def test_invalid_python_and_sql_are_reported_as_warnings(tmp_path):
    (tmp_path / "broken_python.py").write_text("def broken(:\n")
    (tmp_path / "broken_query.py").write_text('QUERY = "SELECT * FROM"\n')

    result = scan_project(tmp_path)

    assert result.queries == ()
    assert {warning.source_file for warning in result.warnings} == {
        "broken_python.py",
        "broken_query.py",
    }


def test_dynamic_sql_is_reported_instead_of_guessed(tmp_path):
    (tmp_path / "dynamic_query.py").write_text(
        'def load_table(table_name):\n'
        '    query = f"SELECT * FROM {table_name}"\n'
        '    return query\n'
    )

    result = scan_project(tmp_path)

    assert result.queries == ()
    assert len(result.warnings) == 1
    assert result.warnings[0].function_name == "load_table"
    assert "Dynamic SQL" in result.warnings[0].message


def test_non_directory_project_path_is_rejected(tmp_path):
    file_path = tmp_path / "project.py"
    file_path.write_text("VALUE = 1\n")

    try:
        scan_project(file_path)
    except ValueError as error:
        assert "not a directory" in str(error)
    else:
        raise AssertionError("scan_project must reject a file path")
