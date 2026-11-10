from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from backend.schema_models import ColumnSchema, DatabaseSchema, TableSchema


@dataclass(frozen=True)
class SchemaChange:
    change_type: str
    table: str | None = None
    column: str | None = None
    old_name: str | None = None
    new_name: str | None = None
    property: str | None = None
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        data = {"change_type": self.change_type}
        for name in ("table", "column", "old_name", "new_name"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        if self.property is not None:
            data["property"] = self.property
            data["old_value"] = self.old_value
            data["new_value"] = self.new_value
        return data


def compare_schemas(
    baseline: DatabaseSchema,
    current: DatabaseSchema,
) -> list[SchemaChange]:
    """Return deterministic drift records between two normalized schemas."""
    baseline_tables = set(baseline.tables)
    current_tables = set(current.tables)
    removed_tables = baseline_tables - current_tables
    added_tables = current_tables - baseline_tables

    table_renames = _match_table_renames(
        {name: baseline.tables[name] for name in removed_tables},
        {name: current.tables[name] for name in added_tables},
    )
    renamed_old = set(table_renames)
    renamed_new = set(table_renames.values())

    changes: list[SchemaChange] = []
    for old_name, new_name in sorted(table_renames.items()):
        changes.append(
            SchemaChange(
                change_type="table_renamed",
                old_name=old_name,
                new_name=new_name,
            )
        )
        changes.extend(
            _compare_table_columns(
                baseline.tables[old_name],
                current.tables[new_name],
                output_table_name=new_name,
            )
        )

    for table_name in sorted(removed_tables - renamed_old):
        changes.append(SchemaChange(change_type="table_removed", table=table_name))
    for table_name in sorted(added_tables - renamed_new):
        changes.append(SchemaChange(change_type="table_added", table=table_name))

    for table_name in sorted(baseline_tables & current_tables):
        changes.extend(
            _compare_table_columns(
                baseline.tables[table_name],
                current.tables[table_name],
                output_table_name=table_name,
            )
        )

    return sorted(changes, key=_change_sort_key)


def _compare_table_columns(
    baseline: TableSchema,
    current: TableSchema,
    output_table_name: str,
) -> list[SchemaChange]:
    baseline_columns = set(baseline.columns)
    current_columns = set(current.columns)
    removed = baseline_columns - current_columns
    added = current_columns - baseline_columns
    renames = _match_column_renames(
        {name: baseline.columns[name] for name in removed},
        {name: current.columns[name] for name in added},
    )

    changes: list[SchemaChange] = []
    for old_name, new_name in sorted(renames.items()):
        changes.append(
            SchemaChange(
                change_type="column_renamed",
                table=output_table_name,
                old_name=old_name,
                new_name=new_name,
            )
        )

    for column_name in sorted(removed - set(renames)):
        changes.append(
            SchemaChange(
                change_type="column_removed",
                table=output_table_name,
                column=column_name,
            )
        )
    for column_name in sorted(added - set(renames.values())):
        changes.append(
            SchemaChange(
                change_type="column_added",
                table=output_table_name,
                column=column_name,
            )
        )

    comparable_columns = {
        name: name for name in baseline_columns & current_columns
    }
    comparable_columns.update(renames)
    for old_name, new_name in sorted(comparable_columns.items()):
        changes.extend(
            _compare_column_properties(
                baseline.columns[old_name],
                current.columns[new_name],
                output_table_name,
                new_name,
            )
        )
    return changes


def _compare_column_properties(
    baseline: ColumnSchema,
    current: ColumnSchema,
    table_name: str,
    column_name: str,
) -> list[SchemaChange]:
    properties = (
        "data_type",
        "character_maximum_length",
        "numeric_precision",
        "numeric_scale",
        "is_nullable",
        "column_default",
        "is_primary_key",
        "is_foreign_key",
        "is_unique",
        "referenced_table",
        "referenced_column",
    )
    changes = []
    for property_name in properties:
        old_value = getattr(baseline, property_name)
        new_value = getattr(current, property_name)
        if old_value != new_value:
            changes.append(
                SchemaChange(
                    change_type="column_modified",
                    table=table_name,
                    column=column_name,
                    property=property_name,
                    old_value=old_value,
                    new_value=new_value,
                )
            )
    return changes


def _match_column_renames(
    removed: dict[str, ColumnSchema],
    added: dict[str, ColumnSchema],
) -> dict[str, str]:
    removed_by_signature: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    added_by_signature: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for name, column in removed.items():
        removed_by_signature[column.structural_signature()].append(name)
    for name, column in added.items():
        added_by_signature[column.structural_signature()].append(name)

    matches = {}
    for signature in removed_by_signature.keys() & added_by_signature.keys():
        old_names = removed_by_signature[signature]
        new_names = added_by_signature[signature]
        if len(old_names) == 1 and len(new_names) == 1:
            matches[old_names[0]] = new_names[0]
    return matches


def _match_table_renames(
    removed: dict[str, TableSchema],
    added: dict[str, TableSchema],
) -> dict[str, str]:
    scores = {
        (old_name, new_name): _table_similarity(old_table, new_table)
        for old_name, old_table in removed.items()
        for new_name, new_table in added.items()
    }
    matches = {}
    for old_name in sorted(removed):
        candidates = [
            (score, new_name)
            for (candidate_old, new_name), score in scores.items()
            if candidate_old == old_name and score >= 0.8
        ]
        if not candidates:
            continue
        best_score = max(score for score, _ in candidates)
        best_new = [name for score, name in candidates if score == best_score]
        if len(best_new) != 1:
            continue

        new_name = best_new[0]
        reverse = [
            (score, candidate_old)
            for (candidate_old, candidate_new), score in scores.items()
            if candidate_new == new_name and score >= 0.8
        ]
        reverse_best = max(score for score, _ in reverse)
        reverse_old = [name for score, name in reverse if score == reverse_best]
        if len(reverse_old) == 1 and reverse_old[0] == old_name:
            matches[old_name] = new_name
    return matches


def _table_similarity(baseline: TableSchema, current: TableSchema) -> float:
    baseline_signatures = Counter(
        column.structural_signature() for column in baseline.columns.values()
    )
    current_signatures = Counter(
        column.structural_signature() for column in current.columns.values()
    )
    largest_size = max(sum(baseline_signatures.values()), sum(current_signatures.values()))
    if largest_size == 0:
        return 1.0
    shared = sum((baseline_signatures & current_signatures).values())
    return shared / largest_size


def _change_sort_key(change: SchemaChange) -> tuple[str, ...]:
    return (
        change.change_type,
        change.table or "",
        change.column or "",
        change.old_name or "",
        change.new_name or "",
        change.property or "",
    )

