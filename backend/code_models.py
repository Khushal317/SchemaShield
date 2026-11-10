from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, order=True)
class TableReference:
    name: str
    schema: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.name}" if self.schema else self.name


@dataclass(frozen=True, order=True)
class ColumnReference:
    column: str
    table: str | None = None
    schema: str | None = None

    @property
    def qualified_name(self) -> str:
        table_name = f"{self.table}." if self.table else ""
        schema_name = f"{self.schema}." if self.schema else ""
        return f"{schema_name}{table_name}{self.column}"


@dataclass(frozen=True)
class SqlQueryReference:
    query_id: str
    source_file: str
    function_name: str | None
    statement_type: str
    sql: str
    tables: tuple[TableReference, ...] = field(default_factory=tuple)
    columns: tuple[ColumnReference, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "source_file": self.source_file,
            "function_name": self.function_name,
            "statement_type": self.statement_type,
            "sql": self.sql,
            "tables": [table.qualified_name for table in self.tables],
            "columns": [column.qualified_name for column in self.columns],
        }


@dataclass(frozen=True)
class AnalysisWarning:
    source_file: str
    message: str
    function_name: str | None = None
    query_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "source_file": self.source_file,
            "message": self.message,
        }
        if self.function_name is not None:
            data["function_name"] = self.function_name
        if self.query_id is not None:
            data["query_id"] = self.query_id
        return data


@dataclass(frozen=True)
class CodeAnalysisResult:
    queries: tuple[SqlQueryReference, ...] = field(default_factory=tuple)
    warnings: tuple[AnalysisWarning, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "queries": [query.to_dict() for query in self.queries],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

