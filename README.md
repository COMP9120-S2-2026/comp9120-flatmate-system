# COMP9120 Flatmate Matching System

Group 34 - Semester 2, 2026

## Project
A database-driven flatmate matching system where households can list
available rooms and prospective flatmates can search and apply.

## Team
- Yijian Mei (David)
- Max
- Yu-Han Chang (John)

## Current Stage
- Week 10: Member A's Room/Listing module is implemented.
- Member B's search/preferences/viewings and Member C's accounts/applications remain reserved.
- A/B/C are provisional responsibility labels; the group must map them to real names.
- This is an integration baseline, not a completed whole-system submission.

Read [HANDOFF.md](HANDOFF.md) before extending the schema or application.

## Setup

### VS Code + pgAdmin (local configuration)

1. Open this repository folder in VS Code. Install Microsoft's Python and
   Python Debugger extensions and select `.venv/Scripts/python.exe` as the interpreter.
2. If needed, run `py -3.12 -m venv .venv`, then
   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. Copy `config.example.json` to `config.json` if it does not already exist.
   Edit host, port, dbname, user and password in VS Code.
   This file is ignored by Git because it contains local credentials.
   Do not paste its contents into chat, screenshots or commits.
4. In pgAdmin, connect to the same server using the same host/port/user.
   Create a new empty database named `housematch` if it does not exist.
   Do not delete an existing database or initialise over existing tables.
5. In VS Code's Run and Debug panel, select
   **HouseMatch: Initialise EMPTY database (once)** and run it.
   Only after successful initialisation, run **HouseMatch: Seed demo data (once)**.
6. Select **HouseMatch: List open listings** for everyday use.
   Alternatively run `.\.venv\Scripts\python.exe run.py` in the terminal.
   No PYTHONPATH or DATABASE_URL environment setup is required for this route.
7. In pgAdmin, open Query Tool on **housematch**, then open
   `sql/90_pgadmin_queries.sql` to query the same data.
   Refresh **Schemas > public > Tables** after creating the tables.

Connection priority: an explicitly supplied connection URL (used by tests),
then local `config.json`, then `DATABASE_URL`.
An invalid local config raises an error instead of silently connecting elsewhere.
The database must exist before the application connects.

### Environment-variable alternative

Use Python 3.10+ and PostgreSQL. Create a separate empty database named
`housematch` first. Run these commands from the repository root in PowerShell:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\src"
$env:DATABASE_URL = 'postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/housematch'
python -m housematch.cli init
python -m housematch.cli seed
```

Use your own database credentials locally. Never commit passwords or real
connection strings. The application reads environment variables directly.
`init` creates tables in an empty schema and does not drop existing tables.
`seed` refuses to overwrite non-empty user data. All demo data are synthetic.

## Demonstrate Member A's functionality

```powershell
python -m housematch.cli list --status OPEN
python -m housematch.cli --user-id 1 list --mine
python -m housematch.cli show 9
python -m housematch.cli --user-id 1 publish examples/new_room.json --rent 360 --available-from 2026-11-01
python -m housematch.cli --user-id 1 update 9 --rent 335 --available-from 2026-11-05
python -m housematch.cli --user-id 1 update-room 1 examples/new_room.json
python -m housematch.cli --user-id 1 close 9
python -m housematch.cli --user-id 1 relist 1 --rent 340 --available-from 2026-11-05
```

Fresh seeded data contain 3 demo users, 8 rooms and 9 listings, including one
CLOSED historical advertisement. Listing 9 belongs to demo user 1.
`--user-id` selects a demo identity; it is not authentication. Member C owns
the account/session implementation and full application acceptance workflow.

## Tests

```powershell
$env:TEST_DATABASE_URL = $env:DATABASE_URL
python -m unittest discover -s tests -v
python tools/run_verification.py
```

Tests require permission to create schemas. They create a uniquely named
test schema and remove only that schema; existing application schemas are
not reset. The verification script records fresh results under `docs/`.

[Recorded test results](docs/TEST_RESULTS.md) document the previous
25-test Member A run. [CLI smoke results](docs/cli_smoke_results.json)
document the previous command-line smoke run. These records do not prove
that the reserved B/C features or the integrated whole system work.

## Repository layout and responsibilities

| Path | Purpose |
| --- | --- |
| `src/housematch/` | Python implementation and clearly labelled B/C placeholders |
| `sql/00_user_contract.sql` | Shared user scaffold, to be extended by C |
| `sql/10_member_a.sql` | Room/Listing tables, constraints, indexes and triggers |
| `sql/20_member_b_RESERVED.sql` | B's schema placeholder |
| `sql/30_member_c_RESERVED.sql` | C's schema placeholder |
| `tests/test_member_a.py` | A's PostgreSQL integration tests |
| `examples/new_room.json` | Example room input |
| `HANDOFF.md` | Responsibilities, assumptions and integration contract |
| `docs/` | Draft report, A-only ER fragment and verification evidence |

## Report and remaining work

- [English Word report](docs/HouseMatch_Integrated_Report_Member_A.docx)
- [Editable Markdown report](docs/HouseMatch_Integrated_Report_Member_A.md)
- [Member A conceptual ER fragment](docs/diagrams/Member_A_Conceptual_ERD.png)

The report completes A's contribution and visibly reserves B/C's sections.
The diagram is an A-only fragment, not the final whole-system ER diagram.
Review the working assumptions in HANDOFF.md together, complete B/C's real
implementations and evidence, and run end-to-end tests before final submission.
Record actual individual contributions and acknowledge AI assistance as
required by the project brief.
