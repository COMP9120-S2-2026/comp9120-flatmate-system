# HouseMatch — COMP9120 Group 34

Final integration candidate combining `feature/housematch-clean` at `fc4531e` (including restored PR #5) with compatible advertiser services and supporting files from `main` at `865f265`.

## Setup

Requires Python 3.10+ and PostgreSQL 15+. Create a new, empty database for this candidate. Do not initialise over existing tables or use the archived SQL.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows use `py -m venv .venv` and `.venv\Scripts\Activate.ps1`.
Copy `config.example.json` to `config.json` and enter your local connection details. The local file is ignored by Git. Alternatively set `DATABASE_URL` when no local config exists.

```sh
python run.py init
python run.py seed
python run.py list --status OPEN
```

Initialisation uses `housematch_schema.sql` then `housematch_triggers.sql`; seed loads `housematch_sample_data.sql`. Seed once into empty tables. These files and `housematch_transactions.sql` are unchanged from both source branches. The schema has ten tables.

## Run the prototype

### Grouped interactive menu

```sh
python housematch_cli.py
```

Set `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PORT` at the top of this file to the same database configured above. This interface prompts for a password; it does not read `config.json`. `CURRENT_USER_ID` selects a synthetic demo identity, not authentication. The default ID 5 is Ava Thompson. User 7 has seeded preference profiles; user 1 owns listing 1. Restart with the appropriate demo ID to demonstrate owner/applicant workflows.

The menu supports preference creation/selection, profile-based search, saved listings, bookings/cancellation/rebooking, applications and owner acceptance/rejection. Select an active profile before searching. The default user must first create a profile with at least one matching suburb. Active selection lasts for the session.

### Advertiser and application commands

The separate compatible service interface preserves publishing, editing, closing and relisting:

```sh
python run.py --help
python run.py --user-id 1 publish examples/new_room.json --rent 360 --available-from 2026-11-01 --housemates 2
python run.py --user-id 1 applicants 1
python run.py --user-id 2 applications
```

Use returned IDs and the correct owner. Both interfaces share the same database, but have distinct connection configuration and transaction implementations. Keep their tests separate. Manual `close` changes listing status only; acceptance also cancels viewings and rejects competing applications. The service rejection command permits rejecting a pending application on a non-OPEN listing; the grouped menu requires OPEN. These existing behaviours have not been redesigned.

## Verify in a disposable database

```sh
export TEST_DATABASE_URL='postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_TEST_DATABASE'
python tools/run_verification.py
```

On PowerShell set `$env:TEST_DATABASE_URL` instead. Tests create and remove uniquely named schemas; the test role needs permission to create schemas. Never use a production database. The verification command updates evidence in `docs/ALIGNMENT_TEST_RESULTS.md` and `docs/alignment_test_results.json`.

The integrated suite covers advertiser services, configuration, the original 51-case SQL suite, restored grouped CLI acceptance (including injected failure and two competing sessions), profile/search/save operations, booking cancellation/rebooking and application submission. Five additional manual database concurrency scenarios are documented in `housematch_concurrency_tests.sql`; they are not automatically run by the Python suite.

`housematch_queries.sql` contains eight representative queries. `housematch_transactions.sql` contains executable examples that COMMIT changes and assume particular sample IDs: use a disposable demo database, not as a setup script. Run query evidence on a fresh seed before transaction demonstrations.

## Scope and evidence

Preserved domains: listing OPEN/PAUSED/CLOSED; application PENDING/ACCEPTED/REJECTED. No withdrawal, repeat application to the same listing, rescheduling, household membership, room occupancy or authentication is added. Mandatory profile creation and a listing for every room are not database-enforced. The OPEN-application trigger guards submission; acceptance's OPEN/owner checks are in the application workflow. Saved-listing ranks exist in SQL; the grouped menu orders saved listings by rent.

Historical Member A reports/diagrams, `docs/TEST_RESULTS.md`, older JSON evidence and `archive/pre-integration` describe earlier versions and are not final whole-project evidence. Use the fresh alignment results and the agreed final report. The submission report, participation statement, poster and video are coordinated separately.
