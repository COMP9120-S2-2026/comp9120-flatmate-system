# Integrated verification results

Recorded verification on 19 October 2026 using PostgreSQL 18.4.

Tests run: 39; failures: 0; errors: 0; skipped: 0.

The run covers the canonical ten-table schema, A/B/C service integration, rollback, competing acceptances and bookings.

```text
test_accept_atomic_and_reject_others (test_integration.IntegrationTests.test_accept_atomic_and_reject_others) ... ok
test_accept_cancels_existing_booking (test_integration.IntegrationTests.test_accept_cancels_existing_booking) ... ok
test_accept_owner_check (test_integration.IntegrationTests.test_accept_owner_check) ... ok
test_accept_rolls_back_on_injected_failure (test_integration.IntegrationTests.test_accept_rolls_back_on_injected_failure) ... ok
test_advertiser_ownership (test_integration.IntegrationTests.test_advertiser_ownership) ... ok
test_application_dictionary_results (test_integration.IntegrationTests.test_application_dictionary_results) ... ok
test_application_self_and_closed_rejected (test_integration.IntegrationTests.test_application_self_and_closed_rejected) ... ok
test_cancel_and_rebook_retains_history (test_integration.IntegrationTests.test_cancel_and_rebook_retains_history) ... ok
test_cannot_accept_without_closing_listing (test_integration.IntegrationTests.test_cannot_accept_without_closing_listing) ... ok
test_close_then_relist (test_integration.IntegrationTests.test_close_then_relist) ... ok
test_closed_listing_blocks_new_booking (test_integration.IntegrationTests.test_closed_listing_blocks_new_booking) ... ok
test_default_profile_and_last_profile_rule (test_integration.IntegrationTests.test_default_profile_and_last_profile_rule) ... ok
test_delete_profile_with_suburbs_and_last_profile_rollback (test_integration.IntegrationTests.test_delete_profile_with_suburbs_and_last_profile_rollback) ... ok
test_duplicate_active_listing (test_integration.IntegrationTests.test_duplicate_active_listing) ... ok
test_exact_report_columns (test_integration.IntegrationTests.test_exact_report_columns) ... ok
test_existing_property_used_without_duplication (test_integration.IntegrationTests.test_existing_property_used_without_duplication) ... ok
test_invalid_rent_rolls_back_room (test_integration.IntegrationTests.test_invalid_rent_rolls_back_room) ... ok
test_invalid_room_domain (test_integration.IntegrationTests.test_invalid_room_domain) ... ok
test_max_sql_suite (test_integration.IntegrationTests.test_max_sql_suite) ... ok
test_profile_composite_fk (test_integration.IntegrationTests.test_profile_composite_fk) ... ok
test_profile_search_filters (test_integration.IntegrationTests.test_profile_search_filters) ... ok
test_publish_and_update (test_integration.IntegrationTests.test_publish_and_update) ... ok
test_reschedule_retains_identity_and_releases_slot (test_integration.IntegrationTests.test_reschedule_retains_identity_and_releases_slot) ... ok
test_room_mandatory_listing (test_integration.IntegrationTests.test_room_mandatory_listing) ... ok
test_save_duplicate_and_unsave (test_integration.IntegrationTests.test_save_duplicate_and_unsave) ... ok
test_seed_and_queries (test_integration.IntegrationTests.test_seed_and_queries) ... ok
test_shared_property_edit_requires_consistent_owner (test_integration.IntegrationTests.test_shared_property_edit_requires_consistent_owner) ... ok
test_shared_property_room_capacity (test_integration.IntegrationTests.test_shared_property_room_capacity) ... ok
test_sql_transaction_examples (test_integration.IntegrationTests.test_sql_transaction_examples) ... ok
test_two_sessions_compete_to_accept (test_integration.IntegrationTests.test_two_sessions_compete_to_accept) ... ok
test_two_sessions_compete_to_book (test_integration.IntegrationTests.test_two_sessions_compete_to_book) ... ok
test_unknown_advertiser_rollback (test_integration.IntegrationTests.test_unknown_advertiser_rollback) ... ok
test_withdraw_then_reapply (test_integration.IntegrationTests.test_withdraw_then_reapply) ... ok
test_environment_fallback (test_local_config.LocalConfigTests.test_environment_fallback) ... ok
test_explicit_url_overrides_config (test_local_config.LocalConfigTests.test_explicit_url_overrides_config) ... ok
test_invalid_json_rejected_without_showing_contents (test_local_config.LocalConfigTests.test_invalid_json_rejected_without_showing_contents) ... ok
test_invalid_port_rejected (test_local_config.LocalConfigTests.test_invalid_port_rejected) ... ok
test_local_config_overrides_environment (test_local_config.LocalConfigTests.test_local_config_overrides_environment) ... ok
test_placeholder_rejected (test_local_config.LocalConfigTests.test_placeholder_rejected) ... ok

----------------------------------------------------------------------
Ran 39 tests in 2.270s

OK
```
