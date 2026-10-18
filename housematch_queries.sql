-- ============================================================
-- HouseMatch - 04_queries.sql
-- COMP9120 Group Project
-- Eight representative, READ-ONLY PostgreSQL queries.
--
-- Run after 01_schema.sql, 02_triggers.sql and 03_sample_data.sql.
-- Each SELECT can be executed independently in pgAdmin.
-- Example IDs and filters are based on 03_sample_data.sql.
-- Results may change after running the transaction demonstrations.
-- ============================================================


-- ============================================================
-- QUERY 1: Search OPEN listings by suburb and maximum weekly rent
-- Concepts: JOIN, WHERE, ORDER BY
-- Example: rooms in Glebe costing no more than $450 per week.
-- ============================================================
SELECT
    l.listing_id,
    p.suburb,
    p.street_name,
    r.room_type,
    r.is_furnished,
    l.weekly_rent,
    l.available_from
FROM listing AS l
JOIN room AS r
    ON r.room_id = l.room_id
JOIN property_characteristics AS p
    ON p.property_id = r.property_id
WHERE l.status = 'OPEN'
  AND p.suburb = 'Glebe'
  AND l.weekly_rent <= 450.00
ORDER BY l.weekly_rent ASC, l.listing_id;


-- ============================================================
-- QUERY 2: View full details of a particular listing
-- Concepts: multiple JOINs, aliases, filtering
-- Example: listing 3.
-- ============================================================
SELECT
    l.listing_id,
    l.status AS listing_status,
    l.weekly_rent,
    l.available_from,
    l.listing_date,
    l.num_housemates,
    r.room_id,
    r.room_type,
    r.num_roommates,
    r.is_furnished,
    r.has_ensuite,
    r.description AS room_description,
    p.property_id,
    p.unit_number,
    p.street_number,
    p.street_name,
    p.suburb,
    p.state,
    p.postcode,
    p.property_type,
    p.total_rooms,
    p.car_spots,
    p.smoking_policy,
    p.pet_friendly,
    u.user_id AS creator_user_id,
    u.first_name AS creator_first_name,
    u.last_name AS creator_last_name
FROM listing AS l
JOIN room AS r
    ON r.room_id = l.room_id
JOIN property_characteristics AS p
    ON p.property_id = r.property_id
JOIN app_user AS u
    ON u.user_id = l.creator_user_id
WHERE l.listing_id = 3;


-- ============================================================
-- QUERY 3: Match OPEN listings to a user's preference profile
-- Concepts: multiple JOINs, composite-key relationship, conditions
-- Example: user 13, profile 'Uni Commute'.
--
-- Interpretation used for matching:
-- * Listing rent must fall within the profile's min/max range.
-- * Property must be in at least one preferred suburb.
-- * A room must be available by the desired move-in date.
-- * 'No smoking' requires a no-smoking property.
-- * 'Outdoor only' allows no smoking or outdoor-only smoking.
-- * A profile requiring pet-friendly housing matches only properties
--   with pet_friendly = TRUE.
-- * FALSE/NULL profile pet_friendly imposes no pet-friendly filter.
-- ============================================================
SELECT
    pp.user_id,
    pp.profile_name,
    l.listing_id,
    p.suburb,
    r.room_type,
    l.weekly_rent,
    l.available_from,
    p.smoking_policy,
    p.pet_friendly
FROM preference_profile AS pp
JOIN preferred_suburb AS ps
    ON ps.user_id = pp.user_id
   AND ps.profile_name = pp.profile_name
JOIN property_characteristics AS p
    ON p.suburb = ps.preferred_suburb
JOIN room AS r
    ON r.property_id = p.property_id
JOIN listing AS l
    ON l.room_id = r.room_id
WHERE pp.user_id = 13
  AND pp.profile_name = 'Uni Commute'
  AND l.status = 'OPEN'
  AND l.weekly_rent BETWEEN pp.min_rent AND pp.max_rent
  AND (
      pp.desired_move_in_date IS NULL
      OR l.available_from <= pp.desired_move_in_date
  )
  AND (
      pp.smoking_preference = 'Any'
      OR (pp.smoking_preference = 'No smoking'
          AND p.smoking_policy = 'No smoking')
      OR (pp.smoking_preference = 'Outdoor only'
          AND p.smoking_policy IN ('No smoking', 'Outdoor only'))
  )
  AND (
      pp.pet_friendly IS DISTINCT FROM TRUE
      OR p.pet_friendly = TRUE
  )
ORDER BY l.weekly_rent ASC, l.listing_id;


-- ============================================================
-- QUERY 4: Show a user's saved listings by preference rank
-- Concepts: JOIN, ORDER BY, NULLS LAST
-- Example: user 7.
-- Includes saved listings even if they are now PAUSED or CLOSED.
-- ============================================================
SELECT
    s.user_id,
    s.preference_rank,
    l.listing_id,
    l.status AS listing_status,
    p.suburb,
    r.room_type,
    l.weekly_rent,
    l.available_from
FROM saves AS s
JOIN listing AS l
    ON l.listing_id = s.listing_id
JOIN room AS r
    ON r.room_id = l.room_id
JOIN property_characteristics AS p
    ON p.property_id = r.property_id
WHERE s.user_id = 7
ORDER BY s.preference_rank ASC NULLS LAST, l.listing_id;


-- ============================================================
-- QUERY 5: Show applications received for a listing
-- Concepts: JOIN, filtering, ORDER BY
-- Example: listing 1.
-- ============================================================
SELECT
    a.application_id,
    a.listing_id,
    a.application_date,
    a.status AS application_status,
    a.message,
    u.user_id AS applicant_user_id,
    u.first_name AS applicant_first_name,
    u.last_name AS applicant_last_name
FROM application AS a
JOIN app_user AS u
    ON u.user_id = a.user_id
WHERE a.listing_id = 1
ORDER BY a.application_date ASC, a.application_id;


-- ============================================================
-- QUERY 6: Find future AVAILABLE viewing slots for an OPEN listing
-- Concepts: JOIN, date/time filtering, ORDER BY
-- Example: listing 3 (one of its sample slots is already booked).
-- ============================================================
SELECT
    vs.listing_id,
    vs.viewing_timestamp,
    vs.status AS slot_status
FROM viewing_slot AS vs
JOIN listing AS l
    ON l.listing_id = vs.listing_id
WHERE vs.listing_id = 3
  AND l.status = 'OPEN'
  AND vs.status = 'AVAILABLE'
  AND vs.viewing_timestamp > CURRENT_TIMESTAMP
ORDER BY vs.viewing_timestamp ASC;


-- ============================================================
-- QUERY 7: Average weekly rent and listing count by suburb
-- Concepts: GROUP BY, AVG, COUNT, ROUND, ORDER BY
-- Counts only OPEN listings (the currently advertised market).
-- ============================================================
SELECT
    p.suburb,
    p.state,
    COUNT(*) AS open_listing_count,
    ROUND(AVG(l.weekly_rent), 2) AS average_weekly_rent,
    MIN(l.weekly_rent) AS minimum_weekly_rent,
    MAX(l.weekly_rent) AS maximum_weekly_rent
FROM listing AS l
JOIN room AS r
    ON r.room_id = l.room_id
JOIN property_characteristics AS p
    ON p.property_id = r.property_id
WHERE l.status = 'OPEN'
GROUP BY p.suburb, p.state
ORDER BY average_weekly_rent ASC, p.suburb;


-- ============================================================
-- QUERY 8: Find listings that have received no applications
-- Concepts: correlated subquery, NOT EXISTS
-- Includes all listing statuses. In the seed data, listing 5 is
-- PAUSED and has no applications; filtering only OPEN listings
-- would therefore return no rows in the initial seed dataset.
-- ============================================================
SELECT
    l.listing_id,
    l.status AS listing_status,
    p.suburb,
    r.room_type,
    l.weekly_rent,
    l.listing_date
FROM listing AS l
JOIN room AS r
    ON r.room_id = l.room_id
JOIN property_characteristics AS p
    ON p.property_id = r.property_id
WHERE NOT EXISTS (
    SELECT 1
    FROM application AS a
    WHERE a.listing_id = l.listing_id
)
ORDER BY l.listing_id;
