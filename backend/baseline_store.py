from __future__ import annotations

import json
from pathlib import Path

from backend.schema_extractor import extract_schema
from backend.schema_models import DatabaseSchema


def capture_baseline(
    database_url: str,
    path: str | Path,
    schema_name: str = "public",
) -> DatabaseSchema:
    """Extract a PostgreSQL schema and save it as the baseline."""
    schema = extract_schema(database_url, schema_name)
    save_baseline(schema, path)
    return schema


def save_baseline(schema: DatabaseSchema, path: str | Path) -> Path:
    """Save a baseline as readable JSON without leaving a partial file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(schema.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_baseline(path: str | Path) -> DatabaseSchema:
    """Load and validate a baseline JSON file into the schema model."""
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    return DatabaseSchema.from_dict(data)
