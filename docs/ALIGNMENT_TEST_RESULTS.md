# Integrated verification results

Recorded verification on 19 October 2026 using PostgreSQL 18.4.

Tests run: 26; failures: 0; errors: 0; skipped: 0.

The run covers A/C compatibility with the unchanged shared schema, original SQL tests, rollback and competing acceptances. No new B features or database rules are included.

```text
test_accept_failure_rolls_back_all_updates (test_integration.IntegrationTests.test_accept_failure_rolls_back_all_updates) ... ok
test_accept_matches_original_sql_workflow (test_integration.IntegrationTests.test_accept_matches_original_sql_workflow) ... ok
test_accept_owner_check (test_integration.IntegrationTests.test_accept_owner_check) ... ok
test_active_listing_guard_includes_paused (test_integration.IntegrationTests.test_active_listing_guard_includes_paused) ... ok
test_application_queries_use_property_join_and_dictionary_rows (test_integration.IntegrationTests.test_application_queries_use_property_join_and_dictionary_rows) ... ok
test_application_self_and_closed_guards (test_integration.IntegrationTests.test_application_self_and_closed_guards) ... ok
test_cli_list_and_application_commands (test_integration.IntegrationTests.test_cli_list_and_application_commands) ... ok
test_existing_property_room (test_integration.IntegrationTests.test_existing_property_room) ... ok
test_original_grouped_menu_and_profile_view (test_integration.IntegrationTests.test_original_grouped_menu_and_profile_view) ... ok
test_original_max_sql_suite (test_integration.IntegrationTests.test_original_max_sql_suite) ... ok
test_original_schema_domains_and_no_new_indexes (test_integration.IntegrationTests.test_original_schema_domains_and_no_new_indexes) ... ok
test_publish_failure_rolls_back_property_room (test_integration.IntegrationTests.test_publish_failure_rolls_back_property_room) ... ok
test_publish_supplies_required_listing_fields (test_integration.IntegrationTests.test_publish_supplies_required_listing_fields) ... ok
test_publish_unknown_user_rolls_back (test_integration.IntegrationTests.test_publish_unknown_user_rolls_back) ... ok
test_reject_and_original_duplicate_rule (test_integration.IntegrationTests.test_reject_and_original_duplicate_rule) ... ok
test_room_listing_owner_checks (test_integration.IntegrationTests.test_room_listing_owner_checks) ... ok
test_seed_original_queries_and_transaction_examples (test_integration.IntegrationTests.test_seed_original_queries_and_transaction_examples) ... ok
test_two_sessions_accept_one_application (test_integration.IntegrationTests.test_two_sessions_accept_one_application) ... ok
test_update_close_relist_without_allocation_status (test_integration.IntegrationTests.test_update_close_relist_without_allocation_status) ... ok
test_withdraw_is_explicitly_unsupported (test_integration.IntegrationTests.test_withdraw_is_explicitly_unsupported) ... ok
test_environment_fallback (test_local_config.LocalConfigTests.test_environment_fallback) ... ok
test_explicit_url_overrides_config (test_local_config.LocalConfigTests.test_explicit_url_overrides_config) ... ok
test_invalid_json_rejected_without_showing_contents (test_local_config.LocalConfigTests.test_invalid_json_rejected_without_showing_contents) ... ok
test_invalid_port_rejected (test_local_config.LocalConfigTests.test_invalid_port_rejected) ... ok
test_local_config_overrides_environment (test_local_config.LocalConfigTests.test_local_config_overrides_environment) ... ok
test_placeholder_rejected (test_local_config.LocalConfigTests.test_placeholder_rejected) ... ok

----------------------------------------------------------------------
Ran 26 tests in 1.593s

OK
```
