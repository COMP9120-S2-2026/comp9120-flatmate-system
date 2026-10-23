# Member A verification results

Recorded verification on 14 October 2026 using PostgreSQL 18.4.

Tests run: 25; failures: 0; errors: 0; skipped: 0.

The database run covers A only. Full booking and application-acceptance workflows remain reserved for B/C.

```text
test_closed_history_allows_relisting (test_member_a.MemberATests.test_closed_history_allows_relisting) ... ok
test_closed_listing_cannot_be_edited (test_member_a.MemberATests.test_closed_listing_cannot_be_edited) ... ok
test_closing_advert_does_not_occupy_room (test_member_a.MemberATests.test_closing_advert_does_not_occupy_room) ... ok
test_competing_history_deletions_cannot_orphan_room (test_member_a.MemberATests.test_competing_history_deletions_cannot_orphan_room) ... ok
test_deleting_last_listing_rejected (test_member_a.MemberATests.test_deleting_last_listing_rejected) ... ok
test_demo_seed_has_eight_rooms_and_history (test_member_a.MemberATests.test_demo_seed_has_eight_rooms_and_history) ... ok
test_duplicate_open_listing_rejected_by_database (test_member_a.MemberATests.test_duplicate_open_listing_rejected_by_database) ... ok
test_fill_helper_cannot_commit_without_outer_transaction (test_member_a.MemberATests.test_fill_helper_cannot_commit_without_outer_transaction) ... ok
test_fill_helper_changes_roll_back_with_caller_failure (test_member_a.MemberATests.test_fill_helper_changes_roll_back_with_caller_failure) ... ok
test_fill_helper_updates_both_states (test_member_a.MemberATests.test_fill_helper_updates_both_states) ... ok
test_invalid_postcode_rejected (test_member_a.MemberATests.test_invalid_postcode_rejected) ... ok
test_invalid_rent_rolls_back_room (test_member_a.MemberATests.test_invalid_rent_rolls_back_room) ... ok
test_nan_rent_rejected (test_member_a.MemberATests.test_nan_rent_rejected) ... ok
test_negative_housemates_rejected (test_member_a.MemberATests.test_negative_housemates_rejected) ... ok
test_orphan_room_rejected_at_commit (test_member_a.MemberATests.test_orphan_room_rejected_at_commit) ... ok
test_parameterised_description_is_stored_as_text (test_member_a.MemberATests.test_parameterised_description_is_stored_as_text) ... ok
test_publish_room_and_listing (test_member_a.MemberATests.test_publish_room_and_listing) ... ok
test_room_cannot_be_unavailable_while_listing_open (test_member_a.MemberATests.test_room_cannot_be_unavailable_while_listing_open) ... ok
test_two_sessions_compete_to_relist (test_member_a.MemberATests.test_two_sessions_compete_to_relist) ... ok
test_unavailable_room_cannot_receive_open_listing (test_member_a.MemberATests.test_unavailable_room_cannot_receive_open_listing) ... ok
test_unknown_advertiser_rolls_back_room (test_member_a.MemberATests.test_unknown_advertiser_rolls_back_room) ... ok
test_update_open_listing (test_member_a.MemberATests.test_update_open_listing) ... ok
test_update_room_details (test_member_a.MemberATests.test_update_room_details) ... ok
test_wrong_advertiser_cannot_close (test_member_a.MemberATests.test_wrong_advertiser_cannot_close) ... ok
test_wrong_advertiser_cannot_relist (test_member_a.MemberATests.test_wrong_advertiser_cannot_relist) ... ok

----------------------------------------------------------------------
Ran 25 tests in 1.350s

OK
```
