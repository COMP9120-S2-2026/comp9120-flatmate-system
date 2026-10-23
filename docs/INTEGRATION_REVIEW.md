# Submission candidate review — 23 October 2026

Code tested: b87787a (includes merge 38c249b, clean fc4531e and main 865f265).
Database: PostgreSQL 16.15. No shared branches changed during local preparation.

## Automated verification

33 Python tests passed with zero failures, errors or skips. One invokes the original 51-case SQL suite. Details: ALIGNMENT_TEST_RESULTS.md. Restored grouped CLI success, full rollback, competing acceptance, profile/search/save, booking and application paths are covered. Five manual SQL concurrency scenarios remain unexecuted as separate manual scenarios.

## John’s interactive check

Observed from the terminal transcripts John supplied, using an isolated seeded demo database:

- User 7 selected Near Uni and found listing 1, Glebe, $430.
- Saving an already saved listing reported the duplicate without creating another entry.
- Existing saved listings, viewings and applications displayed.
- Owner 1 accepted Emily for listing 8 and rejected Grace for listing 2.
- John cancelled a rejection confirmation for Mia; her application remained PENDING.
- Owner 1 then accepted Mia for listing 1: Mia became ACCEPTED; Jack and Isla became REJECTED; Lucas on listing 2 remained PENDING.
- Switching back to user 7 showed the listing 1 viewing CANCELLED.
- Re-selecting Near Uni and searching returned no matches; listing 1 no longer appeared.

These observations verify the visible success path; rollback and concurrency evidence comes from the automated suite, not this manual session. Direct slot/listing state assertions are in the automated tests.

## Additional advertiser CLI check

Executed through run.py in a different fresh disposable database, leaving John's demo data intact:

- Initialisation and seed completed.
- Owner 1 published a new room/listing at $360, verified by show.
- User 2's attempt to change its rent was rejected; rent remained $360.
- Owner 1 changed rent to $375 and availability to 5 November.
- Room description change was visible through show.
- Closing changed status to CLOSED and removed it from the OPEN list.
- Relisting created a new OPEN listing for the same room at $380.

Command outputs: advertiser_cli_results.json. This check used a room with no bookings; it does not establish manual-close viewing cleanup, which is not implemented. Acceptance provides that cleanup.

## Review boundaries

The grouped menu and four shared SQL files are unchanged from clean. Advertiser services are retained from main. No withdrawal, rescheduling, repeat applications, household or occupancy extensions were introduced. The two interfaces and their configuration remain separate as documented in README.

Pending: team review of the candidate, final submission documents, and a decision to publish the independent branch/PR. This record is not approval to merge main.
