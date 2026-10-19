# Ten-table schema alignment

## Source and decision

The group approved the ten-table relational schema on page 7 of the [current report](https://docs.google.com/document/d/1HtJnRaINpxAydE0r4OUgaTFSml7XnQVv/edit). The [separate schema spreadsheet](https://docs.google.com/spreadsheets/d/1OsY66uIYIXDi1qyfPW_yb5TVRlvPH9lW8nZC_MI5NA0/edit) still showed nine tables when reviewed and is not the implementation authority for this baseline. Google documents were not edited.

## Mapping

| Report entity | SQL table / important attributes |
| --- | --- |
| USER | app_user (avoids the SQL USER keyword) |
| PREFERENCE_PROFILE | preference_profile; composite key user_id, profile_name; pet_preference |
| PREFERRED_SUBURB | preferred_suburb; composite foreign key to profile |
| PROPERTY_CHARACTERISTICS | property_characteristics; property_id; pet_policy |
| ROOM | room; property_id foreign key; num_roommates |
| LISTING | listing; room_id and creator_user_id; num_housemates |
| SAVES | saves; user_id, listing_id composite key; preference_rank |
| APPLICATION | application; independent application_id |
| VIEWING_SLOT | viewing_slot; listing_id, viewing_timestamp composite key |
| VIEWING_BOOKING | viewing_booking; booking_id; composite foreign key to slot |

The automated column test checks all ten tables against the report. Property attributes live in PROPERTY_CHARACTERISTICS, not duplicated in ROOM. Report ERD/prose and the separate nine-table sheet need an explicit update or explanation of this decomposition.

## Explicit implementation decisions

- Listing statuses: OPEN, PAUSED, CLOSED. Acceptance closes the listing; there is no FILLED status or additional occupancy column.
- Applications: PENDING, ACCEPTED, REJECTED, WITHDRAWN. A user may submit again after rejection/withdrawal, but cannot have multiple active applications for one listing.
- Acceptance is one transaction: accept the selected pending application, reject rivals, cancel bookings and viewing slots, close the listing. Failure rolls back every step.
- A booking may move only to an available future slot on the same listing, retaining its booking ID, user and booking date. Cancellation preserves history. Partial unique indexes allow historical bookings but only one confirmed booking per slot and per user/listing.
- Every inserted user receives a Default preference profile. A deferred constraint prevents removal of their last profile.
- Publishing creates a room and its initial listing atomically. Deferred checks prevent committed rooms without listings.
- A property may be shared by multiple rooms, subject to total_rooms capacity. Shared property edits require consistent advertiser ownership across affected rooms.
- pet_policy is Boolean: true permits pets. pet_preference true requires pets to be permitted; false/null adds no pet filter. This does not express a preference for a pet-free household; confirm this interpretation in the report.
- An empty preferred-suburb set means any suburb. Outdoor-only smoking preference also accepts no-smoking properties.
- Demo actor selection is not authentication. Ownership checks in services do not replace production access control.

## Verification and deployment limits

See ALIGNMENT_TEST_RESULTS.md for the actual integrated test run. Tests cover schema columns, constraints, SQL integrity scenarios, rollback and competing transactions. They do not certify the final report, authentication, or every possible direct-SQL lock ordering.

Use a new empty database. This branch does not convert old databases in place or modify personal config.json. Root transaction examples write demonstration data and should only be run on disposable databases.
