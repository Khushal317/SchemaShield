# SchemaShield

SchemaShield is an application that detects PostgreSQL schema drift and identifies Python files, functions, and SQL queries that may be affected by database changes. It compares a saved baseline schema with the current database, scans the application code, assigns severity levels, and produces a downloadable drift report.

## What the demo does

The repository contains everything needed for the controlled demonstration:

- `samples/database/baseline_schema.sql` creates the original PostgreSQL schema.
- `samples/database/modified_schema.sql` creates the changed schema.
- `samples/python_project/` contains Python and SQL code that uses the original schema.
- `samples/database/expected_changes.json` contains the expected schema changes.
- `samples/database/expected_impacts.json` contains the expected code impacts.
- `evaluation_report.json` contains the recorded evaluation results.

The SQL files are the demo database stored in Git. A running PostgreSQL database or Docker container should not be committed. Every teammate recreates the same database locally by loading these SQL files into the PostgreSQL Docker container.

## Requirements

Install these before starting:

- Git
- Python 3.11 or newer
- Docker Desktop

PostgreSQL does not need to be installed separately because the project uses PostgreSQL 16 through Docker. No GPU or HPC resources are required.

## 1. Download or update the project

For the first setup, clone the repository and enter its folder:

```bash
git clone <repository-url>
cd CollagePro
```

Replace `<repository-url>` with the GitHub repository URL.

If the project is already cloned, enter the project and download the latest changes:

```bash
cd CollagePro
git pull
```

Run all remaining commands from the `CollagePro` project folder.

## 2. Create the Python environment

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

When the environment is active, the terminal prompt normally contains `(.venv)`.

### Windows activation

In Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## 3. Verify the project

Run the automated tests:

```bash
python -m pytest -q
```

Expected result:

```text
30 passed
```

A deprecation warning from the test libraries does not stop the project and can currently be ignored.

## 4. Start the demo PostgreSQL database

Open Docker Desktop and wait until Docker is running. Then create the PostgreSQL container:

```bash
docker run \
  --name schemashield-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=schemashield_demo \
  -p 55432:5432 \
  -v "$PWD:/project:ro" \
  -d postgres:16-alpine
```

The first run downloads PostgreSQL and may take a few minutes. Successful output is a long Docker container ID.

Check that PostgreSQL is ready:

```bash
docker exec schemashield-db pg_isready -U postgres -d schemashield_demo
```

Expected result:

```text
/var/run/postgresql:5432 - accepting connections
```

If Docker reports that the container name already exists, do not create another container. Start the existing container:

```bash
docker start schemashield-db
```

Then run the readiness command again.

## 5. Load the original database schema

Load the baseline schema before capturing the baseline in SchemaShield:

```bash
docker exec schemashield-db \
  psql -v ON_ERROR_STOP=1 \
  -U postgres \
  -d schemashield_demo \
  -f /project/samples/database/baseline_schema.sql
```

Expected output contains:

```text
DROP SCHEMA
CREATE SCHEMA
SET
CREATE TABLE
CREATE TABLE
CREATE TABLE
```

A notice saying that the schema does not exist is normal on the first run. The baseline contains the `customers`, `orders`, and `products` tables.

## 6. Start the FastAPI backend

Keep the database running. In Terminal 1, from the project folder, run:

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload
```

Expected output includes:

```text
Application startup complete
Uvicorn running on http://127.0.0.1:8000
```

Verify the backend by opening `http://127.0.0.1:8000/health` in a browser. The response should be:

```json
{"status":"ok"}
```

Keep this terminal running.

## 7. Start the Streamlit dashboard

Open Terminal 2, enter the project folder, and run:

```bash
source .venv/bin/activate
python -m streamlit run frontend/app.py
```

Expected output includes:

```text
Local URL: http://localhost:8501
```

Open `http://localhost:8501` if the dashboard does not open automatically. Keep this terminal running.

## 8. Capture the baseline

Enter these values in the dashboard:

```text
FastAPI URL:
http://localhost:8000

PostgreSQL URL:
postgresql+psycopg://postgres:postgres@localhost:55432/schemashield_demo

Schema name:
schemashield_demo

Python project folder:
samples/python_project

Baseline JSON file:
baseline.json
```

Click **Capture baseline**.

Expected message:

```text
Saved 3 tables to .../CollagePro/baseline.json
```

SchemaShield has now saved the original database structure. Do not capture the baseline again after loading the modified schema.

## 9. Apply the controlled database changes

Open Terminal 3 and run this command from the project folder:

```bash
docker exec schemashield-db \
  psql -v ON_ERROR_STOP=1 \
  -U postgres \
  -d schemashield_demo \
  -f /project/samples/database/modified_schema.sql
```

Expected output again contains `DROP SCHEMA`, `CREATE SCHEMA`, `SET`, and three `CREATE TABLE` lines. A `drop cascades to 3 other objects` notice is normal.

The modified schema intentionally makes these nine changes:

1. Adds the `audit_logs` table.
2. Removes the `products` table.
3. Renames `customers.full_name` to `customers.name`.
4. Removes `customers.phone`.
5. Changes the maximum length of `customers.email` from 150 to 200.
6. Adds `customers.is_active`.
7. Renames `orders.order_total` to `orders.total_amount`.
8. Changes the maximum length of `orders.status` from 20 to 30.
9. Adds `orders.updated_at`.

## 10. Run drift detection

Return to the Streamlit dashboard and click **Run drift detection**.

The **Schema changes** section should show all nine changes listed above. Their display order may differ.

The **Affected code** section should include these files:

- `customer_repository.py`
- `order_repository.py`
- `product_repository.py`
- `report_queries.sql`

Affected Python functions include:

- `get_customer_profile`
- `create_customer`
- `list_customer_orders`
- `mark_order_complete`
- `list_available_products`

Expected severity totals are:

- 4 high-severity findings
- 2 medium-severity findings
- 3 low-severity findings

The controlled test contains 15 expected database-to-code impact links. The sample project uses valid static SQL, so an empty warnings list is a correct result.

Click **Download drift report** to download the complete result as JSON.

## 11. View the evaluation results

In another terminal, from the project folder, run:

```bash
cat evaluation_report.json
```

The important controlled-test results are:

```text
evaluation_passed: true
true_positives: 9
false_positives: 0
false_negatives: 0
accuracy: 1.0
precision: 1.0
recall: 1.0
false_positive_rate: 0.0
matched impact links: 15 of 15
```

These measurements apply to the supplied controlled test cases and should not be described as universal accuracy on every real-world project.

## 12. Verify the no-change result

Restore the original schema:

```bash
docker exec schemashield-db \
  psql -v ON_ERROR_STOP=1 \
  -U postgres \
  -d schemashield_demo \
  -f /project/samples/database/baseline_schema.sql
```

Click **Run drift detection** again without capturing a new baseline. The dashboard should show:

```text
No schema drift detected
```

This confirms that SchemaShield does not report changes when the baseline and current database match.

## 13. Stop and restart the project

Press `Control + C` in the FastAPI and Streamlit terminals.

Stop PostgreSQL:

```bash
docker stop schemashield-db
```

For the next demonstration, start the same database container:

```bash
docker start schemashield-db
```

Load `baseline_schema.sql` again before beginning a new demonstration. Then start FastAPI, start Streamlit, and capture a fresh baseline.

## Optional cleanup

Remove the stopped demo container only if it is no longer needed:

```bash
docker rm schemashield-db
```

Removing the container does not remove the SQL files stored in Git. Running the Docker setup command recreates the same demo database.

## Common problems

### `ModuleNotFoundError: No module named 'backend'`

Run commands from the project root and use Python to start pytest:

```bash
cd CollagePro
source .venv/bin/activate
python -m pytest -q
```

### `Cannot connect to the Docker daemon`

Open Docker Desktop and wait until it finishes starting.

### `The container name schemashield-db is already in use`

Start the existing container:

```bash
docker start schemashield-db
```

### Port `55432` is already in use

Choose another unused computer port, such as `55433`:

```bash
docker run \
  --name schemashield-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=schemashield_demo \
  -p 55433:5432 \
  -v "$PWD:/project:ro" \
  -d postgres:16-alpine
```

Then use port `55433` in the dashboard PostgreSQL URL.

### The dashboard cannot reach FastAPI

Confirm that the backend terminal is still running and that `http://127.0.0.1:8000/health` returns `{"status":"ok"}`.

### Baseline capture reports zero tables

Load `baseline_schema.sql` again and make sure the dashboard schema name is exactly:

```text
schemashield_demo
```

### The dashboard shows unexpected changes

Restore `baseline_schema.sql`, capture a new baseline, apply `modified_schema.sql`, and then run drift detection again in that order.

## Project scope

- PostgreSQL is the supported database.
- Python source code and statically detectable SQL are supported.
- Dynamic and ORM-generated SQL may not be fully resolved.
- Rename detection is heuristic and can be ambiguous in some cases.
- SchemaShield reports potentially affected code; it does not automatically modify application code or perform database migrations.
