-- =====================================================================
-- HouseMatch - housematch_tests.sql
-- COMP9120 Group Project
-- Automated integrity, trigger, transaction and rollback tests.
-- =====================================================================
-- PREREQUISITES
--   1. Run housematch_schema.sql
--   2. Run housematch_triggers.sql (including Triggers 1-10)
--   3. Run housematch_sample_data.sql (recommended, but these tests use their own data)
--
-- HOW TO RUN
--   Open this file in pgAdmin's Query Tool and execute THE WHOLE FILE.
--   Look for "PASS" messages and the final total in the Messages tab.
--   An unexpected result raises "FAIL" and stops the test block.
--
-- SAFETY
--   Every fixture and test runs inside one transaction, rolled back below.
--   No existing rows are intentionally changed. No tables are added.
--   PostgreSQL identity sequences can still advance after ROLLBACK.
--   If execution stops before the final ROLLBACK, run ROLLBACK manually.
--
-- Concurrency requires TWO database sessions and is documented separately
-- in housematch_concurrency_tests.sql.
-- =====================================================================

BEGIN;

DO $housematch_tests$
DECLARE
    v_run TEXT := txid_current()::TEXT;
    v_street TEXT := 'HouseMatch Automated Test Street ' || txid_current()::TEXT;

    v_owner INTEGER;
    v_user_a INTEGER;
    v_user_b INTEGER;
    v_user_c INTEGER;
    v_property INTEGER;
    v_room_open INTEGER;
    v_room_paused INTEGER;
    v_room_workflow INTEGER;
    v_listing_open INTEGER;
    v_listing_paused INTEGER;
    v_listing_workflow INTEGER;
    v_app_a INTEGER;
    v_app_b INTEGER;
    v_work_app_a INTEGER;
    v_work_app_b INTEGER;
    v_booking_a INTEGER;
    v_booking_b INTEGER;
    v_work_booking INTEGER;
    v_new_property INTEGER;
    v_new_room INTEGER;
    v_new_listing INTEGER;
    v_failed_property INTEGER;
    v_failed_room INTEGER;
    v_error_message TEXT;
    v_count INTEGER;
    v_passed INTEGER := 0;

    v_slot_open TIMESTAMP := CURRENT_DATE + 14 + TIME '10:00:00';
    v_slot_other TIMESTAMP := CURRENT_DATE + 14 + TIME '11:00:00';
    v_slot_cancelled TIMESTAMP := CURRENT_DATE + 14 + TIME '12:00:00';
    v_slot_paused TIMESTAMP := CURRENT_DATE + 15 + TIME '10:00:00';
    v_slot_work_a TIMESTAMP := CURRENT_DATE + 16 + TIME '10:00:00';
    v_slot_work_b TIMESTAMP := CURRENT_DATE + 16 + TIME '11:00:00';
BEGIN
    RAISE NOTICE 'HouseMatch tests: preparing isolated test fixtures';

    -- ---------------------------------------------------------------
    -- SETUP: four users, one property, three rooms, three listings.
    -- All fixtures are removed by the outer ROLLBACK.
    -- ---------------------------------------------------------------
    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Test', 'Owner', 'hm_owner_' || v_run || '@example.invalid')
    RETURNING user_id INTO v_owner;

    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Test', 'ApplicantA', 'hm_a_' || v_run || '@example.invalid')
    RETURNING user_id INTO v_user_a;

    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Test', 'ApplicantB', 'hm_b_' || v_run || '@example.invalid')
    RETURNING user_id INTO v_user_b;

    INSERT INTO app_user (first_name, last_name, email)
    VALUES ('Test', 'ApplicantC', 'hm_c_' || v_run || '@example.invalid')
    RETURNING user_id INTO v_user_c;

    INSERT INTO property_characteristics (
        street_number, street_name, suburb, state, postcode, unit_number,
        property_type, total_rooms, car_spots, smoking_policy, pet_policy
    )
    VALUES (
        '999', v_street, 'Testville', 'NSW', '2000', NULL,
        'House', 3, 1, 'No smoking', FALSE
    )
    RETURNING property_id INTO v_property;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES ('Private', 0, TRUE, FALSE, 'Open test room', v_property)
    RETURNING room_id INTO v_room_open;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES ('Private', 0, TRUE, FALSE, 'Paused test room', v_property)
    RETURNING room_id INTO v_room_paused;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES ('Private', 0, TRUE, FALSE, 'Workflow test room', v_property)
    RETURNING room_id INTO v_room_workflow;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (v_room_open, v_owner, 400, CURRENT_DATE + 30,
            CURRENT_DATE, 'OPEN', 2)
    RETURNING listing_id INTO v_listing_open;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (v_room_paused, v_owner, 420, CURRENT_DATE + 30,
            CURRENT_DATE, 'PAUSED', 2)
    RETURNING listing_id INTO v_listing_paused;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (v_room_workflow, v_owner, 440, CURRENT_DATE + 30,
            CURRENT_DATE, 'OPEN', 2)
    RETURNING listing_id INTO v_listing_workflow;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_user_a, v_listing_open)
    RETURNING application_id INTO v_app_a;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_user_b, v_listing_open)
    RETURNING application_id INTO v_app_b;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_user_a, v_listing_workflow)
    RETURNING application_id INTO v_work_app_a;

    INSERT INTO application (user_id, listing_id)
    VALUES (v_user_b, v_listing_workflow)
    RETURNING application_id INTO v_work_app_b;

    INSERT INTO viewing_slot (listing_id, viewing_timestamp, status)
    VALUES
        (v_listing_open, v_slot_open, 'AVAILABLE'),
        (v_listing_open, v_slot_other, 'AVAILABLE'),
        (v_listing_open, v_slot_cancelled, 'CANCELLED'),
        (v_listing_paused, v_slot_paused, 'AVAILABLE'),
        (v_listing_workflow, v_slot_work_a, 'AVAILABLE'),
        (v_listing_workflow, v_slot_work_b, 'AVAILABLE');

    -- ---------------------------------------------------------------
    -- A. STATIC INTEGRITY CONSTRAINTS
    -- Each block deliberately causes the expected PostgreSQL error.
    -- If an invalid row is accepted, the test FAILS.
    -- ---------------------------------------------------------------

    -- A01: UNIQUE email.
    BEGIN
        INSERT INTO app_user (first_name, last_name, email)
        VALUES ('Duplicate', 'Email', 'hm_owner_' || v_run || '@example.invalid');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A01: duplicate email was accepted';
    EXCEPTION WHEN unique_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A01: duplicate email rejected';
    END;

    -- A02: NOT NULL first name.
    BEGIN
        INSERT INTO app_user (last_name, email)
        VALUES ('MissingFirstName', 'hm_missing_' || v_run || '@example.invalid');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A02: NULL first name was accepted';
    EXCEPTION WHEN not_null_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A02: missing required name rejected';
    END;

    -- A03: postcode must contain four digits.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('100', 'Bad Postcode Street', 'Testville', 'NSW', 'ABCD',
                'House', 2, 0, 'No smoking', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A03: invalid postcode was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A03: invalid postcode rejected';
    END;

    -- A04: valid Australian state code required.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('101', 'Bad State Street', 'Testville', 'XYZ', '2000',
                'House', 2, 0, 'No smoking', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A04: invalid state was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A04: invalid state rejected';
    END;

    -- A05: duplicate property address rejected even with NULL unit_number.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode, unit_number,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('999', v_street, 'Testville', 'NSW', '2000', NULL,
                'House', 3, 1, 'No smoking', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A05: duplicate property address was accepted';
    EXCEPTION WHEN unique_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A05: duplicate property address rejected';
    END;

    -- A06: roommates cannot be negative.
    BEGIN
        UPDATE room
        SET num_roommates = -1
        WHERE room_id = v_room_open;
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A06: negative roommates were accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A06: negative roommates rejected';
    END;

    -- A07: weekly rent must be positive.
    BEGIN
        UPDATE listing
        SET weekly_rent = 0
        WHERE listing_id = v_listing_open;
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A07: zero rent was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A07: zero rent rejected';
    END;

    -- A08: listing status is restricted to OPEN/PAUSED/CLOSED.
    BEGIN
        INSERT INTO listing (
            room_id, creator_user_id, weekly_rent, available_from,
            listing_date, status, num_housemates
        )
        VALUES (v_room_open, v_owner, 400, CURRENT_DATE + 30,
                CURRENT_DATE, 'ARCHIVED', 2);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A08: invalid listing status was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A08: invalid listing status rejected';
    END;

    -- A09: foreign key application.user_id must reference a real user.
    BEGIN
        INSERT INTO application (user_id, listing_id)
        VALUES (-1, v_listing_open);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A09: invalid applicant foreign key was accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A09: invalid applicant foreign key rejected';
    END;

    -- A10: user cannot apply twice to the same listing.
    BEGIN
        INSERT INTO application (user_id, listing_id)
        VALUES (v_user_a, v_listing_open);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A10: duplicate application was accepted';
    EXCEPTION WHEN unique_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A10: duplicate application rejected';
    END;

    -- A11: profile maximum rent must be >= minimum rent.
    BEGIN
        INSERT INTO preference_profile (
            user_id, profile_name, min_rent, max_rent,
            smoking_preference, pet_preference
        )
        VALUES (v_user_a, 'Invalid Budget', 600, 400, 'Any', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A11: invalid budget range was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A11: invalid budget range rejected';
    END;

    -- A12: saved listing preference rank must be positive.
    BEGIN
        INSERT INTO saves (user_id, listing_id, preference_rank)
        VALUES (v_user_a, v_listing_open, 0);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A12: zero preference rank was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A12: zero preference rank rejected';
    END;

    -- A13: viewing_slot composite primary key is unique.
    BEGIN
        INSERT INTO viewing_slot (listing_id, viewing_timestamp)
        VALUES (v_listing_open, v_slot_open);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A13: duplicate viewing slot was accepted';
    EXCEPTION WHEN unique_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A13: duplicate viewing slot rejected';
    END;

    -- A14: preferred_suburb must reference an existing preference profile.
    BEGIN
        INSERT INTO preferred_suburb (user_id, profile_name, preferred_suburb)
        VALUES (v_user_a, 'Profile Does Not Exist', 'Glebe');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A14: missing preference profile was accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A14: missing preference profile rejected';
    END;

    -- A15: application status must be PENDING/ACCEPTED/REJECTED.
    BEGIN
        INSERT INTO application (user_id, listing_id, status)
        VALUES (v_user_c, v_listing_open, 'WAITING');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A15: invalid application status was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A15: invalid application status rejected';
    END;

    -- A16: property_type must be one of the permitted categories.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('102', 'Bad Property Type Street', 'Testville', 'NSW', '2000',
                'Terrace', 2, 0, 'No smoking', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A16: invalid property type was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A16: invalid property type rejected';
    END;

    -- A17: smoking_policy must be one of the permitted values.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('103', 'Bad Smoking Policy Street', 'Testville', 'NSW', '2000',
                'House', 2, 0, 'Indoors allowed', FALSE);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A17: invalid smoking policy was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A17: invalid smoking policy rejected';
    END;

    -- A18: pet_policy is required and cannot be NULL.
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('104', 'Missing Pet Friendly Street', 'Testville', 'NSW', '2000',
                'House', 2, 0, 'No smoking', NULL);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A18: NULL pet_policy was accepted';
    EXCEPTION WHEN not_null_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A18: NULL pet_policy rejected';
    END;

    -- A19: room_type must be Private or Shared.
    BEGIN
        UPDATE room
        SET room_type = 'Master'
        WHERE room_id = v_room_open;
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL A19: invalid room type was accepted';
    EXCEPTION WHEN check_violation THEN
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS A19: invalid room type rejected';
    END;

    -- ---------------------------------------------------------------
    -- B. DYNAMIC INTEGRITY CONSTRAINTS (TEN TRIGGERS)
    -- ---------------------------------------------------------------

    -- B01: Trigger 2 rejects new applications to PAUSED listings.
    BEGIN
        INSERT INTO application (user_id, listing_id)
        VALUES (v_user_c, v_listing_paused);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B01: application to PAUSED listing succeeded';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Applications can only be submitted to OPEN listings%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B01: application to PAUSED listing rejected';
    END;

    -- B02: An application's target listing is immutable.
    BEGIN
        UPDATE application
        SET listing_id = v_listing_paused
        WHERE application_id = v_app_b;
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B02: application moved to PAUSED listing';
    EXCEPTION WHEN check_violation THEN
        IF SQLERRM NOT LIKE '%Application user and listing are immutable%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B02: moving application to PAUSED listing rejected';
    END;

    -- B03: Trigger 1 permits the first acceptance.
    UPDATE application
    SET status = 'ACCEPTED'
    WHERE application_id = v_app_a;

    IF (SELECT status FROM application WHERE application_id = v_app_a) <> 'ACCEPTED' THEN
        RAISE EXCEPTION 'FAIL B03: first application was not accepted';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B03: first application accepted';

    -- B04: Trigger 1 prevents a second accepted application.
    BEGIN
        UPDATE application
        SET status = 'ACCEPTED'
        WHERE application_id = v_app_b;
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B04: second accepted application was allowed';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%already has an accepted application%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B04: second accepted application rejected';
    END;

    -- B05: Trigger 3 rejects a booking for a PAUSED listing.
    BEGIN
        INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
        VALUES (v_user_a, v_listing_paused, v_slot_paused);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B05: PAUSED listing booking was allowed';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%listing that is not OPEN%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B05: booking a PAUSED listing rejected';
    END;

    -- B06: Trigger 3 rejects a CANCELLED viewing slot.
    BEGIN
        INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
        VALUES (v_user_a, v_listing_open, v_slot_cancelled);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B06: cancelled slot was booked';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Viewing slot is not available%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B06: booking a CANCELLED slot rejected';
    END;

    -- B07: Trigger 3 books an available slot and marks it BOOKED.
    INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
    VALUES (v_user_a, v_listing_open, v_slot_open)
    RETURNING booking_id INTO v_booking_a;

    IF (SELECT status FROM viewing_slot
        WHERE listing_id = v_listing_open AND viewing_timestamp = v_slot_open) <> 'BOOKED' THEN
        RAISE EXCEPTION 'FAIL B07: slot was not marked BOOKED';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B07: confirmed booking marks slot BOOKED';

    -- B08: Trigger 3 prevents double-booking.
    BEGIN
        INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
        VALUES (v_user_b, v_listing_open, v_slot_open);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B08: double-booking was allowed';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Viewing slot is not available%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B08: double-booking rejected';
    END;

    -- B09: Report section 2.4 permits rescheduling within the same listing.
    UPDATE viewing_booking SET viewing_timestamp=v_slot_other WHERE booking_id=v_booking_a;
    IF (SELECT status FROM viewing_slot WHERE listing_id=v_listing_open AND viewing_timestamp=v_slot_open)<>'AVAILABLE'
       OR (SELECT status FROM viewing_slot WHERE listing_id=v_listing_open AND viewing_timestamp=v_slot_other)<>'BOOKED' THEN
        RAISE EXCEPTION 'FAIL B09: rescheduling did not move slot availability';
    END IF;
    UPDATE viewing_booking SET viewing_timestamp=v_slot_open WHERE booking_id=v_booking_a;
    v_passed:=v_passed+1;
    RAISE NOTICE 'PASS B09: rescheduling preserves booking identity and releases the old slot';

    -- B10: Trigger 4 releases a slot when the booking is cancelled.
    UPDATE viewing_booking
    SET status = 'CANCELLED'
    WHERE booking_id = v_booking_a;

    IF (SELECT status FROM viewing_slot
        WHERE listing_id = v_listing_open AND viewing_timestamp = v_slot_open) <> 'AVAILABLE' THEN
        RAISE EXCEPTION 'FAIL B10: cancelled booking did not release its slot';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B10: cancelling booking releases its slot';

    -- B11: another user can book the newly released slot.
    INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
    VALUES (v_user_b, v_listing_open, v_slot_open)
    RETURNING booking_id INTO v_booking_b;

    IF (SELECT status FROM viewing_slot
        WHERE listing_id = v_listing_open AND viewing_timestamp = v_slot_open) <> 'BOOKED'
       OR (SELECT status FROM viewing_booking WHERE booking_id = v_booking_a) <> 'CANCELLED'
       OR (SELECT status FROM viewing_booking WHERE booking_id = v_booking_b) <> 'CONFIRMED' THEN
        RAISE EXCEPTION 'FAIL B11: released slot could not be rebooked correctly';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B11: released slot can be rebooked';

    -- B12: Trigger 5 rejects viewing slots in the past.
    BEGIN
        INSERT INTO viewing_slot (listing_id, viewing_timestamp)
        VALUES (v_listing_open, CURRENT_DATE - 1 + TIME '10:00:00');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL B12: past viewing slot was accepted';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Viewing timestamp must be in the future%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B12: past viewing slot rejected';
    END;

    -- B13: Reject a second OPEN listing for the same room.
    BEGIN
        INSERT INTO listing (
            room_id, creator_user_id, weekly_rent,
            available_from, listing_date, status, num_housemates
        )
        VALUES (
            v_room_open, v_owner, 400,
            CURRENT_DATE + 30, CURRENT_DATE, 'OPEN', 2
        );

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B13: second OPEN listing was allowed';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%This room already has an active listing%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B13: second OPEN listing rejected';
    END;


    -- B14: Reject a PAUSED listing when the room already has an OPEN listing.
    BEGIN
        INSERT INTO listing (
            room_id, creator_user_id, weekly_rent,
            available_from, listing_date, status, num_housemates
        )
        VALUES (
            v_room_open, v_owner, 400,
            CURRENT_DATE + 30, CURRENT_DATE, 'PAUSED', 2
        );

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B14: second active listing was allowed';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%This room already has an active listing%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B14: OPEN and PAUSED listings cannot coexist';
    END;


    -- B15: Reject moving an active listing to a room with an active listing.
    BEGIN
        UPDATE listing
        SET room_id = v_room_open
        WHERE listing_id = v_listing_paused;

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B15: active listing moved to occupied room';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%This room already has an active listing%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B15: active listing cannot move to occupied room';
    END;


    -- B16 and B17: CLOSED listings are allowed, but cannot be reopened
    -- while another active listing exists for the same room.
    DECLARE
        v_closed_listing INTEGER;
    BEGIN

        -- B16: A CLOSED listing is allowed for a room with an OPEN listing.
        INSERT INTO listing (
            room_id, creator_user_id, weekly_rent,
            available_from, listing_date, status, num_housemates
        )
        VALUES (
            v_room_open, v_owner, 400,
            CURRENT_DATE + 30, CURRENT_DATE, 'CLOSED', 2
        )
        RETURNING listing_id INTO v_closed_listing;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B16: CLOSED listing allowed alongside OPEN listing';


        -- B17: Reopening that CLOSED listing must be rejected.
        BEGIN
            UPDATE listing
            SET status = 'OPEN'
            WHERE listing_id = v_closed_listing;

            RAISE EXCEPTION USING ERRCODE = 'PT001',
                MESSAGE = 'FAIL B17: CLOSED listing was reopened';

        EXCEPTION WHEN raise_exception THEN
            IF SQLERRM NOT LIKE '%This room already has an active listing%' THEN
                RAISE;
            END IF;

            v_passed := v_passed + 1;
            RAISE NOTICE 'PASS B17: reopening conflicting CLOSED listing rejected';
        END;

    END;


    -- ---------------------------------------------------------------
    -- TRIGGER 7: PROPERTY ROOM CAPACITY
    -- ---------------------------------------------------------------

    -- B18: Reject adding a fourth room to a property with total_rooms = 3.
    BEGIN
        INSERT INTO room (
            room_type, num_roommates, is_furnished,
            has_ensuite, property_id
        )
        VALUES ('Private', 0, TRUE, FALSE, v_property);

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B18: property exceeded its room capacity';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Property cannot exceed its total number of rooms%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B18: fourth room rejected';
    END;

    -- B19: Reject moving a room into a property that is already full.
    DECLARE
        v_full_property INTEGER;
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode,
            property_type, total_rooms, car_spots,
            smoking_policy, pet_policy
        )
        VALUES (
            '998', v_street, 'Testville', 'NSW', '2000',
            'House', 1, 0, 'No smoking', FALSE
        )
        RETURNING property_id INTO v_full_property;

        INSERT INTO room (
            room_type, num_roommates, is_furnished,
            has_ensuite, property_id
        )
        VALUES ('Private', 0, TRUE, FALSE, v_full_property);

        BEGIN
            UPDATE room
            SET property_id = v_full_property
            WHERE room_id = v_room_paused;

            RAISE EXCEPTION USING ERRCODE = 'PT001',
                MESSAGE = 'FAIL B19: room moved into full property';

        EXCEPTION WHEN raise_exception THEN
            IF SQLERRM NOT LIKE '%Property cannot exceed its total number of rooms%' THEN
                RAISE;
            END IF;

            v_passed := v_passed + 1;
            RAISE NOTICE 'PASS B19: moving room into full property rejected';
        END;
    END;

    -- ---------------------------------------------------------------
    -- TRIGGER 8: UPDATING TOTAL_ROOMS
    -- ---------------------------------------------------------------

    -- B20: Reject reducing total_rooms below existing room count.
    BEGIN
        UPDATE property_characteristics
        SET total_rooms = 2
        WHERE property_id = v_property;

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B20: total_rooms reduced below existing rooms';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Total rooms cannot be less than the number of existing rooms%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B20: reducing total_rooms below room count rejected';
    END;

    -- B21: Allow increasing total_rooms, then restore original value.
    UPDATE property_characteristics
    SET total_rooms = 4
    WHERE property_id = v_property;

    IF (SELECT total_rooms
        FROM property_characteristics
        WHERE property_id = v_property) IS DISTINCT FROM 4 THEN
        RAISE EXCEPTION 'FAIL B21: increasing total_rooms failed';
    END IF;

    UPDATE property_characteristics
    SET total_rooms = 3
    WHERE property_id = v_property;

    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B21: increasing total_rooms allowed';

    -- ---------------------------------------------------------------
    -- TRIGGER 9: USERS CANNOT APPLY TO THEIR OWN LISTINGS
    -- ---------------------------------------------------------------

    -- B22: Reject an application from the listing creator.
    BEGIN
        INSERT INTO application (user_id, listing_id)
        VALUES (v_owner, v_listing_open);

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B22: owner applied to own listing';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Users cannot apply to their own listings%' THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B22: owner application rejected';
    END;

    -- B23: Allow a different user to apply.
    INSERT INTO application (user_id, listing_id)
    VALUES (v_user_c, v_listing_open);

    IF NOT EXISTS (
        SELECT 1 FROM application
        WHERE user_id = v_user_c AND listing_id = v_listing_open
    ) THEN
        RAISE EXCEPTION 'FAIL B23: valid application was not created';
    END IF;

    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B23: different user can apply';

    -- ---------------------------------------------------------------
    -- TRIGGER 10: ONE CONFIRMED VIEWING PER USER PER LISTING
    -- ---------------------------------------------------------------

    -- B24: Reject a second confirmed booking for the same listing.
    -- User B already has a confirmed booking from B11.
    BEGIN
        INSERT INTO viewing_booking (
            user_id, listing_id, viewing_timestamp
        )
        VALUES (v_user_b, v_listing_open, v_slot_other);

        RAISE EXCEPTION USING ERRCODE = 'PT001',
            MESSAGE = 'FAIL B24: user booked two viewings for one listing';

    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE
            '%User already has a confirmed viewing booking for this listing%'
        THEN
            RAISE;
        END IF;

        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS B24: second confirmed booking rejected';
    END;

    -- A failed booking must leave the other slot AVAILABLE.
    IF (SELECT status FROM viewing_slot
        WHERE listing_id = v_listing_open
          AND viewing_timestamp = v_slot_other) IS DISTINCT FROM 'AVAILABLE' THEN
        RAISE EXCEPTION 'FAIL B24: failed booking changed slot availability';
    END IF;

    -- B25: Allow the same user to book a different listing.
    INSERT INTO viewing_booking (
        user_id, listing_id, viewing_timestamp
    )
    VALUES (v_user_b, v_listing_workflow, v_slot_work_b);

    IF NOT EXISTS (
        SELECT 1 FROM viewing_booking
        WHERE user_id = v_user_b
          AND listing_id = v_listing_workflow
          AND status = 'CONFIRMED'
    ) THEN
        RAISE EXCEPTION 'FAIL B25: booking different listing failed';
    END IF;

    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B25: user can book a different listing';

    -- B26: Allow rebooking after cancelling the previous booking.
    UPDATE viewing_booking
    SET status = 'CANCELLED'
    WHERE booking_id = v_booking_b;

    INSERT INTO viewing_booking (
        user_id, listing_id, viewing_timestamp
    )
    VALUES (v_user_b, v_listing_open, v_slot_other);

    IF (SELECT COUNT(*) FROM viewing_booking
        WHERE user_id = v_user_b
          AND listing_id = v_listing_open
          AND status = 'CONFIRMED') <> 1
       OR (SELECT status FROM viewing_slot
           WHERE listing_id = v_listing_open
             AND viewing_timestamp = v_slot_open) IS DISTINCT FROM 'AVAILABLE'
       OR (SELECT status FROM viewing_slot
           WHERE listing_id = v_listing_open
             AND viewing_timestamp = v_slot_other) IS DISTINCT FROM 'BOOKED'
    THEN
        RAISE EXCEPTION 'FAIL B26: cancellation and rebooking failed';
    END IF;

    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS B26: cancelled booking can be replaced';

    -- ---------------------------------------------------------------
    -- C. MULTI-STEP TRANSACTION 1: ACCEPT APPLICATION / CLOSE LISTING
    -- Replicates the workflow from housematch_transactions.sql on test fixtures.
    -- ---------------------------------------------------------------
    INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
    VALUES (v_user_a, v_listing_workflow, v_slot_work_a)
    RETURNING booking_id INTO v_work_booking;

    PERFORM 1
    FROM listing
    WHERE listing_id = v_listing_workflow AND status = 'OPEN'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'FAIL C01: workflow listing is not OPEN';
    END IF;

    UPDATE application
    SET status = 'ACCEPTED'
    WHERE application_id = v_work_app_a
      AND listing_id = v_listing_workflow
      AND status = 'PENDING';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'FAIL C01: selected application was not accepted';
    END IF;

    UPDATE application
    SET status = 'REJECTED'
    WHERE listing_id = v_listing_workflow
      AND application_id <> v_work_app_a
      AND status = 'PENDING';

    UPDATE viewing_booking
    SET status = 'CANCELLED'
    WHERE listing_id = v_listing_workflow AND status = 'CONFIRMED';

    UPDATE viewing_slot
    SET status = 'CANCELLED'
    WHERE listing_id = v_listing_workflow AND status <> 'CANCELLED';

    UPDATE listing
    SET status = 'CLOSED'
    WHERE listing_id = v_listing_workflow;

    IF (SELECT status FROM application WHERE application_id = v_work_app_a) <> 'ACCEPTED'
       OR (SELECT status FROM application WHERE application_id = v_work_app_b) <> 'REJECTED'
       OR (SELECT status FROM viewing_booking WHERE booking_id = v_work_booking) <> 'CANCELLED'
       OR (SELECT status FROM listing WHERE listing_id = v_listing_workflow) <> 'CLOSED'
       OR EXISTS (
           SELECT 1 FROM viewing_slot
           WHERE listing_id = v_listing_workflow AND status <> 'CANCELLED'
       ) THEN
        RAISE EXCEPTION 'FAIL C01: accepting application did not complete all related changes';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS C01: accepting application closes listing, rejects others and cancels viewings';

    -- C02: closed listing cannot receive a new application.
    BEGIN
        INSERT INTO application (user_id, listing_id)
        VALUES (v_user_c, v_listing_workflow);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL C02: CLOSED listing accepted an application';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Applications can only be submitted to OPEN listings%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS C02: CLOSED listing rejects new applications';
    END;

    -- C03: closed listing cannot receive a confirmed viewing booking.
    BEGIN
        INSERT INTO viewing_booking (user_id, listing_id, viewing_timestamp)
        VALUES (v_user_c, v_listing_workflow, v_slot_work_b);
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL C03: CLOSED listing accepted a viewing';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%listing that is not OPEN%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS C03: CLOSED listing rejects viewing bookings';
    END;

    -- C04: Trigger 5 rejects new viewing slots for CLOSED listings.
    BEGIN
        INSERT INTO viewing_slot (listing_id, viewing_timestamp)
        VALUES (v_listing_workflow, CURRENT_DATE + 60 + TIME '10:00:00');
        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL C04: CLOSED listing accepted a new viewing slot';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE '%Cannot add viewing slot to a closed listing%' THEN
            RAISE;
        END IF;
        v_passed := v_passed + 1;
        RAISE NOTICE 'PASS C04: CLOSED listing rejects new viewing slots';
    END;

    -- ---------------------------------------------------------------
    -- D. MULTI-STEP TRANSACTION 2: PROPERTY -> ROOM -> LISTING
    -- ---------------------------------------------------------------
    INSERT INTO property_characteristics (
        street_number, street_name, suburb, state, postcode, unit_number,
        property_type, total_rooms, car_spots, smoking_policy, pet_policy
    )
    VALUES ('1000', 'HouseMatch New Listing Street ' || v_run,
            'Petersham', 'NSW', '2049', NULL,
            'Apartment', 3, 1, 'No smoking', TRUE)
    RETURNING property_id INTO v_new_property;

    INSERT INTO room (
        room_type, num_roommates, is_furnished, has_ensuite,
        description, property_id
    )
    VALUES ('Private', 0, TRUE, FALSE,
            'Test listing room', v_new_property)
    RETURNING room_id INTO v_new_room;

    INSERT INTO listing (
        room_id, creator_user_id, weekly_rent, available_from,
        listing_date, status, num_housemates
    )
    VALUES (v_new_room, v_owner, 375, CURRENT_DATE + 30,
            CURRENT_DATE, 'OPEN', 2)
    RETURNING listing_id INTO v_new_listing;

    SELECT COUNT(*) INTO v_count
    FROM listing AS l
    JOIN room AS r ON r.room_id = l.room_id
    JOIN property_characteristics AS p ON p.property_id = r.property_id
    WHERE l.listing_id = v_new_listing
      AND r.room_id = v_new_room
      AND p.property_id = v_new_property
      AND l.creator_user_id = v_owner
      AND l.status = 'OPEN';

    IF v_count <> 1 THEN
        RAISE EXCEPTION 'FAIL D01: property/room/listing chain is incomplete';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS D01: property, room and listing created with valid relationships';

    -- ---------------------------------------------------------------
    -- E. FAILURE / ATOMIC ROLLBACK TEST
    -- Deliberately fail the THIRD insert. The nested EXCEPTION block
    -- rolls back the first two inserts in that block as well.
    -- ---------------------------------------------------------------
    BEGIN
        INSERT INTO property_characteristics (
            street_number, street_name, suburb, state, postcode, unit_number,
            property_type, total_rooms, car_spots, smoking_policy, pet_policy
        )
        VALUES ('1001', 'HouseMatch Rollback Test Street ' || v_run,
                'Petersham', 'NSW', '2049', NULL,
                'Apartment', 2, 0, 'No smoking', FALSE)
        RETURNING property_id INTO v_failed_property;

        INSERT INTO room (
            room_type, num_roommates, is_furnished, has_ensuite, property_id
        )
        VALUES ('Private', 0, TRUE, FALSE, v_failed_property)
        RETURNING room_id INTO v_failed_room;

        -- This must fail: weekly_rent > 0.
        INSERT INTO listing (
            room_id, creator_user_id, weekly_rent, available_from,
            listing_date, status, num_housemates
        )
        VALUES (v_failed_room, v_owner, -50, CURRENT_DATE + 30,
                CURRENT_DATE, 'OPEN', 1);

        RAISE EXCEPTION USING ERRCODE = 'PT001', MESSAGE = 'FAIL E01: negative-rent listing unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_error_message = MESSAGE_TEXT;
        IF v_error_message NOT LIKE '%listing%' THEN
            RAISE EXCEPTION 'FAIL E01: wrong constraint caused rollback: %', v_error_message;
        END IF;
    END;

    IF v_failed_property IS NULL OR v_failed_room IS NULL
       OR EXISTS (SELECT 1 FROM property_characteristics WHERE property_id = v_failed_property)
       OR EXISTS (SELECT 1 FROM room WHERE room_id = v_failed_room) THEN
        RAISE EXCEPTION 'FAIL E01: failed listing left behind a property or room';
    END IF;
    v_passed := v_passed + 1;
    RAISE NOTICE 'PASS E01: failed third INSERT rolls back preceding property and room INSERTs';

    RAISE NOTICE '======================================================';
    RAISE NOTICE 'ALL % HOUSEMATCH AUTOMATED TESTS PASSED', v_passed;
    RAISE NOTICE 'Outer transaction will now ROLLBACK test fixtures.';
    RAISE NOTICE '======================================================';
END;
$housematch_tests$;

-- IMPORTANT: remove all fixtures, including the successful test changes.
ROLLBACK;

-- The file should finish with "ROLLBACK" in pgAdmin Messages.
-- No new tables or lasting test rows are created.
