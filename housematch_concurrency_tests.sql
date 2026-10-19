-- =====================================================================
-- HouseMatch - Manual Concurrency Tests (updated for Triggers 1-10)
-- COMP9120 Group Project
-- =====================================================================
-- FIVE TWO-SESSION TESTS
--   F01  Trigger 1:  two applications accepted for the same listing
--   F02  Trigger 3:  two users book the same viewing slot
--   F03  Trigger 6:  two active listings created for the same room
--   F04  Trigger 7:  two rooms added with only one space remaining
--   F05  Trigger 10: one user books two slots for the same listing
--
-- Triggers 8 (reducing total_rooms) and 9 (applying to your own listing)
-- are covered by the automated tests; they do not require two sessions.
--
-- BEFORE STARTING
--   * Run the latest schema, all 10 triggers, and (optionally) sample data.
--   * Open TWO separate pgAdmin Query Tool connections to housematch.
--   * In each Query Tool run: SELECT pg_backend_pid();
--     The two numbers must differ.
--   * Run the SETUP section ONCE in Session A. It COMMITs the fixtures.
--   * For EACH test: run Session A's BEGIN + statement; then run
--     Session B's BEGIN + statement. Session B should wait.
--     While B waits, COMMIT in A. B should then receive the expected
--     error. ROLLBACK in B, then run the verification query.
--   * Run tests IN ORDER: F01, F02, F03, F04, F05.
--   * At the end, run the commented CLEANUP section once.
--
-- IMPORTANT
--   The setup below is executable; test steps and cleanup are COMMENTED
--   so that running this whole file cannot accidentally run all tests.
--   Copy each commented step into its designated Query Tool and remove
--   the leading '-- ' from each SQL line before executing it.
--   Never COMMIT in Session B after its expected error: use ROLLBACK.
--   The tests assume READ COMMITTED isolation, explicitly selected below.
--   No new tables are created; only dedicated test rows are inserted.
-- =====================================================================

-- ---------------------------------------------------------------------
-- SETUP: run this section ONCE, in Session A.
-- ---------------------------------------------------------------------
BEGIN;

DO $concurrency_setup$
DECLARE
    v_owner INTEGER;
    v_a INTEGER;
    v_b INTEGER;
    v_property_existing INTEGER;
    v_property_capacity INTEGER;
    v_app_room INTEGER;
    v_view_room INTEGER;
    v_active_room INTEGER;
    v_second_view_room INTEGER;
    v_app_listing INTEGER;
    v_view_listing INTEGER;
    v_second_view_listing INTEGER;
    v_app_a INTEGER;
    v_app_b INTEGER;
BEGIN
    IF EXISTS (
        SELECT 1 FROM app_user
        WHERE email IN (
            'hm_concurrency_owner@example.invalid',
            'hm_concurrency_a@example.invalid',
            'hm_concurrency_b@example.invalid'
        )
    ) OR EXISTS (
        SELECT 1 FROM property_characteristics
        WHERE street_name = 'HouseMatch Concurrency Test Street'
          AND suburb = 'Testville'
    ) THEN
        RAISE EXCEPTION
            'Concurrency fixtures already exist. Run the CLEANUP section before setup.';
    END IF;

    -- Three dedicated users (owner and two applicants/viewers).
    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Concurrency', 'Owner', 'hm_concurrency_owner@example.invalid')
    RETURNING user_id INTO v_owner;

    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Concurrency', 'ApplicantA', 'hm_concurrency_a@example.invalid')
    RETURNING user_id INTO v_a;

    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Concurrency', 'ApplicantB', 'hm_concurrency_b@example.invalid')
    RETURNING user_id INTO v_b;

    -- Property 1: full (2/2 rooms), for the original F01 and F02 tests.
    INSERT INTO property_characteristics (
        street_number, street_name, suburb, state, postcode, unit_number,
        property_type, total_rooms, car_spots, smoking_policy, pet_friendly
    )
    VALUES (
        '999', 'HouseMatch Concurrency Test Street', 'Testville',
        'NSW', '2000', NULL, 'House', 2, 0, 'No smoking', FALSE
    )
    RETURNING property_id INTO v_property_existing;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES (
        'Private', 0, TRUE, FALSE,
        'Concurrency acceptance test room', v_property_existing
    )
    RETURNING room_id INTO v_app_room;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES (
        'Private', 0, TRUE, FALSE,
        'Concurrency same-slot booking room', v_property_existing
    )
    RETURNING room_id INTO v_view_room;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (
        v_app_room, v_owner, 400, CURRENT_DATE + 30,
        CURRENT_DATE, 'OPEN', 1
    )
    RETURNING listing_id INTO v_app_listing;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (
        v_view_room, v_owner, 420, CURRENT_DATE + 30,
        CURRENT_DATE, 'OPEN', 1
    )
    RETURNING listing_id INTO v_view_listing;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_a, v_app_listing)
    RETURNING application_id INTO v_app_a;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_b, v_app_listing)
    RETURNING application_id INTO v_app_b;

    INSERT INTO viewing_slot (listing_id, viewing_timestamp, status)
    VALUES (
        v_view_listing,
        CURRENT_DATE + 30 + TIME '10:00:00',
        'AVAILABLE'
    );

    -- Property 2: capacity 3, but only 2 rooms initially.
    --   Room A has NO listing (for F03).
    --   Room B has a listing with TWO slots (for F05).
    --   One free room space remains (for F04).
    INSERT INTO property_characteristics (
        street_number, street_name, suburb, state, postcode, unit_number,
        property_type, total_rooms, car_spots, smoking_policy, pet_friendly
    )
    VALUES (
        '998', 'HouseMatch Concurrency Test Street', 'Testville',
        'NSW', '2000', NULL, 'House', 3, 0, 'No smoking', FALSE
    )
    RETURNING property_id INTO v_property_capacity;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES (
        'Private', 0, TRUE, FALSE,
        'Concurrency active-listing test room', v_property_capacity
    )
    RETURNING room_id INTO v_active_room;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES (
        'Private', 0, TRUE, FALSE,
        'Concurrency one-user-two-slots room', v_property_capacity
    )
    RETURNING room_id INTO v_second_view_room;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (
        v_second_view_room, v_owner, 440, CURRENT_DATE + 30,
        CURRENT_DATE, 'OPEN', 1
    )
    RETURNING listing_id INTO v_second_view_listing;

    INSERT INTO viewing_slot (listing_id, viewing_timestamp, status)
    VALUES
        (v_second_view_listing, CURRENT_DATE + 30 + TIME '11:00:00', 'AVAILABLE'),
        (v_second_view_listing, CURRENT_DATE + 30 + TIME '12:00:00', 'AVAILABLE');

    RAISE NOTICE 'F01: listing %, application A %, application B %',
        v_app_listing, v_app_a, v_app_b;
    RAISE NOTICE 'F02: listing %, user A %, user B %, slot 10:00',
        v_view_listing, v_a, v_b;
    RAISE NOTICE 'F03: room % (initially no listing)', v_active_room;
    RAISE NOTICE 'F04: property % (total_rooms=3; initially 2 rooms)',
        v_property_capacity;
    RAISE NOTICE 'F05: listing %, user A %, slots 11:00 and 12:00',
        v_second_view_listing, v_a;
END;
$concurrency_setup$;

COMMIT;

-- Optional lookup to confirm the dedicated fixtures.
SELECT
    p.street_number,
    p.property_id,
    p.total_rooms,
    (SELECT COUNT(*) FROM room AS r2
     WHERE r2.property_id = p.property_id) AS current_room_count,
    r.room_id,
    r.description AS test_purpose,
    l.listing_id,
    l.status AS listing_status
FROM property_characteristics AS p
JOIN room AS r ON r.property_id = p.property_id
LEFT JOIN listing AS l ON l.room_id = r.room_id
WHERE p.street_name = 'HouseMatch Concurrency Test Street'
  AND p.suburb = 'Testville'
ORDER BY p.street_number DESC, r.room_id;

-- =====================================================================
-- F01: TWO SESSIONS ACCEPT DIFFERENT APPLICATIONS FOR THE SAME LISTING
-- Tests Trigger 1: enforce_one_accepted_application
-- =====================================================================
-- SESSION A: execute BEGIN and UPDATE. Do NOT commit yet.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- UPDATE application AS a
-- SET status = 'ACCEPTED'
-- FROM app_user AS u, listing AS l, room AS r
-- WHERE a.user_id = u.user_id
--   AND a.listing_id = l.listing_id
--   AND l.room_id = r.room_id
--   AND u.email = 'hm_concurrency_a@example.invalid'
--   AND r.description = 'Concurrency acceptance test room';
--
-- SESSION B: execute BEGIN and UPDATE in the OTHER Query Tool.
-- The UPDATE should wait for Session A's listing lock.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- UPDATE application AS a
-- SET status = 'ACCEPTED'
-- FROM app_user AS u, listing AS l, room AS r
-- WHERE a.user_id = u.user_id
--   AND a.listing_id = l.listing_id
--   AND l.room_id = r.room_id
--   AND u.email = 'hm_concurrency_b@example.invalid'
--   AND r.description = 'Concurrency acceptance test room';
--
-- SESSION A: COMMIT;
-- SESSION B: expect "This listing already has an accepted application".
-- SESSION B: ROLLBACK;
--
-- VERIFY (run in either session): accepted_count should be 1 of 2.
-- SELECT COUNT(*) AS total_applications,
--        COUNT(*) FILTER (WHERE a.status = 'ACCEPTED') AS accepted_count
-- FROM application AS a
-- JOIN listing AS l ON l.listing_id = a.listing_id
-- JOIN room AS r ON r.room_id = l.room_id
-- WHERE r.description = 'Concurrency acceptance test room';

-- =====================================================================
-- F02: TWO USERS BOOK THE SAME VIEWING SLOT
-- Tests Trigger 3: enforce_available_viewing_slot
-- =====================================================================
-- SESSION A: book the 10:00 slot; leave transaction open.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
-- VALUES (
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_a@example.invalid'),
--     (SELECT l.listing_id FROM listing AS l
--      JOIN room AS r ON r.room_id = l.room_id
--      WHERE r.description = 'Concurrency same-slot booking room'),
--     CURRENT_DATE + 30 + TIME '10:00:00'
-- );
--
-- SESSION B: book the SAME slot for a different user; should wait.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
-- VALUES (
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_b@example.invalid'),
--     (SELECT l.listing_id FROM listing AS l
--      JOIN room AS r ON r.room_id = l.room_id
--      WHERE r.description = 'Concurrency same-slot booking room'),
--     CURRENT_DATE + 30 + TIME '10:00:00'
-- );
--
-- SESSION A: COMMIT;
-- SESSION B: expect "Viewing slot is not available".
-- SESSION B: ROLLBACK;
--
-- VERIFY: one CONFIRMED booking; the 10:00 slot is BOOKED.
-- SELECT vs.viewing_timestamp, vs.status AS slot_status,
--        COUNT(vb.booking_id) FILTER (WHERE vb.status = 'CONFIRMED')
--            AS confirmed_bookings
-- FROM viewing_slot AS vs
-- JOIN listing AS l ON l.listing_id = vs.listing_id
-- JOIN room AS r ON r.room_id = l.room_id
-- LEFT JOIN viewing_booking AS vb
--   ON vb.listing_id = vs.listing_id
--  AND vb.viewing_timestamp = vs.viewing_timestamp
-- WHERE r.description = 'Concurrency same-slot booking room'
-- GROUP BY vs.viewing_timestamp, vs.status;

-- =====================================================================
-- F03: TWO ACTIVE LISTINGS FOR THE SAME ROOM
-- Tests Trigger 6: enforce_one_active_listing
-- =====================================================================
-- SESSION A: create the room's FIRST active listing; leave open.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO listing (
--     room_id, creator_user_id, weekly_rent, available_from,
--     listing_date, status, num_housemates
-- )
-- VALUES (
--     (SELECT room_id FROM room
--      WHERE description = 'Concurrency active-listing test room'),
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_owner@example.invalid'),
--     450, CURRENT_DATE + 30, CURRENT_DATE, 'OPEN', 1
-- );
--
-- SESSION B: try a SECOND OPEN listing for the SAME room; should wait.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO listing (
--     room_id, creator_user_id, weekly_rent, available_from,
--     listing_date, status, num_housemates
-- )
-- VALUES (
--     (SELECT room_id FROM room
--      WHERE description = 'Concurrency active-listing test room'),
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_owner@example.invalid'),
--     475, CURRENT_DATE + 30, CURRENT_DATE, 'OPEN', 1
-- );
--
-- SESSION A: COMMIT;
-- SESSION B: expect "This room already has an active listing".
-- SESSION B: ROLLBACK;
--
-- VERIFY: exactly one active (OPEN or PAUSED) listing for this room.
-- SELECT r.room_id,
--        COUNT(l.listing_id) FILTER (WHERE l.status IN ('OPEN', 'PAUSED'))
--            AS active_listing_count
-- FROM room AS r
-- LEFT JOIN listing AS l ON l.room_id = r.room_id
-- WHERE r.description = 'Concurrency active-listing test room'
-- GROUP BY r.room_id;

-- =====================================================================
-- F04: TWO ROOMS INSERTED WHEN ONLY ONE SPACE REMAINS
-- Tests Trigger 7: enforce_property_room_limit
-- =====================================================================
-- Property 998 has total_rooms=3 and currently contains 2 rooms.
-- SESSION A: insert the THIRD room; leave open.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO room (
--     room_type, num_roommates, is_furnished, has_ensuite,
--     description, property_id
-- )
-- VALUES (
--     'Private', 0, TRUE, FALSE, 'F04 room inserted by Session A',
--     (SELECT property_id FROM property_characteristics
--      WHERE street_number = '998'
--        AND street_name = 'HouseMatch Concurrency Test Street'
--        AND suburb = 'Testville')
-- );
--
-- SESSION B: try to insert a FOURTH room; should wait.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO room (
--     room_type, num_roommates, is_furnished, has_ensuite,
--     description, property_id
-- )
-- VALUES (
--     'Private', 0, TRUE, FALSE, 'F04 room inserted by Session B',
--     (SELECT property_id FROM property_characteristics
--      WHERE street_number = '998'
--        AND street_name = 'HouseMatch Concurrency Test Street'
--        AND suburb = 'Testville')
-- );
--
-- SESSION A: COMMIT;
-- SESSION B: expect "Property cannot exceed its total number of rooms".
-- SESSION B: ROLLBACK;
--
-- VERIFY: total_rooms=3, actual_room_count=3.
-- SELECT p.property_id, p.total_rooms,
--        COUNT(r.room_id) AS actual_room_count
-- FROM property_characteristics AS p
-- LEFT JOIN room AS r ON r.property_id = p.property_id
-- WHERE p.street_number = '998'
--   AND p.street_name = 'HouseMatch Concurrency Test Street'
--   AND p.suburb = 'Testville'
-- GROUP BY p.property_id, p.total_rooms;

-- =====================================================================
-- F05: SAME USER BOOKS TWO DIFFERENT SLOTS FOR THE SAME LISTING
-- Tests Trigger 10: enforce_one_viewing_per_listing
-- =====================================================================
-- SESSION A: user A books the 11:00 slot; leave open.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
-- VALUES (
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_a@example.invalid'),
--     (SELECT l.listing_id FROM listing AS l
--      JOIN room AS r ON r.room_id = l.room_id
--      WHERE r.description = 'Concurrency one-user-two-slots room'),
--     CURRENT_DATE + 30 + TIME '11:00:00'
-- );
--
-- SESSION B: same user books the DIFFERENT 12:00 slot; should wait.
--
-- BEGIN ISOLATION LEVEL READ COMMITTED;
-- INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
-- VALUES (
--     (SELECT user_id FROM app_user
--      WHERE email = 'hm_concurrency_a@example.invalid'),
--     (SELECT l.listing_id FROM listing AS l
--      JOIN room AS r ON r.room_id = l.room_id
--      WHERE r.description = 'Concurrency one-user-two-slots room'),
--     CURRENT_DATE + 30 + TIME '12:00:00'
-- );
--
-- SESSION A: COMMIT;
-- SESSION B: expect
--   "User already has a confirmed viewing booking for this listing".
-- SESSION B: ROLLBACK;
--
-- VERIFY: 11:00 is BOOKED with 1 confirmed booking;
--         12:00 remains AVAILABLE with 0 confirmed bookings.
-- SELECT vs.viewing_timestamp::time AS viewing_time,
--        vs.status AS slot_status,
--        COUNT(vb.booking_id) FILTER (WHERE vb.status = 'CONFIRMED')
--            AS confirmed_bookings
-- FROM viewing_slot AS vs
-- JOIN listing AS l ON l.listing_id = vs.listing_id
-- JOIN room AS r ON r.room_id = l.room_id
-- LEFT JOIN viewing_booking AS vb
--   ON vb.listing_id = vs.listing_id
--  AND vb.viewing_timestamp = vs.viewing_timestamp
-- WHERE r.description = 'Concurrency one-user-two-slots room'
-- GROUP BY vs.viewing_timestamp, vs.status
-- ORDER BY vs.viewing_timestamp;

-- =====================================================================
-- CLEANUP: RUN ONLY AFTER F01-F05 HAVE FINISHED.
-- First make sure BOTH Query Tool sessions have ended their transactions.
-- Copy/uncomment this section and run it ONCE in either session.
-- This also cleans up fixtures from the original two-test version.
-- =====================================================================
-- BEGIN;
--
-- DELETE FROM viewing_booking
-- WHERE listing_id IN (
--     SELECT l.listing_id FROM listing AS l
--     JOIN room AS r ON r.room_id = l.room_id
--     JOIN property_characteristics AS p ON p.property_id = r.property_id
--     WHERE p.street_name = 'HouseMatch Concurrency Test Street'
--       AND p.suburb = 'Testville'
-- );
--
-- DELETE FROM viewing_slot
-- WHERE listing_id IN (
--     SELECT l.listing_id FROM listing AS l
--     JOIN room AS r ON r.room_id = l.room_id
--     JOIN property_characteristics AS p ON p.property_id = r.property_id
--     WHERE p.street_name = 'HouseMatch Concurrency Test Street'
--       AND p.suburb = 'Testville'
-- );
--
-- DELETE FROM application
-- WHERE listing_id IN (
--     SELECT l.listing_id FROM listing AS l
--     JOIN room AS r ON r.room_id = l.room_id
--     JOIN property_characteristics AS p ON p.property_id = r.property_id
--     WHERE p.street_name = 'HouseMatch Concurrency Test Street'
--       AND p.suburb = 'Testville'
-- );
--
-- DELETE FROM saves
-- WHERE listing_id IN (
--     SELECT l.listing_id FROM listing AS l
--     JOIN room AS r ON r.room_id = l.room_id
--     JOIN property_characteristics AS p ON p.property_id = r.property_id
--     WHERE p.street_name = 'HouseMatch Concurrency Test Street'
--       AND p.suburb = 'Testville'
-- );
--
-- DELETE FROM listing
-- WHERE room_id IN (
--     SELECT r.room_id FROM room AS r
--     JOIN property_characteristics AS p ON p.property_id = r.property_id
--     WHERE p.street_name = 'HouseMatch Concurrency Test Street'
--       AND p.suburb = 'Testville'
-- );
--
-- DELETE FROM room
-- WHERE property_id IN (
--     SELECT property_id FROM property_characteristics
--     WHERE street_name = 'HouseMatch Concurrency Test Street'
--       AND suburb = 'Testville'
-- );
--
-- DELETE FROM property_characteristics
-- WHERE street_name = 'HouseMatch Concurrency Test Street'
--   AND suburb = 'Testville';
--
-- DELETE FROM app_user
-- WHERE email IN (
--     'hm_concurrency_owner@example.invalid',
--     'hm_concurrency_a@example.invalid',
--     'hm_concurrency_b@example.invalid'
-- );
--
-- COMMIT;
