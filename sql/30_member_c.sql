-- Member C: Users and Applications - Yu-Han Chang (John)
-- Run after:
--   00_user_contract.sql
--   10_member_a.sql
--
-- app_user is defined in 00_user_contract.sql.
-- room and listing are defined in 10_member_a.sql.


CREATE TABLE application (
    application_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id BIGINT NOT NULL
        REFERENCES app_user(user_id)
        ON DELETE RESTRICT,

    listing_id BIGINT NOT NULL
        REFERENCES listing(listing_id)
        ON DELETE RESTRICT,

    application_date DATE NOT NULL DEFAULT CURRENT_DATE,

    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'ACCEPTED',
                'REJECTED',
                'WITHDRAWN'
            )
        ),

    message TEXT
);


-- ---------------------------------------------------------
-- Business rule:
-- A user may have at most one active application
-- for the same listing.
--
-- WITHDRAWN/REJECTED applications remain as history and
-- therefore do not stop a user applying again later.
-- ---------------------------------------------------------

CREATE UNIQUE INDEX one_pending_application_per_user_listing
ON application(user_id, listing_id)
WHERE status = 'PENDING';


-- ---------------------------------------------------------
-- Business rule:
-- Only one application can ultimately be accepted
-- for a listing.
-- ---------------------------------------------------------

CREATE UNIQUE INDEX one_accepted_application_per_listing
ON application(listing_id)
WHERE status = 'ACCEPTED';


-- Useful indexes for the main Member C operations.

CREATE INDEX applications_by_user
ON application(user_id, application_date DESC);

CREATE INDEX applications_by_listing
ON application(listing_id, application_date DESC);


-- ---------------------------------------------------------
-- Business rule:
-- New applications may only target OPEN listings.
--
-- Also prevents the advertiser from applying to their
-- own listing.
-- ---------------------------------------------------------

CREATE FUNCTION check_new_application()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    listing_status TEXT;
    listing_creator BIGINT;
BEGIN
    SELECT status, creator_user_id
      INTO listing_status, listing_creator
      FROM listing
     WHERE listing_id = NEW.listing_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Listing % does not exist', NEW.listing_id
            USING ERRCODE = '23503';
    END IF;

    IF listing_status <> 'OPEN' THEN
        RAISE EXCEPTION
            'Applications can only be submitted to OPEN listings'
            USING ERRCODE = '23514';
    END IF;

    IF listing_creator = NEW.user_id THEN
        RAISE EXCEPTION
            'A user cannot apply to their own listing'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER application_requires_open_listing
BEFORE INSERT ON application
FOR EACH ROW
EXECUTE FUNCTION check_new_application();


-- ---------------------------------------------------------
-- Business rule:
-- Application status should move through sensible states.
--
-- PENDING -> ACCEPTED / REJECTED / WITHDRAWN
--
-- Terminal states are retained as history and cannot
-- later be changed into another state.
-- ---------------------------------------------------------

CREATE FUNCTION check_application_status_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status = NEW.status THEN
        RETURN NEW;
    END IF;

    IF OLD.status <> 'PENDING' THEN
        RAISE EXCEPTION
            'Application % is already %, so its status cannot be changed',
            OLD.application_id,
            OLD.status
            USING ERRCODE = '23514';
    END IF;

    IF NEW.status NOT IN ('ACCEPTED', 'REJECTED', 'WITHDRAWN') THEN
        RAISE EXCEPTION
            'Invalid application status transition from % to %',
            OLD.status,
            NEW.status
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER valid_application_status_transition
BEFORE UPDATE OF status ON application
FOR EACH ROW
EXECUTE FUNCTION check_application_status_transition();