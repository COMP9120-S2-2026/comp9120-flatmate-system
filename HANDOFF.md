# Integrated team handoff

## Agreed baseline

Use the report's page 7 ten-table schema, including PROPERTY_CHARACTERISTICS. The separate nine-table spreadsheet must be reconciled before submission. See docs/SCHEMA_ALIGNMENT.md.

## Suggested review ownership

These are review areas, not claims about who originally authored the code. Confirm the A/B/C mapping with the group.

| Area | Review responsibilities |
| --- | --- |
| A — Property, room and listing | Verify property sharing, room capacity, advertiser ownership, publish/relist and VS Code/pgAdmin setup |
| B — Preferences and viewings | Verify profile matching, suburb rules, saved listings, booking history and same-listing rescheduling |
| C — Applications and integration | Verify submit/withdraw/reject/accept, owner checks, atomic acceptance and concurrency evidence |
| Everyone | Reconcile ERD/schema/report, review the integrated diff, reproduce tests and prepare the demonstration |

## Before merging/submitting

- Review changes to all three service modules; earlier A/C implementations are retained in archive/pre-integration.
- Run the integrated tests on PostgreSQL and try the CLI against a new empty database.
- Align the Google ERD and separate schema spreadsheet with the approved relational model.
- Explain the default preference profile and deferred mandatory-participation rules in the report.
- Confirm the status domains and pet-preference semantics documented in SCHEMA_ALIGNMENT.md.
- Account registration/login/session handling remains outside this demo implementation. Do not describe demo user selection as authentication.
- Update the final report, screenshots, contribution statement and AI acknowledgement. Earlier A-only Word/Markdown reports are not final.
- Keep real passwords and personal configuration out of commits.

No existing local database is automatically migrated. Preserve it and test this version separately.
