from backend.schema_extractor import extract_schema_from_connection


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self.rows


class FakeConnection:
    def __init__(self, column_rows, key_rows):
        self.results = [FakeResult(column_rows), FakeResult(key_rows)]
        self.calls = []

    def execute(self, query, parameters):
        self.calls.append((str(query), parameters))
        return self.results.pop(0)


def test_extract_schema_normalizes_columns_and_keys():
    columns = [
        {
            "table_name": "customers",
            "column_name": "id",
            "ordinal_position": 1,
            "data_type": "INTEGER",
            "character_maximum_length": None,
            "numeric_precision": 32,
            "numeric_scale": 0,
            "is_nullable": "NO",
            "column_default": None,
        },
        {
            "table_name": "orders",
            "column_name": "customer_id",
            "ordinal_position": 2,
            "data_type": "INTEGER",
            "character_maximum_length": None,
            "numeric_precision": 32,
            "numeric_scale": 0,
            "is_nullable": "NO",
            "column_default": None,
        },
    ]
    keys = [
        {
            "table_name": "customers",
            "column_name": "id",
            "constraint_type": "PRIMARY KEY",
            "referenced_table": None,
            "referenced_column": None,
        },
        {
            "table_name": "orders",
            "column_name": "customer_id",
            "constraint_type": "FOREIGN KEY",
            "referenced_table": "customers",
            "referenced_column": "id",
        },
    ]
    connection = FakeConnection(columns, keys)

    schema = extract_schema_from_connection(connection, "schemashield_demo")

    assert schema.schema_name == "schemashield_demo"
    customer_id = schema.tables["customers"].columns["id"]
    assert customer_id.data_type == "integer"
    assert customer_id.is_nullable is False
    assert customer_id.is_primary_key is True

    order_customer_id = schema.tables["orders"].columns["customer_id"]
    assert order_customer_id.is_foreign_key is True
    assert order_customer_id.referenced_table == "customers"
    assert order_customer_id.referenced_column == "id"
    assert len(connection.calls) == 2
    assert all(
        parameters == {"schema_name": "schemashield_demo"}
        for _, parameters in connection.calls
    )

