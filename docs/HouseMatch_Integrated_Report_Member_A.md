# HouseMatch Group Project Report

Group 34 | Tutorial 26 | Submission date 25 October 2026

Member A is responsible for Room and Listing. Member B owns preferences, saved listings and viewings. Member C owns users and applications. Replace the role labels with the agreed member names before submission.

## Project Overview

HouseMatch supports shared-accommodation advertising and discovery through a PostgreSQL database and Python command-line prototype. Users can advertise rooms, search using named preferences, save listings, arrange private viewings and submit applications. Room details are separated from advertisement-specific rent, dates and status so that advertising history can be retained. The database supports integrity constraints and transactions for related changes. Member A's implemented module manages rooms and listings; the remaining modules and their report contributions are assigned to Members B and C.

## 1. Problem and Requirements (10%)

### 1.1 Problem and Motivation

Shared-accommodation searches involve room characteristics, advertised prices, availability, viewing appointments and applications. Separate or outdated records can cause conflicting reservations and inconsistent application outcomes. We use a relational database to connect these records and to validate related changes consistently.

### 1.2 Users and Stakeholders

Prospective flatmates need to compare rooms, save suitable advertisements, book viewings and track applications. Advertisers need to publish and update room listings, organise viewings and review applicants. One registered user may perform both roles. The prototype uses a command-line interface to demonstrate database behaviour.

### 1.3 Data Requirements

We record users, named preference profiles, preferred suburbs, rooms, listings, saves, viewing slots, bookings and applications. Room stores physical features, address and living-environment information. Listing stores advertised rent, availability date, listing date, status and its advertiser. Each preference profile is identified within its owning user. Each viewing slot is identified within a listing. Booking and application records retain their identifiers and statuses.

### 1.4 Business Rules and Scope

Every listing advertises one room and has one advertiser. A stored room has one or more historical/current listings, with at most one OPEN listing at a time. Rent must be positive and finite. Only OPEN listings receive new applications or viewing bookings. Each user/listing save pair is unique. Each user has at least one preference profile in the integrated system. A viewing slot may have several historical bookings but at most one BOOKED booking. Each user/listing pair has at most one active application, defined as PENDING or ACCEPTED. A listing has at most one ACCEPTED application. Acceptance fills the listing, makes its room unavailable and rejects the other pending applications in one transaction.

Property and Household information is stored in Room; individual household membership, payments, tenancy contracts, bonds, messaging and ownership transfers are outside scope. Closing an advertisement does not occupy its room. The latest listing creator manages that room. Cancelled bookings remain as history; existing bookings are retained after closing/filling until the advertiser cancels them.

### 1.5 Representative User Operations

Publish a room and its first advertisement, then update, close or relist it.

Find matching OPEN listings and save or remove them from a shortlist.

Book an available viewing, cancel it and view booking status.

Apply for a listing, withdraw a pending application and review applicants.

Accept one applicant while keeping all related records consistent.

## 2. Conceptual Design (ER Model) (20%)

### 2.1 Final ER Diagram

[A_ER_DIAGRAM]

Figure 1 shows Member A's conceptual contribution. Room participates in Advertises 1..*, and Listing participates 1..1. User participates in Creates 0..*, and Listing participates 1..1. Arrows point from constrained entities into relationship diamonds; thick lines express mandatory participation. Address is composite, keys are underlined and is_furnished is a single-valued attribute.

[MEMBER B TO COMPLETE: combine PreferenceProfile, preferred suburbs, Saves, ViewingSlot and ViewingBooking with this fragment. Use double rectangles and identifying relationships for weak entities, dashed underlining for partial keys, and a double ellipse only for preferred suburbs. Slot-to-booking participation is 0..* when cancellation history is retained.]

[MEMBER C TO COMPLETE: add complete User attributes and Application relationships. Produce the combined whole-system ER figure with B and confirm all participation constraints before final submission.]

### 2.2 Entities and Attributes

Room is a strong entity identified by room_id. Its physical and environment attributes are room_type, property_type, number_rooms, is_furnished, has_ensuite, car_spots, num_housemates, smoking_policy, pet_policy and description. The composite address contains street_number, street_name, suburb, state and postcode. allocation_status records whether the room is AVAILABLE or UNAVAILABLE. num_housemates is stored because individual household members are outside scope.

Listing is a strong entity identified by listing_id. weekly_rent and available_from describe one advertisement rather than the physical room. listing_date records when that advertisement was created. status distinguishes OPEN, CLOSED and FILLED. The advertiser and room are represented by relationships in the conceptual model and foreign keys in the logical model.

[MEMBER B TO COMPLETE: explain each preference, save, slot and booking attribute, including local identifiers and the decision to use one timestamp for a viewing.]

[MEMBER C TO COMPLETE: explain User and Application attributes, optional messages, identifiers and status domains.]

### 2.3 Relationships and Constraints

Advertises connects Room and Listing. Room's total participation ensures that every recorded room has an advertisement; historical advertisements remain after closing. Creates connects User and Listing and identifies the advertiser responsible for each listing. The one-OPEN-listing restriction is conditional on status and must be enforced separately from the historical 1..* cardinality.

[MEMBER B TO COMPLETE: explain profile ownership, multivalued suburbs, Saves, listing-owned viewings and booking relationships, including cancellation history.]

[MEMBER C TO COMPLETE: explain one applicant and one target listing per application and the conditional restrictions on active/accepted applications.]

### 2.4 Design Rationale and Assumptions

We retain Room and Listing separately because a room can be advertised repeatedly with different prices and dates. Property and Household remain merged into Room to follow the latest group scope. Shared physical property management and membership history are excluded. A room is first entered together with a listing, and the creator of its most recent listing manages subsequent details and advertisements. This permission assumption should be reviewed if ownership transfers are later introduced.

We add allocation_status to represent the documented acceptance outcome. Closing a listing alone does not change it. A finalisation helper changes both listing and room states but leaves transaction control and application updates to Member C. This version also adopts cancellation history for bookings and one timestamp for each viewing, as specified in HANDOFF.md.

[MEMBER B/C TO COMPLETE: record tutor feedback and add the rationale for their profile, booking, identity and application decisions.]

## 3. Logical Design and Normalisation (20%)

### 3.1 Relational Schema

Member A implements the following relations. PK denotes a primary key and FK a foreign key.

ROOM(room_id PK, room_type, property_type, number_rooms, is_furnished, has_ensuite, car_spots, num_housemates, smoking_policy, pet_policy, description, street_number, street_name, suburb, state, postcode, allocation_status).

LISTING(listing_id PK, room_id FK -> ROOM.room_id, creator_user_id FK -> APP_USER.user_id, weekly_rent, available_from, listing_date, status).

APP_USER(user_id PK, first_name, last_name, email UNIQUE, phone_num, bio) is an integration scaffold. Member C owns its extension and account/session behaviour. It permits testing A before B's preference tables are available; it does not yet enforce mandatory initial preference creation.

| Owner | Reserved relation | Proposed key or reference |
| --- | --- | --- |
| B | PREFERENCE_PROFILE | PK (user_id, profile_name); FK user_id -> APP_USER |
| B | PREFERRED_SUBURB | PK (user_id, profile_name, preferred_suburb); composite FK -> PREFERENCE_PROFILE |
| B | SAVES | PK (user_id, listing_id); FKs -> APP_USER and LISTING |
| B | VIEWING_SLOT | PK (listing_id, viewing_at); FK listing_id -> LISTING |
| B | VIEWING_BOOKING | PK booking_id; FK user_id -> APP_USER; composite FK -> VIEWING_SLOT |
| C | APPLICATION | PK application_id; FKs user_id -> APP_USER and listing_id -> LISTING |

[MEMBER B TO COMPLETE: add the full attributes, data types, candidate keys, foreign keys and constraints for the five B relations.]

[MEMBER C TO COMPLETE: finalise APP_USER and APPLICATION, including their candidate keys and partial uniqueness constraints. Insert the final whole-system relational diagram with B.]

### 3.2 Mapping from ER Model to Relations

Room and Listing each map to one relation because both have global identifiers. The composite address is flattened into atomic columns. Mandatory Listing participation in Advertises and Creates maps to NOT NULL foreign keys room_id and creator_user_id. Historical cardinality does not make room_id globally unique in Listing; a partial unique index restricts it only for OPEN rows.

[MEMBER B TO COMPLETE: demonstrate mapping the two weak entities, the multivalued preferred suburbs and the Saves association. Explain both composite foreign keys as complete tuples.]

[MEMBER C TO COMPLETE: explain Application mapping and account-key decisions.]

### 3.3 Functional Dependencies

For Room, room_id determines all other Room attributes. Address is not declared unique because several offered rooms can share a location. For Listing, listing_id determines room_id, creator_user_id, weekly_rent, available_from, listing_date and status. room_id does not determine listing_id or rent across advertising history. Similarly, creator_user_id does not determine a listing because one advertiser may create many.

[MEMBER B TO COMPLETE: list full functional dependencies for profile/suburb/save/slot/booking relations using the proposed composite keys.]

[MEMBER C TO COMPLETE: list User and Application dependencies and explain candidate keys. Distinguish conditional active-row uniqueness from unconditional functional dependencies.]

### 3.4 Normalisation Analysis

Room and Listing use atomic values and therefore satisfy 1NF. Each has a single-column primary key, so no non-key attribute depends on only part of that key. Under the declared record-level dependencies, all non-trivial determinants in these two relations are keys, giving BCNF and hence 3NF. We do not infer a global dependency from room_id to a listing's price because historical advertisements can differ.

The Room result is conditional on the scope assumption that property/environment values are maintained as attributes of an offered-room record. If the domain instead requires one authoritative property record whose address determines property_type, number_rooms or parking for every room at that location, those additional dependencies create repeated facts and potential update anomalies. The appropriate refinement would restore a separate Property relation. We therefore document this trade-off rather than asserting that merging Property always produces BCNF.

[MEMBER B/C TO COMPLETE: analyse their actual implemented relations, state the normal form and justify any decomposition. Review the Room scope assumption with tutor feedback.]

### 3.5 Final Design Decisions and Trade-offs

Separate Listing history preserves advertisement-specific prices and dates. A surrogate room identifier allows multiple rooms at one address. Restoring suburb makes address data and matching queries consistent. Explicit room availability supports acceptance without adding occupancy history. Keeping environment fields in Room simplifies the agreed prototype but can repeat property facts; the assumption and possible future decomposition are stated above. Status-based uniqueness uses a partial index rather than forbidding all historical listings.

[MEMBER B TO COMPLETE: explain the timestamp simplification, composite keys and retained booking history.]

[MEMBER C TO COMPLETE: explain identity keys, application history and authentication choices.]

## 4. SQL, Integrity and Transactions (20%)

### 4.1 PostgreSQL Implementation

Member A's implementation uses PostgreSQL and Python with Psycopg. sql/00_user_contract.sql creates the shared user scaffold; sql/10_member_a.sql creates Room, Listing, indexes and integrity triggers. The CLI init command creates these objects in an empty schema without resetting an existing database. The seed command supplies three synthetic users, eight rooms and nine listings, including one closed historical advertisement. Sample names, addresses and rents are demonstration fixtures.

The CLI implements publishing, viewing details, advertiser listing lists, room-detail updates, advertised-term updates, closing and relisting. --user-id selects a demo actor; Member C will supply the account/session layer. Installation, environment variables and commands are documented in README.md. A's real PostgreSQL verification result is summarised in Section 4.6.

[MEMBER B/C TO COMPLETE: describe their implemented tables, setup order, additional fixtures and executable CLI commands.]

### 4.2 Representative SQL Operations

The following implemented read joins room features to advertisement information and lists one advertiser's current offers. Runtime values are passed as parameters, not concatenated into SQL.

```sql
SELECT l.listing_id, r.room_type, r.suburb,
       l.weekly_rent, l.available_from, l.status
FROM listing l JOIN room r USING (room_id)
WHERE l.creator_user_id = %s AND l.status = 'OPEN'
ORDER BY l.weekly_rent, l.listing_id;
```

Publishing performs two INSERT operations in one transaction, first returning room_id and then referencing it in Listing. Updating an open advertisement changes weekly_rent and available_from after verifying the actor and current state. Closing changes only Listing.status to CLOSED. Relisting inserts another advertisement linked to the same available room and preserves the old advertisement.

[MEMBER B TO COMPLETE: add preference/lifestyle matching, saved-listing retrieval, available-viewing queries and booking/cancellation SQL with actual outputs.]

[MEMBER C TO COMPLETE: add applicant queries, pending-application aggregation and application modification SQL with actual outputs.]

### 4.3 Integrity Constraints

Primary keys identify Room and Listing. NOT NULL foreign keys prevent advertisements without a valid room or advertiser; deletion is restricted while references exist. Domain checks require positive finite rent, positive number_rooms, non-negative housemate/parking counts, valid state values and four-digit postcodes. Furnishing and ensuite availability are single Boolean values.

```sql
CREATE UNIQUE INDEX one_open_listing_per_room
ON listing(room_id) WHERE status = 'OPEN';
```

A trigger checks that an OPEN listing references an AVAILABLE room. Another rejects making a room UNAVAILABLE while its listing remains OPEN. Deferred constraint triggers verify at commit that every stored room retains at least one listing, allowing the room and its first advertisement to be inserted within one transaction. These checks supplement the foreign keys; a foreign key alone cannot require a parent Room to have a child Listing.

Advertiser permissions are enforced in Python using the supplied actor identifier. They are not a database row-security or login mechanism. The listing creator manages its advertisement; the most recent listing creator manages the room. Member C must supply trusted identity when integrating sessions.

[MEMBER B TO COMPLETE: prove duplicate-save rejection, composite FK validity, mandatory profile handling and one active booking per slot.]

[MEMBER C TO COMPLETE: prove application-status and active/accepted uniqueness constraints.]

### 4.4 Transaction Scenario

Member A's completed transaction publishes a new room and its first listing. The transaction begins before INSERT Room, uses the returned identifier in INSERT Listing and commits after both succeed. The deferred room-participation constraint is checked at that commit. If rent is invalid or the advertiser does not exist, both inserts roll back, preventing an orphan room.

The cross-module acceptance operation remains Member C's contribution. A supplies lock_owned_open_listing and mark_filled_in_transaction. The latter changes Listing to FILLED and Room to UNAVAILABLE on the caller's connection and never commits independently. C must accept the selected pending Application and reject the remaining pending Applications in the same outer transaction.

[MEMBER C TO COMPLETE: insert the full acceptance implementation, transaction boundary and application-state results. A's two-state helper is not evidence that the complete acceptance workflow is implemented.]

### 4.5 Failure and Concurrency Reasoning

Psycopg transaction contexts commit successful operations and roll back on exceptions. The implementation uses autocommit connections for independent reads and explicit contexts for multi-step writes. A simulated failure after the fill helper verifies that both room and listing changes roll back with the caller's transaction.

Relisting locks the Room row before inspecting history and inserting a new Listing. Advertiser changes use the same Room-then-Listing order and re-check ownership, availability and OPEN status after locking. A real two-connection test shows one concurrent relisting succeeds and the other is rejected; the partial unique index supplies an additional database safeguard. Default READ COMMITTED isolation and these row locks are sufficient for the tested A operations. Full acceptance and booking concurrency require their own integration tests.

[MEMBER B TO COMPLETE: document competing booking and cancellation/rebooking behaviour. Use Room -> Listing -> ViewingSlot before changing bookings.]

[MEMBER C TO COMPLETE: test competing acceptances using Room -> Listing -> Application; show rollback after an application update fails.]

### 4.6 Testing and Evidence of Correctness

On 14 October 2026, 25 A-module integration tests ran against a separate PostgreSQL 18.4 instance. All 25 passed, with zero failures, errors or skipped tests. Each run creates a unique test schema and removes only that schema. Detailed test names and results are supplied in TEST_RESULTS.md and test_results.json. Nine documented CLI commands also passed a separate smoke run recorded in cli_smoke_results.json.

| Test group | Observed result |
| --- | --- |
| Publish and seed | Room plus first Listing persisted; seed produced 8 rooms and 9 listings |
| Invalid rent and advertiser | Zero/NaN rent and unknown advertiser rejected; no orphan room remained |
| Domain validation | Negative housemates and malformed postcode rejected |
| Listing lifecycle | Closing kept the room AVAILABLE; relisting retained closed history |
| Advertiser checks | Wrong advertiser could not close or relist; valid updates succeeded |
| Database uniqueness | Direct duplicate OPEN listing rejected |
| Mandatory room participation | Standalone room and deletion of its last listing rejected at commit |
| Concurrent history removal | Only one of two simultaneous historical-listing deletions committed; the room retained a listing |
| Availability consistency | OPEN advertisement of an unavailable room and premature occupancy rejected |
| Fill helper rollback | Both state updates reverted after a simulated later failure |
| Concurrent relisting | Exactly one of two independent sessions created the new OPEN listing |
| SQL parameter handling | SQL-like description was stored as ordinary text |

[MEMBER B TO COMPLETE: add actual preference, save and viewing test evidence.]

[MEMBER C TO COMPLETE: add actual account and complete application/acceptance evidence.]

[GROUP TO COMPLETE: run the combined CLI workflows, record the tutor feedback addressed and select a concise demonstration for the video.]

## References

University of Sydney. COMP9120 Group Project Brief and report template, Semester 2 2026.

University of Sydney. L2 Conceptual Modelling and L3 Relational Model lecture materials, COMP9120.

Group 34. COMP9120 Week 9 Check In and ERD Current, reviewed 14 October 2026.

PostgreSQL Global Development Group. PostgreSQL documentation, Partial Indexes. https://www.postgresql.org/docs/current/indexes-partial.html

Psycopg project. Psycopg 3 documentation, Transactions Management. https://www.psycopg.org/psycopg3/docs/basic/transactions.html

[MEMBER B/C TO COMPLETE: add sources actually used for their contributions.]

## Appendix

| Member | Contribution to complete or verify |
| --- | --- |
| A | Room/Listing design, schema, normalisation discussion, advertiser CLI, integrity checks, publishing transaction, state helper and recorded tests |
| B | Preference profiles, suburbs, search, saves, viewing slots/bookings, corresponding SQL/tests/report sections |
| C | Accounts, Application, full acceptance transaction, corresponding SQL/tests/report sections |

HANDOFF.md fixes proposed peer keys, states, cancellation semantics and locking order. B/C sections must be replaced by the responsible members' work and actual test results. Real names, student IDs and contributions should be agreed before preparing the official contribution statement.

AI acknowledgement for group review: OpenAI Codex assisted with integration, Member A code, test construction and report wording. The group must review the design and code, identify its actual use of AI, and be able to explain all submitted work.
