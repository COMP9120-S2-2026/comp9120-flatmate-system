# Narrowed PR: repair compatibility, preserve the database

## Baseline

Reviewed main commit: 70e27bc. The root schema, triggers, sample data, queries, transaction examples, SQL tests, concurrency examples and housematch_cli.py are preserved unchanged.

This supersedes the earlier broad ten-table integration proposal. It does not assert that the database design needs replacing.

## Concrete mismatches repaired

| Existing code | Shared schema / required fix |
| --- | --- |
| member_a inserted address/property fields into room | Insert into property_characteristics and reference property_id from room |
| A/C queried room.suburb | Join property_characteristics |
| A listing insert omitted required fields | Supply listing_date, status and num_housemates explicitly |
| A/C used allocation_status and FILLED | Remove the nonexistent room field and use CLOSED |
| C expected tuple rows | Read named fields from the common dict_row connection |
| run.py init loaded old A-only SQL | Load the root shared schema and triggers |
| C attempted WITHDRAWN | Do not add a status; return an explicit unsupported-operation error |
| C used commit/rollback on an autocommit connection | Wrap the existing multi-step SQL workflow in an explicit transaction |

Acceptance follows Max's existing SQL transaction: accept the selected applicant, reject pending rivals, cancel confirmed bookings and slots, and close the listing. It introduces no new database rule.

## Removed from the previous proposal

- Pet-field renaming: the database keeps pet_friendly.
- Added status values, repeat-application behavior and conditional unique indexes.
- Automatic Default profiles and additional mandatory-participation/immutability triggers.
- New preference/search/booking Python service and rescheduling.
- Replacement of Max's grouped menu.

Application withdrawal cannot be implemented using a WITHDRAWN status without changing the existing schema. It is deliberately disabled, not silently reinterpreted as rejection or deletion.

## Remaining boundaries

- The original menu is preserved, including its unfinished options. A/C operations can be exercised through run.py; this is not a claim that every menu option works.
- The two entry points retain their existing configuration approaches; README explains how to target the same database.
- Original root SQL comments may refer to earlier numbered filenames; database/README.md provides the actual execution order.
- Old reports and nine-table/renamed-field documents still need team reconciliation. This code patch does not edit Google documents.
- Authentication, a web interface, rescheduling and database redesign are outside this PR.
- The broad version's 39-test claim no longer describes this revision. See the freshly generated ALIGNMENT_TEST_RESULTS.md.

Earlier implementations remain archived for contribution review. Test failures are checked on an isolated PostgreSQL cluster; no personal database is modified.
