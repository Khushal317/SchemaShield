from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColumnSchema:
    name: str
    ordinal_position: int
    data_type: str
    character_maximum_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    is_nullable: bool = True
    column_default: str | None = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_unique: bool = False
    referenced_table: str | None = None
    referenced_column: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnSchema:
        return cls(**data)

    def structural_signature(self) -> tuple[Any, ...]:
        """Return properties used for conservative rename matching."""
        return (
            self.data_type,
            self.character_maximum_length,
            self.numeric_precision,
            self.numeric_scale,
            self.is_nullable,
            self.column_default,
            self.is_primary_key,
            self.is_foreign_key,
            self.is_unique,
            self.referenced_table,
            self.referenced_column,
        )


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: dict[str, ColumnSchema] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": {
                name: column.to_dict()
                for name, column in sorted(self.columns.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableSchema:
        return cls(
            name=data["name"],
            columns={
                name: ColumnSchema.from_dict(column)
                for name, column in data.get("columns", {}).items()
            },
        )


@dataclass(frozen=True)
class DatabaseSchema:
    schema_name: str
    tables: dict[str, TableSchema] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "tables": {
                name: table.to_dict()
                for name, table in sorted(self.tables.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseSchema:
        return cls(
            schema_name=data["schema_name"],
            tables={
                name: TableSchema.from_dict(table)
                for name, table in data.get("tables", {}).items()
            },
        )

