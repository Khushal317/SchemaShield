from __future__ import annotations

import sqlglot
from sqlglot import exp

from backend.code_models import ColumnReference, SqlQueryReference, TableReference


def parse_sql_query(
    sql: str,
    *,
    query_id: str,
    source_file: str,
    function_name: str | None,
) -> SqlQueryReference:
    """Parse one PostgreSQL statement and return its database references."""
    expression = sqlglot.parse_one(sql, read="postgres")
    return query_reference_from_expression(
        expression,
        sql=sql,
        query_id=query_id,
        source_file=source_file,
        function_name=function_name,
    )


def query_reference_from_expression(
    expression: exp.Expression,
    *,
    sql: str,
    query_id: str,
    source_file: str,
    function_name: str | None,
) -> SqlQueryReference:
    tables_by_key: dict[tuple[str | None, str], TableReference] = {}
    aliases: dict[str, TableReference] = {}
    for node in expression.find_all(exp.Table):
        reference = TableReference(name=node.name, schema=node.db or None)
        tables_by_key[(reference.schema, reference.name)] = reference
        aliases[node.name] = reference
        if node.alias:
            aliases[node.alias] = reference

    tables = tuple(sorted(tables_by_key.values()))
    columns: set[ColumnReference] = set()
    for node in expression.find_all(exp.Column):
        columns.add(_resolve_column(node.name, node.table or None, aliases, tables))

    if isinstance(expression, exp.Insert) and isinstance(expression.this, exp.Schema):
        target = expression.this.this
        if isinstance(target, exp.Table):
            target_reference = TableReference(name=target.name, schema=target.db or None)
            for identifier in expression.this.expressions:
                if isinstance(identifier, exp.Identifier):
                    columns.add(
                        ColumnReference(
                            column=identifier.name,
                            table=target_reference.name,
                            schema=target_reference.schema,
                        )
                    )

    return SqlQueryReference(
        query_id=query_id,
        source_file=source_file,
        function_name=function_name,
        statement_type=expression.key.upper(),
        sql=sql.strip(),
        tables=tables,
        columns=tuple(sorted(columns)),
    )


def _resolve_column(
    column_name: str,
    qualifier: str | None,
    aliases: dict[str, TableReference],
    tables: tuple[TableReference, ...],
) -> ColumnReference:
    if qualifier and qualifier in aliases:
        table = aliases[qualifier]
        return ColumnReference(
            column=column_name,
            table=table.name,
            schema=table.schema,
        )
    if qualifier:
        return ColumnReference(column=column_name, table=qualifier)
    if len(tables) == 1:
        table = tables[0]
        return ColumnReference(
            column=column_name,
            table=table.name,
            schema=table.schema,
        )
    return ColumnReference(column=column_name)

