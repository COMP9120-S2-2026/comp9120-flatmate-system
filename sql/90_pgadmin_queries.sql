-- Open the Query Tool on the housematch database.
-- Run individual statements or select the entire script.
-- These queries only read data.

SELECT current_database(), current_user;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT * FROM public.app_user ORDER BY user_id;
SELECT * FROM public.room ORDER BY room_id;
SELECT * FROM public.listing ORDER BY listing_id;

SELECT l.listing_id, p.suburb, r.room_type, l.weekly_rent,
       l.available_from, l.status, u.first_name AS advertiser
FROM public.listing AS l
JOIN public.room AS r ON r.room_id = l.room_id
JOIN public.property_characteristics AS p ON p.property_id=r.property_id
JOIN public.app_user AS u ON u.user_id = l.creator_user_id
WHERE l.status = 'OPEN'
ORDER BY l.weekly_rent, l.listing_id;
