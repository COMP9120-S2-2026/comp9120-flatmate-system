"""Preference, search, shortlist and viewing operations on the shared schema."""
from .member_a import BusinessRuleError, lock_owned_open_listing
from .member_c import _lock_listing


def list_profiles(conn, user_id):
    return conn.execute('''SELECT p.*,ARRAY(SELECT preferred_suburb FROM preferred_suburb s
        WHERE (s.user_id,s.profile_name)=(p.user_id,p.profile_name) ORDER BY preferred_suburb) AS suburbs
        FROM preference_profile p WHERE user_id=%s ORDER BY profile_name''', (user_id,)).fetchall()


def save_profile(conn, user_id, profile_name, min_rent, max_rent,
                 desired_move_in_date=None, smoking_preference='Any',
                 pet_preference=None, suburbs=()):
    with conn.transaction():
        conn.execute('SELECT 1 FROM app_user WHERE user_id=%s FOR UPDATE', (user_id,))
        profile = conn.execute('''INSERT INTO preference_profile
            (user_id,profile_name,min_rent,max_rent,desired_move_in_date,smoking_preference,pet_preference)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id,profile_name) DO UPDATE
            SET min_rent=EXCLUDED.min_rent,max_rent=EXCLUDED.max_rent,
                desired_move_in_date=EXCLUDED.desired_move_in_date,
                smoking_preference=EXCLUDED.smoking_preference,pet_preference=EXCLUDED.pet_preference
            RETURNING *''',
            (user_id,profile_name,min_rent,max_rent,desired_move_in_date,smoking_preference,pet_preference)).fetchone()
        conn.execute('DELETE FROM preferred_suburb WHERE user_id=%s AND profile_name=%s', (user_id,profile_name))
        for suburb in sorted(set(suburbs)):
            conn.execute('INSERT INTO preferred_suburb VALUES (%s,%s,%s)', (user_id,profile_name,suburb))
        return profile


def delete_profile(conn, user_id, profile_name):
    with conn.transaction():
        conn.execute('SELECT 1 FROM app_user WHERE user_id=%s FOR UPDATE', (user_id,))
        conn.execute('DELETE FROM preferred_suburb WHERE user_id=%s AND profile_name=%s',
                     (user_id,profile_name))
        return conn.execute('DELETE FROM preference_profile WHERE user_id=%s AND profile_name=%s RETURNING *',
                            (user_id,profile_name)).fetchone()


def search_listings(conn, user_id, profile_name):
    if not conn.execute('SELECT 1 FROM preference_profile WHERE user_id=%s AND profile_name=%s',
                        (user_id,profile_name)).fetchone():
        raise BusinessRuleError('Preference profile does not exist.')
    return conn.execute('''SELECT l.*,pc.suburb,r.room_type,pc.smoking_policy,pc.pet_policy
        FROM listing l JOIN room r USING(room_id) JOIN property_characteristics pc USING(property_id)
        CROSS JOIN preference_profile p WHERE p.user_id=%s AND p.profile_name=%s
        AND l.status='OPEN' AND l.creator_user_id<>p.user_id
        AND l.weekly_rent BETWEEN p.min_rent AND p.max_rent
        AND (p.desired_move_in_date IS NULL OR l.available_from<=p.desired_move_in_date)
        AND (p.smoking_preference='Any' OR p.smoking_preference=pc.smoking_policy
             OR (p.smoking_preference='Outdoor only' AND pc.smoking_policy='No smoking'))
        AND (p.pet_preference IS DISTINCT FROM TRUE OR pc.pet_policy=TRUE)
        AND (NOT EXISTS (SELECT 1 FROM preferred_suburb s
                WHERE (s.user_id,s.profile_name)=(p.user_id,p.profile_name))
             OR EXISTS (SELECT 1 FROM preferred_suburb s
                WHERE (s.user_id,s.profile_name)=(p.user_id,p.profile_name) AND s.preferred_suburb=pc.suburb))
        ORDER BY l.weekly_rent,l.listing_id''', (user_id,profile_name)).fetchall()


def save_listing(conn, user_id, listing_id, preference_rank=None):
    with conn.transaction():
        return conn.execute('INSERT INTO saves VALUES (%s,%s,%s) RETURNING *',
                            (user_id,listing_id,preference_rank)).fetchone()


def unsave_listing(conn, user_id, listing_id):
    with conn.transaction():
        return conn.execute('DELETE FROM saves WHERE user_id=%s AND listing_id=%s RETURNING *',
                            (user_id,listing_id)).fetchone()


def list_saved(conn, user_id):
    return conn.execute('''SELECT s.*,l.weekly_rent,l.status,p.suburb FROM saves s
        JOIN listing l USING(listing_id) JOIN room r USING(room_id) JOIN property_characteristics p USING(property_id)
        WHERE s.user_id=%s ORDER BY s.preference_rank NULLS LAST,s.listing_id''', (user_id,)).fetchall()


def create_slot(conn, actor_id, listing_id, viewing_timestamp):
    with conn.transaction():
        lock_owned_open_listing(conn, actor_id, listing_id)
        return conn.execute('INSERT INTO viewing_slot(listing_id,viewing_timestamp) VALUES (%s,%s) RETURNING *',
                            (listing_id,viewing_timestamp)).fetchone()


def book_viewing(conn, user_id, listing_id, viewing_timestamp):
    with conn.transaction():
        _lock_listing(conn, listing_id)
        return conn.execute('''INSERT INTO viewing_booking(user_id,listing_id,viewing_timestamp)
            VALUES (%s,%s,%s) RETURNING *''', (user_id,listing_id,viewing_timestamp)).fetchone()


def _lock_booking(conn, booking_id):
    hint = conn.execute('SELECT listing_id FROM viewing_booking WHERE booking_id=%s', (booking_id,)).fetchone()
    if not hint:
        raise BusinessRuleError('Booking does not exist.')
    advert = _lock_listing(conn, hint['listing_id'])
    booking = conn.execute('SELECT * FROM viewing_booking WHERE booking_id=%s FOR UPDATE', (booking_id,)).fetchone()
    if not booking:
        raise BusinessRuleError('Booking does not exist.')
    return advert, booking


def cancel_booking(conn, actor_id, booking_id):
    with conn.transaction():
        advert, booking = _lock_booking(conn, booking_id)
        if actor_id not in (advert['creator_user_id'],booking['user_id']):
            raise BusinessRuleError('Only the booker or advertiser may cancel.')
        return conn.execute("UPDATE viewing_booking SET status='CANCELLED' WHERE booking_id=%s RETURNING *",
                            (booking_id,)).fetchone()


def reschedule_booking(conn, user_id, booking_id, viewing_timestamp):
    with conn.transaction():
        _, booking = _lock_booking(conn, booking_id)
        if booking['user_id'] != user_id or booking['status'] != 'CONFIRMED':
            raise BusinessRuleError('Only the booker may reschedule a confirmed booking.')
        return conn.execute('UPDATE viewing_booking SET viewing_timestamp=%s WHERE booking_id=%s RETURNING *',
                            (viewing_timestamp,booking_id)).fetchone()
