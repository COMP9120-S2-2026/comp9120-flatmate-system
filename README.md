# COMP9120 Flatmate Matching System

Group 34 — Semester 2, 2026: Yijian Mei (David), Max, Yu-Han Chang (John).

## Compatibility-only revision

This revision fixes the older A/C Python modules to work with Max's existing ten-table database. It does **not** change the shared schema, triggers, SQL queries, sample data, transaction examples or original grouped menu.

Read [COMPATIBILITY_REVIEW.md](docs/COMPATIBILITY_REVIEW.md) for the precise scope. The earlier broad integration proposal has been withdrawn from this PR.

## VS Code and pgAdmin setup

Requires Python 3.10+ and PostgreSQL 15+.

1. Open this repository folder in VS Code.
2. Create the environment and install dependencies:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

3. Copy config.example.json to config.json if it does not exist. Edit your local host, port, dbname, user and password. Never commit credentials or edit the example with a real password.
4. Create a new empty database in pgAdmin (for example housematch_compat), and use that name in config.json.
5. Initialise and seed once:

~~~powershell
.\.venv\Scripts\python.exe run.py init
.\.venv\Scripts\python.exe run.py seed
.\.venv\Scripts\python.exe run.py list --status OPEN
~~~

Both initialisation and manual SQL setup now use the root housematch_schema.sql and housematch_triggers.sql. Sample data come from housematch_sample_data.sql: 14 users, 10 properties, 12 rooms and 12 listings.

Do not initialise over existing tables. Databases made with the earlier broad PR version need a separate fresh database; no automatic migration is included.

In pgAdmin, open Query Tool on the same database and run sql/90_pgadmin_queries.sql.

## Two entry points

- **run.py**: the repaired A/C service command line; uses config.json, or DATABASE_URL if no local config exists.
- **housematch_cli.py**: Max's original grouped menu, preserved unchanged. It prompts for a password and uses the DB_HOST/DB_NAME/DB_USER/DB_PORT constants at the top of that file. Set these to the same database if using both entry points. Never hard-code a password.

The grouped menu in the reviewed main commit implements preference viewing; its other unfinished options remain placeholders. This revision does not claim to finish those features.

## A/C command examples

~~~powershell
python run.py --user-id 1 publish examples/new_room.json --rent 360 --available-from 2026-11-01 --housemates 2
python run.py --user-id 2 applications
python run.py --user-id 1 applicants 1
python run.py --user-id 1 accept 1
python run.py --help
~~~

Use IDs returned by the program and the appropriate listing owner. The accept command modifies data, so run demonstrations on a disposable database. User IDs represent demo identities, not authentication.

Application statuses remain PENDING, ACCEPTED and REJECTED. Withdrawal is not offered by the command line; the old Python withdrawal function now reports that it is unsupported rather than writing an invalid status. Reapplication after rejection remains prohibited by the original uniqueness constraint.

## Tests and evidence

~~~powershell
$env:TEST_DATABASE_URL = 'postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_TEST_DATABASE'
python tools/run_verification.py
~~~

Use a test role allowed to create schemas. Tests create and remove uniquely named schemas, not application tables. [Current results](docs/ALIGNMENT_TEST_RESULTS.md) replace the earlier broad-PR results.

Earlier Member A reports, diagrams and test evidence under docs are historical, not current whole-system documentation. Superseded SQL and member implementations are retained under archive/pre-integration and must not be used for setup.

## Scope

No new preference/search/booking service, rescheduling, conditional unique indexes, mandatory-profile triggers, status domains, authentication or web interface are added. Remaining report/schema differences need group review rather than silently changing the database.
