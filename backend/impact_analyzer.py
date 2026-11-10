from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.code_models import (
    AnalysisWarning,
    CodeAnalysisResult,
    SqlQueryReference,
)
from backend.schema_comparator import SchemaChange


@dataclass(frozen=True)
class AffectedCode:
    query_id: str
    source_file: str
    function_name: str | None
    statement_type: str

    @classmethod
    def from_query(cls, query: SqlQueryReference) -> AffectedCode:
        return cls(
            query_id=query.query_id,
            source_file=query.source_file,
            function_name=query.function_name,
            statement_type=query.statement_type,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "query_id": self.query_id,
            "source_file": self.source_file,
            "statement_type": self.statement_type,
        }
        if self.function_name is not None:
            data["function_name"] = self.function_name
        return data


@dataclass(frozen=True)
class ImpactFinding:
    database_object: str
    change: SchemaChange
    severity: str
    affected_code: tuple[AffectedCode, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_object": self.database_object,
            "change": self.change.to_dict(),
            "severity": self.severity,
            "affected_code": [item.to_dict() for item in self.affected_code],
        }


@dataclass(frozen=True)
class ImpactReport:
    findings: tuple[ImpactFinding, ...] = field(default_factory=tuple)
    warnings: tuple[AnalysisWarning, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [finding.to_dict() for finding in self.findings],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(frozen=True)
class DependencyMap:
    tables: dict[str, tuple[SqlQueryReference, ...]]
    columns: dict[str, tuple[SqlQueryReference, ...]]


def build_dependency_map(analysis: CodeAnalysisResult) -> DependencyMap:
    """Index parsed queries by the tables and resolved columns they use."""
    table_dependencies: dict[str, list[SqlQueryReference]] = {}
    column_dependencies: dict[str, list[SqlQueryReference]] = {}
    for query in analysis.queries:
        for table in query.tables:
            table_dependencies.setdefault(table.name, []).append(query)
        for column in query.columns:
            if column.table is not None:
                key = f"{column.table}.{column.column}"
                column_dependencies.setdefault(key, []).append(query)

    return DependencyMap(
        tables={
            key: _unique_queries(queries)
            for key, queries in sorted(table_dependencies.items())
        },
        columns={
            key: _unique_queries(queries)
            for key, queries in sorted(column_dependencies.items())
        },
    )


def analyze_impacts(
    changes: list[SchemaChange],
    analysis: CodeAnalysisResult,
) -> ImpactReport:
    """Connect detected drift to parsed code references and assign severity."""
    findings = []
    for change in changes:
        affected_queries = tuple(
            query for query in analysis.queries if _query_matches_change(query, change)
        )
        findings.append(
            ImpactFinding(
                database_object=_database_object(change),
                change=change,
                severity=_severity(change, bool(affected_queries)),
                affected_code=tuple(
                    AffectedCode.from_query(query)
                    for query in sorted(affected_queries, key=lambda item: item.query_id)
                ),
            )
        )
    return ImpactReport(findings=tuple(findings), warnings=analysis.warnings)


def _query_matches_change(query: SqlQueryReference, change: SchemaChange) -> bool:
    if change.change_type in {"table_removed", "table_renamed"}:
        target_table = change.table or change.old_name
        return any(table.name == target_table for table in query.tables)
    if change.change_type == "table_added":
        return False

    target_table = change.table
    target_column = change.old_name if change.change_type == "column_renamed" else change.column
    if change.change_type == "column_added" or target_table is None or target_column is None:
        return False

    query_uses_table = any(table.name == target_table for table in query.tables)
    return any(
        column.column == target_column
        and (
            column.table == target_table
            or (column.table is None and query_uses_table)
        )
        for column in query.columns
    )


def _database_object(change: SchemaChange) -> str:
    if change.change_type == "table_renamed":
        return change.old_name or ""
    if change.change_type in {"table_added", "table_removed"}:
        return change.table or ""
    column_name = change.old_name if change.change_type == "column_renamed" else change.column
    return f"{change.table}.{column_name}"


def _severity(change: SchemaChange, has_dependencies: bool) -> str:
    if not has_dependencies:
        return "low"
    if change.change_type in {
        "table_removed",
        "table_renamed",
        "column_removed",
        "column_renamed",
    }:
        return "high"
    if change.change_type == "column_modified":
        return "medium"
    return "low"


def _unique_queries(queries: list[SqlQueryReference]) -> tuple[SqlQueryReference, ...]:
    return tuple(
        sorted(
            {query.query_id: query for query in queries}.values(),
            key=lambda query: query.query_id,
        )
    )

