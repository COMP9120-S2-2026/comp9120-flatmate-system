# Integrated smoke checks

Executed on 19 October 2026 using PostgreSQL 18.4 in a separate local test cluster. The user's normal database and personal configuration were not used.

| Check | Observed result |
| --- | --- |
| run.py init | Created the ten-table schema and triggers in a new empty database |
| run.py seed | Created 14 users, 10 properties, 12 rooms and 12 listings |
| run.py --user-id 1 profiles | Returned the automatically created Default profile |
| housematch_cli.py | Displayed users, accepted demo user 1, displayed the menu and exited normally |
| sql/90_pgadmin_queries.sql | Executed without errors; listed ten tables and ten open listings |

The pgAdmin query file was tested through PostgreSQL's command-line client, not by automating the pgAdmin interface. Menu startup was checked; individual workflow behavior is covered by the integration tests.

See ALIGNMENT_TEST_RESULTS.md for the separate 39-test automated run, including SQL transaction examples and concurrent sessions. These checks do not represent a production authentication or deployment audit.
