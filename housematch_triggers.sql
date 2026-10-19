
-- Trigger 1: 
CREATE OR REPLACE FUNCTION check_accepted_application()
RETURNS TRIGGER AS $$
BEGIN

    IF NEW.status = 'ACCEPTED' THEN

        PERFORM 1
        FROM listing
        WHERE listing_id = NEW.listing_id
        FOR UPDATE;

        IF EXISTS (
            SELECT 1
            FROM application
            WHERE listing_id = NEW.listing_id
              AND status = 'ACCEPTED'
              AND application_id <> NEW.application_id
        ) THEN

            RAISE EXCEPTION 'This listing already has an accepted application';

        END IF;

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enforce_one_accepted_application
ON application;

CREATE TRIGGER enforce_one_accepted_application
BEFORE INSERT OR UPDATE OF status, listing_id
ON application
FOR EACH ROW
EXECUTE FUNCTION check_accepted_application();

--trigger 2
CREATE OR REPLACE FUNCTION check_listing_open()
RETURNS TRIGGER AS $$
DECLARE
    listing_status VARCHAR(30);
BEGIN

    SELECT status
    INTO listing_status
    FROM listing
    WHERE listing_id = NEW.listing_id
    FOR UPDATE;

    IF listing_status IS DISTINCT FROM 'OPEN' THEN
        RAISE EXCEPTION 'Applications can only be submitted to OPEN listings';
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enforce_open_listing
ON application;

CREATE TRIGGER enforce_open_listing
BEFORE INSERT OR UPDATE OF listing_id
ON application
FOR EACH ROW
EXECUTE FUNCTION check_listing_open();

-- trigger 3
CREATE OR REPLACE FUNCTION check_viewing_booking()
RETURNS TRIGGER AS $$
DECLARE
    slot_status VARCHAR(30);
BEGIN

    IF TG_OP = 'UPDATE' THEN

        IF NEW.listing_id IS DISTINCT FROM OLD.listing_id
           OR NEW.viewing_timestamp IS DISTINCT FROM OLD.viewing_timestamp THEN

            RAISE EXCEPTION 'Cannot change the viewing slot of an existing booking';

        END IF;

        IF OLD.status = 'CONFIRMED'
           OR NEW.status <> 'CONFIRMED' THEN
            RETURN NEW;
        END IF;

    ELSIF NEW.status <> 'CONFIRMED' THEN
        RETURN NEW;
    END IF;

    -- Only allow confirmed bookings for OPEN listings.
    -- Lock the listing first so booking and closure cannot race.
    PERFORM 1
    FROM listing
    WHERE listing_id = NEW.listing_id
      AND status = 'OPEN'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cannot book a viewing for a listing that is not OPEN';
    END IF;

    SELECT status
    INTO slot_status
    FROM viewing_slot
    WHERE listing_id = NEW.listing_id
      AND viewing_timestamp = NEW.viewing_timestamp
    FOR UPDATE;

    IF slot_status IS DISTINCT FROM 'AVAILABLE' THEN
        RAISE EXCEPTION 'Viewing slot is not available';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM viewing_booking
        WHERE listing_id = NEW.listing_id
          AND viewing_timestamp = NEW.viewing_timestamp
          AND status = 'CONFIRMED'
          AND booking_id IS DISTINCT FROM NEW.booking_id
    ) THEN

        RAISE EXCEPTION 'This viewing slot is already booked';

    END IF;

    UPDATE viewing_slot
    SET status = 'BOOKED'
    WHERE listing_id = NEW.listing_id
      AND viewing_timestamp = NEW.viewing_timestamp;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS enforce_available_viewing_slot
ON viewing_booking;

CREATE TRIGGER enforce_available_viewing_slot
BEFORE INSERT OR UPDATE OF status, listing_id, viewing_timestamp
ON viewing_booking
FOR EACH ROW
EXECUTE FUNCTION check_viewing_booking();

--trigger 4

CREATE OR REPLACE FUNCTION release_cancelled_viewing_slot()
RETURNS TRIGGER AS $$
BEGIN

    UPDATE viewing_slot
    SET status = 'AVAILABLE'
    WHERE listing_id = NEW.listing_id
      AND viewing_timestamp = NEW.viewing_timestamp
      AND status = 'BOOKED';

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS release_slot_on_cancellation
ON viewing_booking;

CREATE TRIGGER release_slot_on_cancellation
AFTER UPDATE OF status
ON viewing_booking
FOR EACH ROW
WHEN (
    OLD.status = 'CONFIRMED'
    AND NEW.status = 'CANCELLED'
)
EXECUTE FUNCTION release_cancelled_viewing_slot();






--trigger 5: ensure viewing_timestamp for viewing slot is in the future and ensure that a viewing slot cannot be created for a closed listing
CREATE OR REPLACE FUNCTION check_valid_viewing_slot()
RETURNS TRIGGER AS $$
DECLARE
    listing_status VARCHAR(30);
BEGIN

    -- Check the listing's current status
    SELECT status INTO listing_status
    FROM listing
    WHERE listing_id = NEW.listing_id
    FOR UPDATE;

    -- Reject viewing slots for closed listings
    IF listing_status = 'CLOSED' THEN
        RAISE EXCEPTION 'Cannot add viewing slot to a closed listing';
    END IF;

    -- Reject viewing slots scheduled in the past
    IF NEW.viewing_timestamp <= LOCALTIMESTAMP THEN
        RAISE EXCEPTION 'Viewing timestamp must be in the future';
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER enforce_valid_viewing_slot
BEFORE INSERT OR UPDATE OF listing_id, viewing_timestamp
ON viewing_slot
FOR EACH ROW
EXECUTE FUNCTION check_valid_viewing_slot();


-- Trigger 6: Ensure only one active listing per room

CREATE OR REPLACE FUNCTION check_one_active_listing()
RETURNS TRIGGER AS $$
BEGIN

    -- Only check listings that are OPEN or PAUSED
    IF NEW.status IN ('OPEN', 'PAUSED') THEN

        -- Lock the room to prevent concurrent conflicting listings
        PERFORM 1
        FROM room
        WHERE room_id = NEW.room_id
        FOR UPDATE;

        -- Check whether another active listing exists for this room
        IF EXISTS (
            SELECT 1
            FROM listing
            WHERE room_id = NEW.room_id
              AND status IN ('OPEN', 'PAUSED')
              AND listing_id IS DISTINCT FROM NEW.listing_id
        ) THEN

            RAISE EXCEPTION 'This room already has an active listing';

        END IF;

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER enforce_one_active_listing
BEFORE INSERT OR UPDATE OF room_id, status
ON listing
FOR EACH ROW
EXECUTE FUNCTION check_one_active_listing();


-- Trigger 7: Ensure a property cannot exceed its total_rooms

CREATE OR REPLACE FUNCTION check_property_room_limit()
RETURNS TRIGGER AS $$
DECLARE
    max_rooms INTEGER;
    existing_rooms INTEGER;
BEGIN

    -- Lock the property and retrieve its room limit
    SELECT total_rooms INTO max_rooms
    FROM property_characteristics
    WHERE property_id = NEW.property_id
    FOR UPDATE;

    -- Count existing rooms, excluding the room being updated
    SELECT COUNT(*) INTO existing_rooms
    FROM room
    WHERE property_id = NEW.property_id
      AND room_id IS DISTINCT FROM NEW.room_id;

    -- Reject if the property is already at capacity
    IF existing_rooms >= max_rooms THEN
        RAISE EXCEPTION 'Property cannot exceed its total number of rooms';
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER enforce_property_room_limit
BEFORE INSERT OR UPDATE OF property_id
ON room
FOR EACH ROW
EXECUTE FUNCTION check_property_room_limit();

-- Trigger 8: Prevent reducing total_rooms below existing room count

CREATE OR REPLACE FUNCTION check_total_rooms_limit()
RETURNS TRIGGER AS $$
DECLARE
    existing_rooms INTEGER;
BEGIN

    -- Count rooms currently belonging to the property
    SELECT COUNT(*) INTO existing_rooms
    FROM room
    WHERE property_id = NEW.property_id;

    -- Reject if the new limit is smaller than the existing room count
    IF NEW.total_rooms < existing_rooms THEN
        RAISE EXCEPTION 'Total rooms cannot be less than the number of existing rooms';
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER enforce_total_rooms_limit
BEFORE UPDATE OF total_rooms
ON property_characteristics
FOR EACH ROW
EXECUTE FUNCTION check_total_rooms_limit();

-- Trigger 9: Prevent users from applying to their own listings

CREATE OR REPLACE FUNCTION check_own_listing_application()
RETURNS TRIGGER AS $$
BEGIN

    -- Check whether the applicant owns the listing
    IF EXISTS (
        SELECT 1
        FROM listing
        WHERE listing_id = NEW.listing_id
          AND creator_user_id = NEW.user_id
    ) THEN

        RAISE EXCEPTION 'Users cannot apply to their own listings';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER prevent_own_listing_application
BEFORE INSERT OR UPDATE OF user_id, listing_id
ON application
FOR EACH ROW
EXECUTE FUNCTION check_own_listing_application();

-- Trigger 10: Prevent users from booking multiple viewing slots
-- for the same listing

CREATE OR REPLACE FUNCTION check_one_viewing_per_listing()
RETURNS TRIGGER AS $$
BEGIN

    -- Only check confirmed bookings
    IF NEW.status = 'CONFIRMED' THEN

        -- Lock the listing to prevent concurrent conflicting bookings
        PERFORM 1
        FROM listing
        WHERE listing_id = NEW.listing_id
        FOR UPDATE;

        -- Check whether the user already has a confirmed booking
        IF EXISTS (
            SELECT 1
            FROM viewing_booking
            WHERE user_id = NEW.user_id
              AND listing_id = NEW.listing_id
              AND status = 'CONFIRMED'
              AND booking_id IS DISTINCT FROM NEW.booking_id
        ) THEN

            RAISE EXCEPTION
                'User already has a confirmed viewing booking for this listing';

        END IF;

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER enforce_one_viewing_per_listing
BEFORE INSERT OR UPDATE OF user_id, listing_id, status
ON viewing_booking
FOR EACH ROW
EXECUTE FUNCTION check_one_viewing_per_listing();