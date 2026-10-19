-- ============================================================
-- HouseMatch - 03_sample_data.sql
-- COMP9120 Group Project
-- Fictional users, addresses and listings for development/testing.
-- ============================================================
-- Run AFTER 01_schema.sql and 02_triggers.sql.
-- Run ONCE against an EMPTY HouseMatch database.
-- This script does NOT delete existing data.
-- IDs below assume the identity sequences begin at 1.
-- If any statement fails, execute ROLLBACK before trying again.
-- ============================================================

BEGIN;

-- Safety check: do not accidentally seed an already populated database.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM app_user)
       OR EXISTS (SELECT 1 FROM property_characteristics)
       OR EXISTS (SELECT 1 FROM preference_profile)
       OR EXISTS (SELECT 1 FROM preferred_suburb)
       OR EXISTS (SELECT 1 FROM room)
       OR EXISTS (SELECT 1 FROM listing)
       OR EXISTS (SELECT 1 FROM saves)
       OR EXISTS (SELECT 1 FROM application)
       OR EXISTS (SELECT 1 FROM viewing_slot)
       OR EXISTS (SELECT 1 FROM viewing_booking) THEN
        RAISE EXCEPTION 'Sample data script requires empty HouseMatch tables.';
    END IF;
END;
$$;

-- Ensure IDs are predictable even if previous test rows were deleted.
ALTER TABLE app_user ALTER COLUMN user_id RESTART WITH 1;
ALTER TABLE property_characteristics ALTER COLUMN property_id RESTART WITH 1;
ALTER TABLE room ALTER COLUMN room_id RESTART WITH 1;
ALTER TABLE listing ALTER COLUMN listing_id RESTART WITH 1;
ALTER TABLE application ALTER COLUMN application_id RESTART WITH 1;
ALTER TABLE viewing_booking ALTER COLUMN booking_id RESTART WITH 1;

-- 1. USERS (14)
-- Users 1-6 mainly create listings; users 7-14 mainly search for rooms.
INSERT INTO app_user (first_name, last_name, phone_num, email, bio)
VALUES
    ('Olivia', 'Chen', '0400 000 001', 'olivia.chen@example.com', 'Works in design; enjoys a quiet, tidy household.'),
    ('Liam', 'Patel', '0400 000 002', 'liam.patel@example.com', 'Software developer and weekend cyclist.'),
    ('Sophie', 'Nguyen', '0400 000 003', 'sophie.nguyen@example.com', 'Postgraduate student who enjoys cooking.'),
    ('Noah', 'Williams', '0400 000 004', 'noah.williams@example.com', 'Works in hospitality and loves live music.'),
    ('Ava', 'Thompson', '0400 000 005', 'ava.thompson@example.com', 'Marketing professional and keen runner.'),
    ('Ethan', 'Brown', '0400 000 006', 'ethan.brown@example.com', 'Teacher looking for considerate housemates.'),
    ('Mia', 'Robinson', '0400 000 007', 'mia.robinson@example.com', 'USYD student looking near campus.'),
    ('Jack', 'Wilson', '0400 000 008', 'jack.wilson@example.com', 'Graduate engineer who works in the CBD.'),
    ('Isla', 'Martin', '0400 000 009', 'isla.martin@example.com', 'Graphic designer; values natural light.'),
    ('Lucas', 'Davis', '0400 000 010', 'lucas.davis@example.com', 'New to Sydney; flexible with move-in dates.'),
    ('Grace', 'Lee', '0400 000 011', 'grace.lee@example.com', 'Animal lover seeking a pet-friendly home.'),
    ('Arjun', 'Shah', '0400 000 012', 'arjun.shah@example.com', 'Research student who prefers a quiet home.'),
    ('Emily', 'Clarke', '0400 000 013', 'emily.clarke@example.com', 'Healthcare worker looking for easy transport.'),
    ('Zara', 'Ahmed', '0400 000 014', 'zara.ahmed@example.com', 'Creative professional seeking an Inner West share house.');

-- 2. PROPERTY CHARACTERISTICS (10)
-- All addresses are fictional examples; state/postcode combinations are plausible.
INSERT INTO property_characteristics
    (street_number, street_name, suburb, state, postcode, unit_number,
     property_type, total_rooms, car_spots, smoking_policy, pet_friendly)
VALUES
    ('24', 'Bridge Road', 'Glebe', 'NSW', '2037', '3B', 'Apartment', 3, 1, 'No smoking', TRUE),
    ('18', 'King Street', 'Newtown', 'NSW', '2042', NULL, 'Townhouse', 4, 0, 'Outdoor only', FALSE),
    ('7', 'Ross Street', 'Forest Lodge', 'NSW', '2037', NULL, 'House', 5, 1, 'No smoking', TRUE),
    ('51', 'Abercrombie Street', 'Chippendale', 'NSW', '2008', '12', 'Apartment', 2, 0, 'No smoking', FALSE),
    ('12', 'Cleveland Street', 'Surry Hills', 'NSW', '2010', '4', 'Apartment', 3, 0, 'Outdoor only', TRUE),
    ('6', 'Lawson Street', 'Redfern', 'NSW', '2016', NULL, 'Townhouse', 3, 0, 'No smoking', TRUE),
    ('90', 'Parramatta Road', 'Annandale', 'NSW', '2038', '2', 'Apartment', 2, 1, 'No smoking', FALSE),
    ('14', 'Australia Street', 'Camperdown', 'NSW', '2050', NULL, 'House', 4, 1, 'Outdoor only', TRUE),
    ('30', 'Enmore Road', 'Enmore', 'NSW', '2042', '5', 'Apartment', 2, 0, 'No smoking', TRUE),
    ('25', 'Mitchell Road', 'Alexandria', 'NSW', '2015', NULL, 'Townhouse', 3, 1, 'No smoking', TRUE);

-- 3. PREFERENCE PROFILES (10)
-- References user IDs assigned in the first INSERT.
INSERT INTO preference_profile
    (user_id, profile_name, min_rent, max_rent, desired_move_in_date,
     smoking_preference, pet_friendly)
VALUES
    (7, 'Near Uni', 300.00, 450.00, '2026-11-01', 'No smoking', TRUE),
    (7, 'Budget', 250.00, 360.00, '2026-12-01', 'Any', FALSE),
    (8, 'Inner West', 300.00, 450.00, '2026-11-05', 'Outdoor only', TRUE),
    (9, 'Close to CBD', 350.00, 550.00, '2026-11-20', 'No smoking', FALSE),
    (10, 'Flexible', 280.00, 430.00, '2026-11-01', 'Any', NULL),
    (11, 'Pet Friendly', 350.00, 600.00, '2026-12-01', 'Outdoor only', TRUE),
    (12, 'Quiet Home', 280.00, 450.00, '2026-11-15', 'No smoking', FALSE),
    (13, 'Uni Commute', 300.00, 500.00, '2026-12-01', 'No smoking', TRUE),
    (14, 'Creative Neighbourhoods', 280.00, 420.00, '2026-11-01', 'Outdoor only', TRUE),
    (14, 'Summer Move', 350.00, 600.00, '2027-01-01', 'Any', NULL);

-- 4. PREFERRED SUBURBS (23)
INSERT INTO preferred_suburb (user_id, profile_name, preferred_suburb)
VALUES
    (7, 'Near Uni', 'Glebe'),
    (7, 'Near Uni', 'Forest Lodge'),
    (7, 'Near Uni', 'Camperdown'),
    (7, 'Budget', 'Newtown'),
    (7, 'Budget', 'Enmore'),
    (8, 'Inner West', 'Newtown'),
    (8, 'Inner West', 'Annandale'),
    (8, 'Inner West', 'Glebe'),
    (9, 'Close to CBD', 'Surry Hills'),
    (9, 'Close to CBD', 'Chippendale'),
    (9, 'Close to CBD', 'Redfern'),
    (10, 'Flexible', 'Newtown'),
    (10, 'Flexible', 'Alexandria'),
    (11, 'Pet Friendly', 'Redfern'),
    (11, 'Pet Friendly', 'Forest Lodge'),
    (12, 'Quiet Home', 'Camperdown'),
    (12, 'Quiet Home', 'Annandale'),
    (13, 'Uni Commute', 'Glebe'),
    (13, 'Uni Commute', 'Chippendale'),
    (14, 'Creative Neighbourhoods', 'Enmore'),
    (14, 'Creative Neighbourhoods', 'Newtown'),
    (14, 'Summer Move', 'Surry Hills'),
    (14, 'Summer Move', 'Alexandria');

-- 5. ROOMS (12)
INSERT INTO room
    (room_type, num_roommates, is_furnished, has_ensuite, description, property_id)
VALUES
    ('Private', 0, TRUE, TRUE, 'Bright master bedroom with private bathroom.', 1),
    ('Private', 0, FALSE, FALSE, 'Quiet room overlooking a shared courtyard.', 1),
    ('Private', 0, TRUE, FALSE, 'Furnished double room close to cafes and trains.', 2),
    ('Private', 0, FALSE, FALSE, 'Spacious unfurnished room in a friendly house.', 3),
    ('Private', 0, TRUE, FALSE, 'Compact furnished room with good natural light.', 4),
    ('Private', 0, TRUE, TRUE, 'Large ensuite room near Central Station.', 5),
    ('Private', 0, FALSE, FALSE, 'Room in a pet-friendly Redfern townhouse.', 6),
    ('Private', 0, TRUE, FALSE, 'Furnished room with an off-street parking space.', 7),
    ('Private', 0, TRUE, FALSE, 'Sunny room with desk and wardrobe.', 8),
    ('Private', 0, FALSE, FALSE, 'Room close to Enmore restaurants and music venues.', 9),
    ('Private', 0, TRUE, TRUE, 'Modern ensuite room in a townhouse.', 10),
    ('Shared', 1, TRUE, FALSE, 'Shared bedroom with one other occupant.', 3);

-- 6. LISTINGS (12)
-- Listing 7 begins OPEN so applications can be inserted; it is CLOSED below.
INSERT INTO listing
    (room_id, creator_user_id, weekly_rent, available_from, listing_date,
     status, num_housemates)
VALUES
    (1, 1, 430.00, '2026-11-01', '2026-10-10', 'OPEN', 2),
    (2, 1, 340.00, '2026-11-05', '2026-10-11', 'OPEN', 2),
    (3, 2, 385.00, '2026-11-15', '2026-10-12', 'OPEN', 3),
    (4, 3, 360.00, '2026-12-01', '2026-10-13', 'OPEN', 4),
    (5, 4, 460.00, '2026-11-20', '2026-10-08', 'PAUSED', 1),
    (6, 5, 520.00, '2026-11-10', '2026-10-05', 'OPEN', 2),
    (7, 6, 410.00, '2026-11-08', '2026-10-06', 'OPEN', 2),
    (8, 1, 390.00, '2026-12-05', '2026-10-14', 'OPEN', 1),
    (9, 3, 370.00, '2026-11-18', '2026-10-12', 'OPEN', 3),
    (10, 2, 345.00, '2026-12-10', '2026-10-15', 'OPEN', 1),
    (11, 4, 550.00, '2026-12-01', '2026-10-15', 'OPEN', 2),
    (12, 3, 295.00, '2026-11-25', '2026-10-15', 'OPEN', 4);

-- 7. SAVED LISTINGS (18)
INSERT INTO saves (user_id, listing_id, preference_rank)
VALUES
    (7, 1, 1), (7, 3, 2), (7, 9, 3),
    (8, 1, 1), (8, 6, 2), (8, 12, 3),
    (9, 4, 1), (9, 2, 2),
    (10, 2, 1), (10, 8, 2),
    (11, 6, 1), (11, 10, 2),
    (12, 3, 1), (12, 11, 2),
    (13, 8, 1), (13, 1, 2),
    (14, 9, 1), (14, 4, 2);

-- 8. APPLICATIONS (20)
-- All are inserted as PENDING against OPEN listings.
-- Listing 7 will subsequently demonstrate an accepted application.
INSERT INTO application (user_id, listing_id, application_date, message)
VALUES
    (7, 1, '2026-10-15', 'I study nearby and would love to inspect the room.'),
    (8, 1, '2026-10-15', 'I am tidy and can move in early November.'),
    (9, 1, '2026-10-16', 'Is the room still available?'),
    (10, 2, '2026-10-15', 'The location is ideal for my commute.'),
    (11, 2, '2026-10-16', 'I would be interested in arranging a viewing.'),
    (7, 3, '2026-10-16', 'I like the location and the furnished room.'),
    (12, 3, '2026-10-16', 'I am a quiet and respectful housemate.'),
    (13, 3, '2026-10-17', 'The move-in date works well for me.'),
    (9, 4, '2026-10-16', 'I would like to know more about the house.'),
    (14, 4, '2026-10-17', 'I enjoy shared cooking and a relaxed household.'),
    (8, 6, '2026-10-15', 'The ensuite room looks great.'),
    (11, 6, '2026-10-16', 'I would love to arrange an inspection.'),
    (10, 7, '2026-10-10', 'I can move in on the advertised date.'),
    (12, 7, '2026-10-11', 'Please consider my application.'),
    (13, 8, '2026-10-16', 'The parking space would be helpful.'),
    (14, 9, '2026-10-16', 'I like the location and the shared living space.'),
    (7, 9, '2026-10-17', 'I would be happy to arrange a viewing.'),
    (11, 10, '2026-10-17', 'I am interested in the room.'),
    (12, 11, '2026-10-17', 'I would like to inspect the ensuite room.'),
    (8, 12, '2026-10-17', 'Is the shared room available in November?');

-- Historical example: one accepted application, one rejected.
-- Listing 7 is closed after its cancelled viewing slot is inserted.
-- Trigger 1 permits the first acceptance and would reject a second one.
UPDATE application
SET status = 'ACCEPTED'
WHERE user_id = 10 AND listing_id = 7;

UPDATE application
SET status = 'REJECTED'
WHERE user_id = 12 AND listing_id = 7;

-- 9. VIEWING SLOTS (19)
-- Viewing times use days relative to CURRENT_DATE so Trigger 5
-- always receives future timestamps, including on later reruns.
-- Slots that will be booked are inserted as AVAILABLE.
-- Trigger 3 automatically changes their status to BOOKED later.
INSERT INTO viewing_slot (listing_id, viewing_timestamp, status)
VALUES
    (1, (CURRENT_DATE + 14 + TIME '11:00:00'), 'AVAILABLE'),
    (1, (CURRENT_DATE + 15 + TIME '15:00:00'), 'AVAILABLE'),
    (1, (CURRENT_DATE + 16 + TIME '18:00:00'), 'AVAILABLE'),
    (2, (CURRENT_DATE + 17 + TIME '17:30:00'), 'AVAILABLE'),
    (2, (CURRENT_DATE + 18 + TIME '12:00:00'), 'AVAILABLE'),
    (3, (CURRENT_DATE + 20 + TIME '10:00:00'), 'AVAILABLE'),
    (3, (CURRENT_DATE + 21 + TIME '14:00:00'), 'AVAILABLE'),
    (4, (CURRENT_DATE + 27 + TIME '11:00:00'), 'AVAILABLE'),
    (4, (CURRENT_DATE + 28 + TIME '13:00:00'), 'AVAILABLE'),
    (5, (CURRENT_DATE + 23 + TIME '10:00:00'), 'CANCELLED'),
    (6, (CURRENT_DATE + 14 + TIME '12:00:00'), 'AVAILABLE'),
    (6, (CURRENT_DATE + 15 + TIME '16:00:00'), 'AVAILABLE'),
    (7, (CURRENT_DATE + 7 + TIME '14:00:00'), 'CANCELLED'),
    (8, (CURRENT_DATE + 34 + TIME '13:00:00'), 'AVAILABLE'),
    (9, (CURRENT_DATE + 23 + TIME '11:00:00'), 'AVAILABLE'),
    (9, (CURRENT_DATE + 25 + TIME '17:00:00'), 'AVAILABLE'),
    (10, (CURRENT_DATE + 38 + TIME '18:00:00'), 'AVAILABLE'),
    (11, (CURRENT_DATE + 28 + TIME '11:00:00'), 'AVAILABLE'),
    (12, (CURRENT_DATE + 29 + TIME '14:00:00'), 'AVAILABLE');

-- Listing 7 is now CLOSED after its historical cancelled slot was created.
UPDATE listing
SET status = 'CLOSED'
WHERE listing_id = 7;

-- 10. VIEWING BOOKINGS (7)
-- The default booking status is CONFIRMED.
-- Trigger 3 marks each associated slot BOOKED.
INSERT INTO viewing_booking
    (user_id, listing_id, viewing_timestamp, booking_date)
VALUES
    (7, 1, (CURRENT_DATE + 14 + TIME '11:00:00'), '2026-10-16'),
    (10, 2, (CURRENT_DATE + 17 + TIME '17:30:00'), '2026-10-16'),
    (12, 3, (CURRENT_DATE + 20 + TIME '10:00:00'), '2026-10-17'),
    (9, 4, (CURRENT_DATE + 27 + TIME '11:00:00'), '2026-10-17'),
    (11, 6, (CURRENT_DATE + 14 + TIME '12:00:00'), '2026-10-17'),
    (14, 9, (CURRENT_DATE + 23 + TIME '11:00:00'), '2026-10-17'),
    (13, 8, (CURRENT_DATE + 34 + TIME '13:00:00'), '2026-10-17');

-- Demonstrate Trigger 4: cancelling booking 6 releases its slot.
UPDATE viewing_booking
SET status = 'CANCELLED'
WHERE booking_id = 6;

COMMIT;

-- ============================================================
-- READ-ONLY VERIFICATION QUERIES (safe to rerun)
-- ============================================================

-- Counts for all 10 tables.
SELECT 'app_user' AS table_name, COUNT(*) AS row_count FROM app_user
UNION ALL SELECT 'property_characteristics', COUNT(*) FROM property_characteristics
UNION ALL SELECT 'preference_profile', COUNT(*) FROM preference_profile
UNION ALL SELECT 'preferred_suburb', COUNT(*) FROM preferred_suburb
UNION ALL SELECT 'room', COUNT(*) FROM room
UNION ALL SELECT 'listing', COUNT(*) FROM listing
UNION ALL SELECT 'saves', COUNT(*) FROM saves
UNION ALL SELECT 'application', COUNT(*) FROM application
UNION ALL SELECT 'viewing_slot', COUNT(*) FROM viewing_slot
UNION ALL SELECT 'viewing_booking', COUNT(*) FROM viewing_booking
ORDER BY table_name;

-- Check the booking/slot status pairs.
SELECT vb.booking_id, vb.user_id, vb.listing_id,
       vb.viewing_timestamp, vb.status AS booking_status,
       vs.status AS slot_status
FROM viewing_booking AS vb
JOIN viewing_slot AS vs
  ON vs.listing_id = vb.listing_id
 AND vs.viewing_timestamp = vb.viewing_timestamp
ORDER BY vb.booking_id;

-- Check the accepted application and closed listing example.
SELECT a.application_id, a.user_id, a.listing_id,
       a.status AS application_status, l.status AS listing_status
FROM application AS a
JOIN listing AS l ON l.listing_id = a.listing_id
WHERE a.listing_id = 7
ORDER BY a.application_id;
