BEGIN;

DO $$
DECLARE
    selected_listing_id INTEGER := 1;
    selected_application_id INTEGER := 1;
BEGIN

    -- Step 1: Lock the listing and verify it is OPEN
    PERFORM 1
    FROM listing
    WHERE listing_id = selected_listing_id
      AND status = 'OPEN'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Listing is not OPEN';
    END IF;

    -- Step 2: Accept the selected application
    UPDATE application
    SET status = 'ACCEPTED'
    WHERE application_id = selected_application_id
      AND listing_id = selected_listing_id
      AND status = 'PENDING';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Application cannot be accepted';
    END IF;

    -- Step 3: Reject all other pending applications
    UPDATE application
    SET status = 'REJECTED'
    WHERE listing_id = selected_listing_id
      AND application_id <> selected_application_id
      AND status = 'PENDING';

    -- Step 4: Cancel existing confirmed viewing bookings
    UPDATE viewing_booking
    SET status = 'CANCELLED'
    WHERE listing_id = selected_listing_id
      AND status = 'CONFIRMED';

    -- Step 5: Cancel all viewing slots
    UPDATE viewing_slot
    SET status = 'CANCELLED'
    WHERE listing_id = selected_listing_id
      AND status <> 'CANCELLED';

    -- Step 6: Close the listing
    UPDATE listing
    SET status = 'CLOSED'
    WHERE listing_id = selected_listing_id;

END;
$$;

COMMIT;


BEGIN;

DO $$
DECLARE
    new_property_id INTEGER;
    new_room_id INTEGER;
BEGIN

    -- Step 1: Create the property
    INSERT INTO property_characteristics (
        street_number,
        street_name,
        suburb,
        state,
        postcode,
        unit_number,
        property_type,
        total_rooms,
        car_spots,
        smoking_policy,
        pet_policy
    )
    VALUES (
        '42',
        'Example Street',
        'Petersham',
        'NSW',
        '2049',
        '7',
        'Apartment',
        3,
        1,
        'No smoking',
        TRUE
    )
    RETURNING property_id INTO new_property_id;

    -- Step 2: Create a room at that property
    INSERT INTO room (
        room_type,
        num_roommates,
        is_furnished,
        has_ensuite,
        description,
        property_id
    )
    VALUES (
        'Private',
        0,
        TRUE,
        FALSE,
        'Spacious furnished bedroom',
        new_property_id
    )
    RETURNING room_id INTO new_room_id;

    -- Step 3: Publish the listing
    INSERT INTO listing (
        room_id,
        creator_user_id,
        weekly_rent,
        available_from,
        listing_date,
        status,
        num_housemates
    )
    VALUES (
        new_room_id,
        1,
        375.00,
        '2026-11-15',
        CURRENT_DATE,
        'OPEN',
        2
    );

END;
$$;

COMMIT;

