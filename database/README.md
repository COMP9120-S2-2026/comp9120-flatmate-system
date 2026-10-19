# Database setup

Canonical SQL files are in the repository root. In a new empty PostgreSQL 15+ database, execute:

1. housematch_schema.sql
2. housematch_triggers.sql
3. housematch_sample_data.sql

Alternatively, use run.py init followed by run.py seed. Both routes use the same ten-table schema. Do not run both initialisation routes on the same database.

For read-only examples, use housematch_queries.sql or sql/90_pgadmin_queries.sql. Transaction and concurrency examples perform writes and belong in a disposable demo database. The integrated automated suite is run with tools/run_verification.py.

This is a fresh-install baseline, not an in-place migration. Preserve existing databases and personal configuration.
