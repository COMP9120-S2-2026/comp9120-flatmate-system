-- Member A: Room and Listing. Run after 00_user_contract.sql.
CREATE TABLE room (
    room_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_type TEXT NOT NULL CHECK (btrim(room_type) <> ''),
    property_type TEXT NOT NULL CHECK (btrim(property_type) <> ''),
    number_rooms INTEGER NOT NULL CHECK (number_rooms > 0),
    is_furnished BOOLEAN NOT NULL,
    has_ensuite BOOLEAN NOT NULL,
    car_spots INTEGER NOT NULL CHECK (car_spots >= 0),
    num_housemates INTEGER NOT NULL CHECK (num_housemates >= 0),
    smoking_policy TEXT NOT NULL CHECK (smoking_policy IN ('ALLOWED','NOT_ALLOWED')),
    pet_policy TEXT NOT NULL CHECK (pet_policy IN ('ALLOWED','NOT_ALLOWED')),
    description TEXT NOT NULL,
    street_number TEXT NOT NULL CHECK (btrim(street_number) <> ''),
    street_name TEXT NOT NULL CHECK (btrim(street_name) <> ''),
    suburb TEXT NOT NULL CHECK (btrim(suburb) <> ''),
    state TEXT NOT NULL CHECK (state IN ('NSW','VIC','QLD','SA','WA','TAS','ACT','NT')),
    postcode TEXT NOT NULL CHECK (postcode ~ '^[0-9]{4}$'),
    allocation_status TEXT NOT NULL DEFAULT 'AVAILABLE'
        CHECK (allocation_status IN ('AVAILABLE','UNAVAILABLE'))
);

CREATE TABLE listing (
    listing_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id BIGINT NOT NULL REFERENCES room(room_id) ON DELETE RESTRICT,
    creator_user_id BIGINT NOT NULL REFERENCES app_user(user_id) ON DELETE RESTRICT,
    weekly_rent NUMERIC(10,2) NOT NULL CHECK (weekly_rent > 0 AND weekly_rent < 100000000),
    available_from DATE NOT NULL,
    listing_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED','FILLED'))
);

-- Historical CLOSED/FILLED advertisements do not prevent later advertising.
CREATE UNIQUE INDEX one_open_listing_per_room ON listing(room_id) WHERE status='OPEN';
CREATE INDEX advertiser_listings ON listing(creator_user_id,listing_date DESC);

-- Cross-table rule: opening a listing requires an available physical room.
CREATE FUNCTION check_open_listing_room() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE availability TEXT;
BEGIN
    SELECT allocation_status INTO availability FROM room WHERE room_id=NEW.room_id FOR UPDATE;
    IF NEW.status='OPEN' AND availability IS DISTINCT FROM 'AVAILABLE' THEN
        RAISE EXCEPTION 'An OPEN listing requires an AVAILABLE room' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER open_listing_room BEFORE INSERT OR UPDATE OF status,room_id ON listing
    FOR EACH ROW EXECUTE FUNCTION check_open_listing_room();

CREATE FUNCTION check_unavailable_room() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.allocation_status='UNAVAILABLE' AND EXISTS
       (SELECT 1 FROM listing WHERE room_id=NEW.room_id AND status='OPEN') THEN
        RAISE EXCEPTION 'Close or fill the OPEN listing before making its room unavailable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER unavailable_room BEFORE UPDATE OF allocation_status ON room
    FOR EACH ROW EXECUTE FUNCTION check_unavailable_room();

-- Mandatory Room participation is checked at commit, so publishing can insert
-- the room first and its first listing second within the same transaction.
CREATE FUNCTION require_room_listing() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE room_ids BIGINT[]; candidate BIGINT;
BEGIN
    IF TG_TABLE_NAME='room' THEN
        room_ids:=ARRAY[NEW.room_id];
    ELSIF TG_OP='DELETE' THEN
        room_ids:=ARRAY[OLD.room_id];
    ELSE
        room_ids:=ARRAY[OLD.room_id,NEW.room_id];
    END IF;
    FOREACH candidate IN ARRAY room_ids LOOP
        -- Serialize child-removal checks on the common parent so two sessions
        -- cannot each remove one of the last two advertisements and both commit.
        PERFORM room_id FROM room WHERE room_id=candidate FOR UPDATE;
        IF EXISTS (SELECT 1 FROM room WHERE room_id=candidate) AND NOT EXISTS
           (SELECT 1 FROM listing WHERE room_id=candidate) THEN
            RAISE EXCEPTION 'Each recorded room must have at least one listing'
                USING ERRCODE='23514';
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER room_requires_listing AFTER INSERT OR UPDATE ON room
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_room_listing();
CREATE CONSTRAINT TRIGGER listing_preserves_room_participation AFTER DELETE OR UPDATE ON listing
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_room_listing();
