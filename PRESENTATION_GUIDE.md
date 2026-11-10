# SchemaShield Presentation and Demo Guide

This guide explains SchemaShield in simple language. Read it before presenting or demonstrating the application.

## 1. SchemaShield in one sentence

SchemaShield detects changes in a PostgreSQL database and tells developers which Python files, functions, and SQL queries may be affected by those changes.

## 2. The problem

Most applications use a database. The application code sends SQL queries to that database.

For example, the database may have a `customers` table with a column called `full_name`:

```sql
SELECT full_name FROM customers;
```

Later, someone may rename `full_name` to `name` in the database. The old application code still asks for `full_name`, which no longer exists. This can cause errors when the application runs.

The same problem can happen when someone:

- Adds a table or column.
- Removes a table or column.
- Renames a table or column.
- Changes a datatype, length, default value, or other column property.

Checking every source file manually is slow and unreliable. A developer may not know which functions use the changed database object.

This difference between an expected database structure and the current structure is called **schema drift**.

## 3. Our solution

SchemaShield solves the problem in four main stages:

1. It saves the original database structure as a **baseline**.
2. It reads the current database and compares it with the baseline.
3. It scans Python and SQL files to find where database tables and columns are used.
4. It creates an impact report showing the changes, affected code, and severity.

SchemaShield does not automatically change the application code. It gives developers an early warning and tells them where to look.

## 4. A simple real-world example

Assume the original database contains:

```text
customers.full_name
customers.phone
orders.order_total
products
```

The Python application contains queries that use these objects.

Now assume the database is changed:

```text
customers.full_name becomes customers.name
customers.phone is removed
orders.order_total becomes orders.total_amount
products table is removed
```

SchemaShield compares the old and new database structures. It then scans the source code and reports information such as:

```text
Changed object: customers.full_name
Change: renamed to customers.name
Severity: high
Affected file: customer_repository.py
Affected function: get_customer_profile
```

The developer can now update that function before users face a runtime error.

## 5. Important terms

### Database schema

The structure of a database: tables, columns, datatypes, keys, defaults, and relationships.

### Baseline

A saved copy of the original database structure. Think of it as a photograph of the database before changes were made.

### Current schema

The database structure that exists now.

### Schema drift

The difference between the baseline schema and the current schema.

### Static analysis

Reading and understanding source code without running the application.

### Dependency

A connection between code and a database object. For example, a function that selects `customers.email` depends on that column.

### Impact analysis

Finding which queries, functions, and files may be affected by a database change.

### False positive

The tool reports a change or impact that is not actually present.

### False negative

The tool misses a change or impact that should have been reported.

## 6. Main technologies and why they are used

### Python

Python contains the core comparison and analysis logic. It is simple, readable, and has good libraries for database and source-code analysis.

### PostgreSQL

PostgreSQL is the database supported by the current version. The project reads metadata from PostgreSQL's `information_schema`.

### SQLAlchemy

SQLAlchemy connects Python to PostgreSQL and runs the metadata queries.

### Psycopg

Psycopg is the PostgreSQL database driver used by SQLAlchemy.

### Python AST

AST means Abstract Syntax Tree. Python converts a source file into a structured tree. SchemaShield uses this tree to find functions and SQL strings without executing the application code.

### SQLGlot

SQLGlot parses SQL text and identifies referenced tables, columns, aliases, and statement types.

### FastAPI

FastAPI is the backend. It receives requests from the dashboard, runs the analysis modules, and returns structured JSON results.

### Streamlit

Streamlit provides the dashboard. It lets the user enter database details, capture a baseline, run drift detection, view results, and download the report.

### Docker

Docker runs the same PostgreSQL 16 environment on every team member's laptop. This avoids differences between local PostgreSQL installations.

### JSON

JSON is used to store the baseline and the final drift report because it is easy for people and software to read.

## 7. Complete project flow

The complete flow is:

```text
User
  -> Streamlit dashboard
  -> FastAPI backend
  -> PostgreSQL schema extraction
  -> Baseline/current schema comparison
  -> Python AST and SQLGlot code analysis
  -> Dependency mapping
  -> Impact and severity analysis
  -> Dashboard and downloadable JSON report
```

### Step 1: The user provides inputs

The dashboard asks for:

- FastAPI URL
- PostgreSQL connection URL
- PostgreSQL schema name
- Python project folder
- Baseline JSON file location

These inputs tell SchemaShield which database and source-code project to analyse.

### Step 2: SchemaShield captures the baseline

When the user clicks **Capture baseline**, FastAPI connects to PostgreSQL.

SchemaShield reads `information_schema` to collect:

- Table names
- Column names
- Column positions
- Datatypes
- Maximum lengths
- Numeric precision and scale
- Nullability
- Default values
- Primary keys
- Unique columns
- Foreign keys
- Referenced tables and columns

The information is normalised into Python schema objects and saved in `baseline.json`.

Why this is needed: SchemaShield needs a known original structure to recognise later changes.

### Step 3: The database changes

During normal development, someone changes tables or columns. In the demonstration, `modified_schema.sql` creates controlled changes so the result is known in advance.

### Step 4: SchemaShield reads the current schema

When the user clicks **Run drift detection**, SchemaShield connects to PostgreSQL again and reads the structure that exists now.

### Step 5: The comparison engine detects drift

The comparison engine checks the baseline and current schema.

It detects:

- Added tables
- Removed tables
- Renamed tables
- Added columns
- Removed columns
- Renamed columns
- Modified column properties

Renames are detected using structural similarity. Rename detection is a best estimate because databases do not always record whether an object was renamed or removed and recreated.

### Step 6: SchemaShield scans the source code

SchemaShield scans Python files and standalone `.sql` files in the selected project folder.

Python AST identifies:

- Source files
- Python functions
- Module-level SQL strings
- SQL strings inside functions

SQLGlot identifies:

- SQL statement type, such as `SELECT`, `INSERT`, `UPDATE`, or `DELETE`
- Referenced tables
- Referenced columns
- Table aliases

The source code is not executed. This makes the scan safer.

### Step 7: Dependency mapping connects the database to code

SchemaShield creates relationships such as:

```text
customers.email
  -> customer_repository.py
  -> get_customer_profile
  -> SELECT query
```

This map tells the system where each database object is used.

### Step 8: Impact analysis checks each change

For every detected database change, SchemaShield checks the dependency map.

If code uses the changed object, that file and function are added to the impact report.

### Step 9: Severity is assigned

SchemaShield uses three simple severity levels:

- **High:** A referenced table or column was removed or renamed. Existing queries are likely to fail.
- **Medium:** A referenced column was modified. The query may continue to work, but its behaviour or accepted data may change.
- **Low:** An object was added or no existing code depends on the changed object.

### Step 10: Results are returned

FastAPI returns:

- Detected changes
- Affected files
- Affected functions
- Query types and query identifiers
- Severity levels
- Analysis warnings
- Processing time

Streamlit displays the results and provides a **Download drift report** button.

## 8. What is stored in Git

The running PostgreSQL container is not stored in Git. Git stores the instructions required to recreate the same database:

- `samples/database/baseline_schema.sql`
- `samples/database/modified_schema.sql`
- `samples/database/expected_changes.json`
- `samples/database/expected_impacts.json`
- `samples/python_project/`

Each team member loads these files into Docker and receives the same demonstration database.

The generated `baseline.json` file is local and is ignored by Git.

## 9. Demonstration test case

### Original database

The baseline contains three tables:

- `customers`
- `orders`
- `products`

It contains 14 columns in total.

### Modified database

The demonstration intentionally makes nine changes:

1. Adds the `audit_logs` table.
2. Removes the `products` table.
3. Renames `customers.full_name` to `customers.name`.
4. Removes `customers.phone`.
5. Changes the maximum length of `customers.email` from 150 to 200.
6. Adds `customers.is_active`.
7. Renames `orders.order_total` to `orders.total_amount`.
8. Changes the maximum length of `orders.status` from 20 to 30.
9. Adds `orders.updated_at`.

### Expected impact

SchemaShield should identify affected code in:

- `customer_repository.py`
- `order_repository.py`
- `product_repository.py`
- `report_queries.sql`

Expected affected Python functions include:

- `get_customer_profile`
- `create_customer`
- `list_customer_orders`
- `mark_order_complete`
- `list_available_products`

Expected severity totals are:

- 4 high-severity findings
- 2 medium-severity findings
- 3 low-severity findings

## 10. Short demonstration procedure

The complete setup commands are documented in `README.md`. The following is the presentation sequence.

### Terminal 1: Start PostgreSQL and load the baseline

```bash
docker start schemashield-db
docker exec schemashield-db psql -v ON_ERROR_STOP=1 -U postgres -d schemashield_demo -f /project/samples/database/baseline_schema.sql
```

If the container has never been created, follow the Docker creation step in `README.md` first.

### Terminal 1: Start FastAPI

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload
```

Leave this terminal running.

### Terminal 2: Start Streamlit

```bash
source .venv/bin/activate
python -m streamlit run frontend/app.py
```

Leave this terminal running.

### Dashboard: Capture the original schema

Use:

```text
FastAPI URL: http://localhost:8000
PostgreSQL URL: postgresql+psycopg://postgres:postgres@localhost:55432/schemashield_demo
Schema name: schemashield_demo
Python project folder: samples/python_project
Baseline JSON file: baseline.json
```

Click **Capture baseline**. The expected result is three saved tables.

### Terminal 3: Apply the changes

```bash
docker exec schemashield-db psql -v ON_ERROR_STOP=1 -U postgres -d schemashield_demo -f /project/samples/database/modified_schema.sql
```

### Dashboard: Run the analysis

Click **Run drift detection**.

Verify:

- Nine schema changes are displayed.
- Affected files and functions are displayed.
- Severity levels are displayed.
- The report download button is available.

### Explain the result

Say:

> SchemaShield saved the original database structure, compared it with the changed database, scanned the source code, and connected each risky database change to the files and functions that use it.

## 11. Suggested presentation script

### 30-second introduction

> Applications depend on database tables and columns. When the database changes, old SQL queries in the code may stop working. Finding all affected code manually is difficult. SchemaShield saves a baseline database structure, detects later schema changes, scans Python and SQL code, and produces an impact report showing affected files, functions, and severity.

### While capturing the baseline

> We are saving the original structure of the database. SchemaShield reads table, column, datatype, constraint, and key metadata from PostgreSQL information_schema and stores it as JSON.

### While applying the modified schema

> This controlled script simulates normal development changes such as adding, removing, renaming, and modifying tables and columns.

### While running drift detection

> SchemaShield now compares the baseline with the current database. At the same time, it uses Python AST and SQLGlot to understand where database objects are used in the source code.

### While showing affected code

> A removed or renamed object receives high severity when existing code depends on it. A modified referenced column receives medium severity. Added or unreferenced objects receive low severity.

### While downloading the report

> The same result can be downloaded as JSON and used by developers or integrated into another workflow.

## 12. Evaluation results

The controlled evaluation produced:

```text
Expected schema changes: 9
Correctly detected changes: 9
False changes: 0
Missed changes: 0
Expected code-impact links: 15
Correctly matched impact links: 15
Missing impact links: 0
Unexpected impact links: 0
```

Calculated metrics:

```text
Accuracy: 1.0
Precision: 1.0
Recall: 1.0
False-positive rate: 0.0
```

Processing time in the recorded test was approximately 42 milliseconds. Processing time may differ slightly on another laptop.

These results apply only to the supplied controlled test cases. Do not claim that the application has 100% accuracy on every possible real-world project.

## 13. How the metrics are calculated

### Accuracy

How many evaluated cases were classified correctly.

```text
(true positives + true negatives) / all evaluated cases
```

### Precision

Of all changes SchemaShield reported, how many were correct.

```text
true positives / (true positives + false positives)
```

### Recall

Of all changes that should have been detected, how many SchemaShield found.

```text
true positives / (true positives + false negatives)
```

### False-positive rate

How often SchemaShield incorrectly reports a change in an evaluated unchanged case.

```text
false positives / (false positives + true negatives)
```

## 14. What SchemaShield does not do

SchemaShield currently does not:

- Automatically modify affected Python code.
- Automatically perform database migrations.
- Guarantee that every rename is identified correctly.
- Fully understand every dynamically generated SQL query.
- Fully understand ORM-generated database operations.
- Support databases other than PostgreSQL.
- Replace normal testing, code review, or developer judgement.

The application reports potential impact. A developer reviews the report and decides how to update the code.

## 15. Current limitations

### Dynamic SQL

A query assembled while the application is running may not exist as one complete string in the source code. Static analysis may not be able to understand it.

### ORM-generated SQL

Frameworks can build SQL internally without writing ordinary SQL strings. The current version focuses on statically detectable SQL.

### Rename ambiguity

A database may not tell us whether a column was renamed or whether one column was removed and another was added. SchemaShield uses structure-based matching, so some cases can be ambiguous.

### Affected SQL display

The current dashboard displays the affected file, function, and query type. A future version can display the complete SQL statement and exact source line directly in the dashboard.

### Controlled evaluation size

The current evaluation is intentionally small and repeatable. Larger and more varied projects are needed before making wider accuracy claims.

## 16. Future improvements

SchemaShield can be improved by adding:

1. Full affected SQL text and exact line numbers in the dashboard.
2. A check that prevents saving an empty baseline when the schema name is incorrect.
3. Better rename detection with confidence scores and migration history.
4. Support for dynamic SQL patterns.
5. Support for ORM frameworks such as SQLAlchemy ORM and Django ORM.
6. Support for MySQL, SQLite, SQL Server, and other databases.
7. A visual dependency graph connecting tables, columns, queries, functions, and files.
8. Git and CI/CD integration so drift analysis can run automatically before deployment.
9. Notifications through email, Slack, or issue trackers.
10. Baseline version history and comparison between multiple database versions.
11. Suggested code changes, while still requiring developer approval.
12. Authentication and access control for team or hosted use.
13. Larger real-world evaluation datasets and performance testing.

## 17. Common questions and answers

### What is the main purpose of SchemaShield?

To detect database schema changes and identify application code that may be affected.

### What is schema drift?

Schema drift is the difference between the expected or saved database structure and the current database structure.

### Why do we need a baseline?

Without an original structure, the system has nothing to compare with the current database.

### Why use `information_schema`?

It is PostgreSQL's standard metadata view for reading tables, columns, datatypes, defaults, and constraints.

### Does SchemaShield read the actual customer or business data?

No. It reads database structure metadata, not table records.

### Does SchemaShield execute the Python application?

No. It uses static analysis to inspect source code without executing it.

### Why use AST instead of searching text with keywords?

AST understands Python structure. It can connect a SQL string to the function containing it and avoids many errors caused by simple text matching.

### Why use SQLGlot?

SQLGlot understands SQL structure and can identify tables, columns, aliases, and statement types more reliably than regular expressions.

### What is the difference between drift detection and migration?

Drift detection reports what changed. A migration intentionally changes the database. SchemaShield detects and reports changes; it does not perform migrations.

### Does the system correct affected code?

No. It reports the affected location and severity. The developer makes the final code correction.

### How is severity decided?

Referenced removals and renames are high severity, referenced modifications are medium severity, and additions or unreferenced changes are low severity.

### Why is removing a table high severity?

Any query using that table will probably fail because the table no longer exists.

### Why is adding a column usually low severity?

Existing queries usually continue to work when an unused column is added.

### Can SchemaShield produce false results?

Yes. Static analysis and rename detection have limitations. This is why the report says code is potentially affected and should be reviewed by a developer.

### Why is Docker used?

Docker provides the same PostgreSQL version and configuration on every laptop, making the demonstration repeatable.

### Is the database pushed to Git?

The running database is not pushed. The SQL files that recreate the baseline and modified database are pushed.

### Why are the reported metrics 100%?

The controlled test cases have known expected answers, and SchemaShield matched all of them. This does not prove 100% accuracy on all real applications.

### Does it require a GPU or HPC system?

No. It uses schema comparison and static source-code analysis and runs on a normal CPU laptop.

### Can it analyse Java, JavaScript, or other languages?

Not in the current version. The current scope is Python source code and SQL.

### Can it work with MySQL?

Not currently. The extraction logic is designed for PostgreSQL.

### What happens when there is no schema change?

The comparison returns zero changes and the dashboard displays `No schema drift detected`.

### What happens when SQL cannot be parsed?

The scan continues and records a warning instead of stopping the entire analysis.

### What is unique about the approach?

It does more than list database differences. It connects those differences to Python functions, SQL queries, and source files so developers know where the risk is.

## 18. Demo recovery guide

### Docker is not running

Open Docker Desktop and wait until it is ready.

### The container already exists

```bash
docker start schemashield-db
```

### The dashboard cannot connect to FastAPI

Make sure the backend terminal is running:

```bash
python -m uvicorn backend.api:app --reload
```

Open `http://127.0.0.1:8000/health`. It should show `{"status":"ok"}`.

### Baseline capture shows zero tables

Confirm that the schema name is `schemashield_demo` and reload the baseline SQL.

### The result is not the expected nine changes

Repeat this exact order:

1. Load `baseline_schema.sql`.
2. Click **Capture baseline**.
3. Load `modified_schema.sql`.
4. Click **Run drift detection**.

### `ModuleNotFoundError` appears

Enter the repository root, activate the environment, and run Python modules using `python -m`:

```bash
source .venv/bin/activate
python -m pytest -q
```

## 19. Final presentation checklist

Before presenting, confirm:

- Docker Desktop is running.
- The `schemashield-db` container starts successfully.
- The baseline SQL loads successfully.
- `python -m pytest -q` reports 30 passing tests.
- FastAPI health returns `{"status":"ok"}`.
- Streamlit opens at `http://localhost:8501`.
- Baseline capture reports three tables.
- The modified SQL loads successfully.
- Drift detection reports nine changes.
- Affected files, functions, and severity levels are visible.
- The JSON report downloads successfully.
- The presenter can explain that SchemaShield reports affected code but does not automatically repair it.
- The presenter describes the 100% metrics as controlled-test results only.

## 20. Final summary

SchemaShield protects applications from unnoticed database changes. It saves a baseline, detects schema drift, understands statically detectable Python and SQL dependencies, and produces an impact report. Its main value is that it tells developers not only what changed in the database, but also where the application may be affected.
