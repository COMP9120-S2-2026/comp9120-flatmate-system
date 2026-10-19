
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
           OR NEW.user_id IS DISTINCT FROM OLD.user_id
           OR NEW.booking_date IS DISTINCT FROM OLD.booking_date THEN

            RAISE EXCEPTION 'Booking listing, user and original date are immutable';

        END IF;

        IF NEW.status <> 'CONFIRMED'
           OR (OLD.status = 'CONFIRMED' AND NEW.viewing_timestamp=OLD.viewing_timestamp) THEN
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

    IF slot_status IS DISTINCT FROM 'AVAILABLE'
       OR NEW.viewing_timestamp <= (CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Sydney') THEN
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

    IF TG_OP='UPDATE' AND OLD.status='CONFIRMED'
       AND NEW.viewing_timestamp<>OLD.viewing_timestamp THEN
        UPDATE viewing_slot SET status='AVAILABLE'
        WHERE listing_id=OLD.listing_id AND viewing_timestamp=OLD.viewing_timestamp
          AND status='BOOKED';
    END IF;

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

-- Report section 2.4: every registered user has at least one profile.
CREATE FUNCTION create_default_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO preference_profile(user_id,profile_name,min_rent,max_rent,smoking_preference)
    VALUES (NEW.user_id,'Default',0,99999999,'Any');
    RETURN NEW;
END $$;
CREATE TRIGGER default_profile AFTER INSERT ON app_user
    FOR EACH ROW EXECUTE FUNCTION create_default_profile();

CREATE FUNCTION preserve_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM 1 FROM app_user WHERE user_id=OLD.user_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM app_user WHERE user_id=OLD.user_id)
       AND NOT EXISTS (SELECT 1 FROM preference_profile WHERE user_id=OLD.user_id) THEN
        RAISE EXCEPTION 'Each user must retain at least one preference profile' USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER profile_participation AFTER DELETE OR UPDATE ON preference_profile
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION preserve_profile();

-- Report section 2.4: publishing creates the room and first listing atomically.
CREATE FUNCTION require_room_listing() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidates INTEGER[]; candidate INTEGER;
BEGIN
    IF TG_TABLE_NAME='room' THEN candidates:=ARRAY[NEW.room_id];
    ELSIF TG_OP='DELETE' THEN candidates:=ARRAY[OLD.room_id];
    ELSE candidates:=ARRAY[OLD.room_id,NEW.room_id]; END IF;
    FOREACH candidate IN ARRAY candidates LOOP
        PERFORM 1 FROM room WHERE room_id=candidate FOR UPDATE;
        IF EXISTS (SELECT 1 FROM room WHERE room_id=candidate)
           AND NOT EXISTS (SELECT 1 FROM listing WHERE room_id=candidate) THEN
            RAISE EXCEPTION 'Each recorded room must have at least one listing' USING ERRCODE='23514';
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER room_participation AFTER INSERT OR UPDATE ON room
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_room_listing();
CREATE CONSTRAINT TRIGGER listing_participation AFTER DELETE OR UPDATE ON listing
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_room_listing();

CREATE FUNCTION application_lifecycle() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.user_id<>OLD.user_id OR NEW.listing_id<>OLD.listing_id THEN
        RAISE EXCEPTION 'Application user and listing are immutable' USING ERRCODE='23514';
    END IF;
    IF NEW.status<>OLD.status AND OLD.status<>'PENDING' THEN
        RAISE EXCEPTION 'Only PENDING applications can change status' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER application_lifecycle_rules BEFORE UPDATE ON application
    FOR EACH ROW EXECUTE FUNCTION application_lifecycle();

CREATE FUNCTION listing_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.room_id<>OLD.room_id OR NEW.creator_user_id<>OLD.creator_user_id THEN
        RAISE EXCEPTION 'Listing room and creator are immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER listing_identity_rules BEFORE UPDATE ON listing
    FOR EACH ROW EXECUTE FUNCTION listing_identity();

-- An accepted application must not commit with an open listing or pending rivals.
CREATE FUNCTION verify_acceptance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target INTEGER; advert_status TEXT;
BEGIN
    target:=COALESCE(NEW.listing_id,OLD.listing_id);
    SELECT status INTO advert_status FROM listing WHERE listing_id=target FOR UPDATE;
    IF EXISTS (SELECT 1 FROM application WHERE listing_id=target AND status='ACCEPTED') THEN
        IF advert_status IS DISTINCT FROM 'CLOSED' OR EXISTS (
            SELECT 1 FROM application WHERE listing_id=target AND status='PENDING'
        ) THEN
            RAISE EXCEPTION 'Acceptance must close the listing and reject pending rivals in one transaction'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER application_acceptance AFTER INSERT OR UPDATE ON application
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION verify_acceptance();
CREATE CONSTRAINT TRIGGER listing_acceptance AFTER UPDATE ON listing
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION verify_acceptance();
