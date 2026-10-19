# HouseMatch — COMP9120 Flatmate Matching System

Group 34, Semester 2, 2026: Yijian Mei (David), Max, and Yu-Han Chang (John).

## Integrated baseline

The application uses the ten-table relational schema in the group report (page 7), including PROPERTY_CHARACTERISTICS. Room/listing, preference/search/viewing, and application services now share the same schema and connection configuration. This is a reviewable integration baseline, not a claim that the final report or authentication is complete.

Read [schema decisions](docs/SCHEMA_ALIGNMENT.md) and [team handoff](HANDOFF.md). Earlier Member A reports and diagrams under docs are historical, not the final integrated design.

## Local setup in VS Code and pgAdmin

Requires Python 3.10+ and PostgreSQL 15+ (NULLS NOT DISTINCT is used).

1. Open the repository itself in VS Code, not its parent folder.
2. Create a virtual environment and install dependencies:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

3. Select .venv/Scripts/python.exe as the Python interpreter.
4. Copy config.example.json to config.json only if config.json does not already exist. Fill in your local host, port, database, user and password. Never put credentials into config.example.json or commit config.json.
5. In pgAdmin, create a **new empty database**, for example housematch_integrated. Set the same database name in config.json. Existing databases are not migrated by this change.
6. In the VS Code terminal, run:

~~~powershell
.\.venv\Scripts\python.exe run.py init
.\.venv\Scripts\python.exe run.py seed
.\.venv\Scripts\python.exe run.py list --status OPEN
~~~

Run init and seed only once on the new database. Do not run archived SQL or initialise over existing tables. The VS Code Run and Debug configurations can also initialise, seed and list data.

For an interactive menu:

~~~powershell
.\.venv\Scripts\python.exe housematch_cli.py
~~~

In pgAdmin, open Query Tool on that same database and run sql/90_pgadmin_queries.sql. Refresh Schemas > public > Tables to see all ten tables.

Connection priority: explicit connection URL (tests), then local config.json, then DATABASE_URL. No PYTHONPATH setting is needed for run.py. Demo data contain 14 users, 10 properties, 12 rooms and 12 listings; all are synthetic.

## Example commands

~~~powershell
python run.py --user-id 1 profiles
python run.py --user-id 1 search Default
python run.py --user-id 1 applications
python run.py --user-id 1 profile-save examples/preference_profile.json
python run.py --user-id 1 publish examples/new_property_room.json --rent 360 --available-from 2026-11-01 --housemates 2
python run.py --help
~~~

Use IDs returned by the program for later operations. A demo user ID is **not authentication**. Production login, password handling and session security are not implemented.

## Verification

Use an isolated test database and a role allowed to create schemas:

~~~powershell
$env:TEST_DATABASE_URL = 'postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_TEST_DATABASE'
python tools/run_verification.py
~~~

The tests create and remove uniquely named test schemas. Do not use production credentials. [Current verification](docs/ALIGNMENT_TEST_RESULTS.md) records the integrated run; older TEST_RESULTS.md and cli_smoke_results.json describe the historical A-only version.

## Files

| Path | Purpose |
| --- | --- |
| housematch_schema.sql | Canonical ten-table definitions |
| housematch_triggers.sql | Database business rules |
| housematch_sample_data.sql | Synthetic fixtures for empty tables |
| housematch_queries.sql | Demonstration queries |
| housematch_transactions.sql | Write-operation examples; disposable demo databases only |
| housematch_tests.sql | SQL integrity tests, rolled back after execution |
| housematch_concurrency_tests.sql | Manual two-session scenarios |
| src/housematch/member_a.py | Property, room and listing services |
| src/housematch/member_b.py | Preferences, matching, saves and viewings |
| src/housematch/member_c.py | Application lifecycle and atomic acceptance |
| tests/test_integration.py | Integrated and concurrent PostgreSQL tests |
| archive/pre-integration/ | Earlier implementation retained for reference |

Review the report discrepancies and remaining work in HANDOFF.md before submission. Record actual individual contributions and acknowledge AI assistance according to course rules.
