# Shared PostgreSQL database

The canonical SQL files are in the repository root. Execute these in a new empty PostgreSQL 15+ database:

1. housematch_schema.sql
2. housematch_triggers.sql
3. housematch_sample_data.sql

Alternatively, run run.py init and run.py seed. Do not initialise twice.

The shared SQL files and their database rules are unchanged in this compatibility revision. The Python services have been adapted to them.

housematch_queries.sql contains query examples. housematch_transactions.sql and housematch_concurrency_tests.sql perform writes and belong in disposable databases. housematch_tests.sql contains the original rolled-back SQL checks.

Run tools/run_verification.py for Python compatibility and SQL regression tests.
