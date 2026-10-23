# HouseMatch module responsibilities and integration contract

Member A is the current user's assumed role. Replace A/B/C with real names together.
This file fixes interfaces so B and C can work without changing A's implemented tables.
The report contains labelled spaces for their design, code and test evidence.

| Owner | Implemented or reserved contribution |
| --- | --- |
| A | Room, Listing, advertiser CRUD, publishing transaction, integrity constraints, A state helper, A tests, A report content |
| B | RESERVED: named preference profiles, preferred suburbs, search, saves, viewing slots, bookings/cancellation, tests and report content |
| C | RESERVED: accounts/sessions, Application, apply/withdraw/review/accept/reject, full acceptance transaction, tests and report content |

## Shared assumptions for this version

- Property and Household stay merged into Room, following the current Week 9 model.
- `Room.suburb` is restored and `is_furnished` is one Boolean value.
- Each stored Room has at least one historical/current Listing; publishing inserts both in one transaction.
- One OPEN Listing per Room. CLOSED and FILLED listings remain as history.
- Room status is AVAILABLE or UNAVAILABLE. Closing an advertisement leaves its room AVAILABLE.
- The creator of a room's most recent Listing manages its details and future advertisements. Ownership transfers are out of scope. This assumption avoids adding a separate property-owner model.
- One User can perform both roles. CLI `--user-id` is demo identity selection, not authentication; C owns authentication/session design.
- Each User will have at least one PreferenceProfile. The minimal user scaffold permits testing A before B's tables exist; B/C must implement the registration/default-profile rule together.
- Viewing bookings retain cancellation history. A ViewingSlot can have many historical bookings, with at most one BOOKED booking at a time. This changes its old 0..1 total-history cardinality to 0..*.
- Date/time components become a single `viewing_at TIMESTAMPTZ`. Local display uses Australia/Sydney. The ViewingSlot key stays `(listing_id, viewing_at)`.
- Existing bookings are retained when a listing closes/fills; the advertiser can cancel them. New bookings/applications require OPEN. B and C must lock/recheck the listing.
- Empty preferred suburbs mean any suburb. Smoking/pet preference ANY means no filter.

## Member B schema and work to complete

Create `preference_profile` with PK `(user_id, profile_name)` and FK `user_id -> app_user(user_id)`;
fields `max_weekly_rent`, `desired_move_in_date`, `smoking_preference`, `pet_preference`.
Proposed preference values are ANY, ALLOWED and NOT_ALLOWED.

Create `preferred_suburb` with PK `(user_id, profile_name, preferred_suburb)` and ONE composite FK
`(user_id, profile_name) -> preference_profile(user_id, profile_name)`.

Create `saves` with PK `(user_id, listing_id)` and references to app_user and listing.
Unsave deletes this association. Do not silently add save history.

Create `viewing_slot` with PK `(listing_id, viewing_at)`, FK listing_id -> listing,
and status AVAILABLE/CANCELLED. The conceptual entity is weak, with viewing_at as its partial key.

Create `viewing_booking` with PK booking_id, FK user_id -> app_user, a composite FK
`(listing_id, viewing_at) -> viewing_slot(listing_id, viewing_at)`, booking_date and status BOOKED/CANCELLED.
Use a unique partial index on `(listing_id, viewing_at)` WHERE status='BOOKED'.
Do not add a full unique constraint on that pair: cancellation history must coexist with a later booking.

Implement profile CRUD, optional-suburb/lifestyle matching, save/unsave,
advertiser viewing-slot management, book/cancel and booking lists.
For booking, lock Room, then Listing, then ViewingSlot, check OPEN and slot AVAILABLE,
and insert one BOOKED row. Lock the same slot for cancellations/rebooking.
Return genuine results; the RESERVED Python file deliberately raises NotImplementedError.

Required evidence: composite FK rejection, duplicate save, two competing bookings,
cancel/rebook retaining history, closed-listing booking rejection, empty-suburb search,
lifestyle filtering, and default preference creation coordinated with C.

## Member C schema and work to complete

Extend the app_user contract instead of recreating it. Keep its user_id and name/email columns.
Implement account/session behaviour and coordinate first-profile creation with B.
Create application with PK application_id, FK user_id and listing_id,
application_date, status PENDING/ACCEPTED/REJECTED/WITHDRAWN, optional message.
Use partial unique indexes for one active PENDING/ACCEPTED application per user/listing,
and one ACCEPTED application per listing.

Implement apply, withdraw, applicant lists and accept/reject with ownership checks.
Acceptance must use ONE outer `with conn.transaction():` block:

1. Read application -> listing ID as a hint, then call A's `lock_owned_open_listing`.
   Lock order is Room -> Listing -> Application; re-check the application after locking it.
2. Require the selected application to be PENDING and to still target the locked listing.
3. Call A's `mark_filled_in_transaction` on the SAME connection. It does not commit.
4. Set the selected Application to ACCEPTED and all other PENDING applications to REJECTED.
5. Commit once. Any error must roll back all application, listing and room changes.

Do not present A's helper test as proof that the full acceptance workflow already exists.
Required evidence: apply/withdraw, ownership denial, duplicate active application,
two competing acceptances, full rollback after an injected failure, and rejected remaining applicants.

## Integration checklist

- Add B/C table definitions to their reserved SQL files and feature commands to the CLI.
- Use the same keys, field names, state values and lock order throughout.
- Replace each B/C report marker with the responsible member's text and actual evidence.
- Combine the A conceptual fragment with B/C entities into a final lecture-notation ER diagram.
- Review conditional functional dependencies before claiming BCNF for the merged Room design.
- Record tutor feedback, real names and actual individual contributions. Review AI acknowledgement.
- Run end-to-end tests before recording the final video. The current delivery is A plus integration scaffolding.
