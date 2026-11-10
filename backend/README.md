# Backend

The completed backend foundation contains:

- `schema_models.py`: normalized database, table, and column models.
- `schema_extractor.py`: read-only PostgreSQL `information_schema` extraction.
- `baseline_store.py`: baseline capture plus JSON save and load operations.
- `schema_comparator.py`: table and column drift detection.
- `code_analyzer.py`: safe Python AST and standalone SQL discovery.
- `sql_analyzer.py`: PostgreSQL SQL parsing and table/column extraction.
- `impact_analyzer.py`: dependency mapping, impact matching, and severity.
- `api_models.py`: validated FastAPI request and response models.
- `api.py`: health, baseline-capture, and drift-analysis endpoints.
- `evaluation.py`: detection metrics and impact-ground-truth verification.

Run the backend from the project root:

```bash
.venv/bin/python -m uvicorn backend.api:app --reload
```
