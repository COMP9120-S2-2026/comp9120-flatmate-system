# Integration candidate handoff

Baseline: clean `fc4531e` (restored PR #5); compatible main `865f265`.

- Preserve the clean grouped CLI and all four shared SQL files unchanged.
- Restore main's advertiser/service interface, queries, tests, examples and setup files.
- Adapt the old profile/menu test to the active-profile argument.
- Add tests against the actual restored grouped CLI, including full rollback and concurrent acceptance.
- See README for both entry points, demo identities, setup and limitations.
- Historical evidence is not current evidence; use ALIGNMENT_TEST_RESULTS.md.
- No shared branch has been updated by the local integration. Team review is required before merging into main.
