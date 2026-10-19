# Compatibility-only handoff

This revision aligns the older A/C modules with Max's shared database without changing its rules.

## Fixed

- Move property/address fields out of room queries and inserts; use property_characteristics.
- Supply listing_date, status and num_housemates when inserting listings.
- Remove allocation_status and FILLED assumptions.
- Read dictionary query results consistently.
- Use the root schema/triggers and original sample data for run.py setup.
- Follow the existing SQL acceptance workflow inside one Python transaction.
- Refuse unsupported withdrawal without changing the application status domain.

## Preserved

Max's root SQL files and housematch_cli.py are unchanged from main commit 70e27bc. His menu still has unfinished options; this patch does not implement those extra features. All original SQL constraints and status values remain authoritative.

## Review

1. Review docs/COMPATIBILITY_REVIEW.md.
2. Run verification against an isolated PostgreSQL database.
3. Try run.py commands in a new disposable database.
4. Confirm remaining report/schema naming differences separately.
5. Decide on rescheduling in a separate change if it is required.

Old scripts and tests under archive/pre-integration are historical. Do not run them against the shared database. No existing local data or personal configuration is migrated.
