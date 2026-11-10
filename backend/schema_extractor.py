from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from backend.schema_models import ColumnSchema, DatabaseSchema, TableSchema


COLUMN_QUERY = text(
    """
    SELECT
        c.table_name,
        c.column_name,
        c.ordinal_position,
        c.data_type,
        c.character_maximum_length,
        c.numeric_precision,
        c.numeric_scale,
        c.is_nullable,
        c.column_default
    FROM information_schema.columns AS c
    JOIN information_schema.tables AS t
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE c.table_schema = :schema_name
      AND t.table_type = 'BASE TABLE'
    ORDER BY c.table_name, c.ordinal_position
    """
)

KEY_QUERY = text(
    """
    SELECT
        tc.table_name,
        kcu.column_name,
        tc.constraint_type,
        ccu.table_name AS referenced_table,
        ccu.column_name AS referenced_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON kcu.constraint_catalog = tc.constraint_catalog
     AND kcu.constraint_schema = tc.constraint_schema
     AND kcu.constraint_name = tc.constraint_name
    LEFT JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_catalog = tc.constraint_catalog
     AND ccu.constraint_schema = tc.constraint_schema
     AND ccu.constraint_name = tc.constraint_name
     AND tc.constraint_type = 'FOREIGN KEY'
    WHERE tc.table_schema = :schema_name
      AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
    ORDER BY tc.table_name, kcu.column_name, tc.constraint_type
    """
)


def extract_schema(database_url: str, schema_name: str = "public") -> DatabaseSchema:
    """Connect to PostgreSQL and return a normalized schema representation."""
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            return extract_schema_from_connection(connection, schema_name)
    finally:
        engine.dispose()


def extract_schema_from_connection(
    connection: Connection,
    schema_name: str = "public",
) -> DatabaseSchema:
    """Extract base tables, columns, and key metadata from PostgreSQL."""
    column_rows = connection.execute(
        COLUMN_QUERY,
        {"schema_name": schema_name},
    ).mappings()
    key_rows = connection.execute(
        KEY_QUERY,
        {"schema_name": schema_name},
    ).mappings()

    key_metadata: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "is_primary_key": False,
            "is_foreign_key": False,
            "is_unique": False,
            "referenced_table": None,
            "referenced_column": None,
        }
    )

    for row in key_rows:
        metadata = key_metadata[(row["table_name"], row["column_name"])]
        constraint_type = row["constraint_type"]
        if constraint_type == "PRIMARY KEY":
            metadata["is_primary_key"] = True
        elif constraint_type == "UNIQUE":
            metadata["is_unique"] = True
        elif constraint_type == "FOREIGN KEY":
            metadata["is_foreign_key"] = True
            metadata["referenced_table"] = row["referenced_table"]
            metadata["referenced_column"] = row["referenced_column"]

    table_columns: dict[str, dict[str, ColumnSchema]] = defaultdict(dict)
    for row in column_rows:
        keys = key_metadata[(row["table_name"], row["column_name"])]
        column = ColumnSchema(
            name=row["column_name"],
            ordinal_position=row["ordinal_position"],
            data_type=row["data_type"].lower(),
            character_maximum_length=row["character_maximum_length"],
            numeric_precision=row["numeric_precision"],
            numeric_scale=row["numeric_scale"],
            is_nullable=row["is_nullable"] == "YES",
            column_default=row["column_default"],
            **keys,
        )
        table_columns[row["table_name"]][column.name] = column

    return DatabaseSchema(
        schema_name=schema_name,
        tables={
            table_name: TableSchema(name=table_name, columns=columns)
            for table_name, columns in sorted(table_columns.items())
        },
    )

