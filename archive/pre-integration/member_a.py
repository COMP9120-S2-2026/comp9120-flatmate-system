"""Advertiser operations. Identity is supplied by Member C's future session layer."""

from psycopg import sql
from psycopg.pq import TransactionStatus


class BusinessRuleError(ValueError):
    pass


ROOM_FIELDS = ('room_type', 'property_type', 'number_rooms', 'is_furnished',
               'has_ensuite', 'car_spots', 'num_housemates', 'smoking_policy',
               'pet_policy', 'description', 'street_number', 'street_name',
               'suburb', 'state', 'postcode')


def _insert_room(conn, details):
    if set(details) != set(ROOM_FIELDS):
        raise BusinessRuleError('Room details must contain exactly: ' + ', '.join(ROOM_FIELDS))
    query = sql.SQL('INSERT INTO room ({}) VALUES ({}) RETURNING room_id').format(
        sql.SQL(',').join(map(sql.Identifier, ROOM_FIELDS)),
        sql.SQL(',').join(sql.Placeholder() for _ in ROOM_FIELDS))
    return conn.execute(query, tuple(details[f] for f in ROOM_FIELDS)).fetchone()['room_id']


def _insert_listing(conn, actor_id, room_id, weekly_rent, available_from):
    return conn.execute('''INSERT INTO listing(room_id,creator_user_id,weekly_rent,available_from)
                           VALUES (%s,%s,%s,%s) RETURNING listing_id''',
                        (room_id, actor_id, weekly_rent, available_from)).fetchone()['listing_id']


def publish_new_room(conn, actor_id, details, weekly_rent, available_from):
    """Create a room and its first OPEN listing atomically."""
    with conn.transaction():
        room_id = _insert_room(conn, details)
        listing_id = _insert_listing(conn, actor_id, room_id, weekly_rent, available_from)
    return {'room_id': room_id, 'listing_id': listing_id}


def _lock_room(conn, room_id):
    room = conn.execute('SELECT * FROM room WHERE room_id=%s FOR UPDATE', (room_id,)).fetchone()
    if not room:
        raise BusinessRuleError('Room does not exist.')
    return room


def _require_room_manager(conn, actor_id, room_id):
    latest = conn.execute('''SELECT creator_user_id FROM listing WHERE room_id=%s
                            ORDER BY listing_id DESC LIMIT 1''', (room_id,)).fetchone()
    if not latest or latest['creator_user_id'] != actor_id:
        raise BusinessRuleError('Only the latest listing creator may manage or relist this room.')


def create_listing_for_room(conn, actor_id, room_id, weekly_rent, available_from):
    with conn.transaction():
        room = _lock_room(conn, room_id)
        _require_room_manager(conn, actor_id, room_id)
        if room['allocation_status'] != 'AVAILABLE':
            raise BusinessRuleError('Room is unavailable.')
        if conn.execute("SELECT 1 FROM listing WHERE room_id=%s AND status='OPEN'", (room_id,)).fetchone():
            raise BusinessRuleError('Room already has an OPEN listing.')
        return _insert_listing(conn, actor_id, room_id, weekly_rent, available_from)


def lock_owned_open_listing(conn, actor_id, listing_id):
    """For C integration: requires an existing transaction and never commits it.

    Consistent order is Room first, Listing second. C must then lock Application.
    """
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise BusinessRuleError('An outer transaction is required.')
    found = conn.execute('SELECT room_id FROM listing WHERE listing_id=%s', (listing_id,)).fetchone()
    if not found:
        raise BusinessRuleError('Listing does not exist.')
    room = _lock_room(conn, found['room_id'])
    listing = conn.execute('SELECT * FROM listing WHERE listing_id=%s FOR UPDATE', (listing_id,)).fetchone()
    if not listing or listing['room_id'] != room['room_id']:
        raise BusinessRuleError('Listing changed; retry the operation.')
    if listing['creator_user_id'] != actor_id:
        raise BusinessRuleError('Only the listing creator may manage this listing.')
    if listing['status'] != 'OPEN':
        raise BusinessRuleError('Listing is not OPEN.')
    if room['allocation_status'] != 'AVAILABLE':
        raise BusinessRuleError('Room is unavailable.')
    return listing


def update_listing(conn, actor_id, listing_id, weekly_rent, available_from):
    with conn.transaction():
        lock_owned_open_listing(conn, actor_id, listing_id)
        return conn.execute('''UPDATE listing SET weekly_rent=%s,available_from=%s
                               WHERE listing_id=%s RETURNING *''',
                            (weekly_rent, available_from, listing_id)).fetchone()


def close_listing(conn, actor_id, listing_id):
    with conn.transaction():
        lock_owned_open_listing(conn, actor_id, listing_id)
        return conn.execute("UPDATE listing SET status='CLOSED' WHERE listing_id=%s RETURNING *",
                            (listing_id,)).fetchone()


def update_room_description(conn, actor_id, room_id, description):
    with conn.transaction():
        _lock_room(conn, room_id)
        _require_room_manager(conn, actor_id, room_id)
        return conn.execute('UPDATE room SET description=%s WHERE room_id=%s RETURNING *',
                            (description, room_id)).fetchone()


def update_room(conn, actor_id, room_id, details):
    if set(details) != set(ROOM_FIELDS):
        raise BusinessRuleError('Room details must contain exactly: ' + ', '.join(ROOM_FIELDS))
    with conn.transaction():
        _lock_room(conn, room_id)
        _require_room_manager(conn, actor_id, room_id)
        query=sql.SQL('UPDATE room SET {} WHERE room_id=%s RETURNING *').format(
            sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(f)) for f in ROOM_FIELDS))
        return conn.execute(query,tuple(details[f] for f in ROOM_FIELDS)+(room_id,)).fetchone()


def mark_filled_in_transaction(conn, actor_id, listing_id):
    """A state helper, NOT a complete application-acceptance workflow.

    Member C controls the outer transaction and updates Application in it.
    """
    listing = lock_owned_open_listing(conn, actor_id, listing_id)
    conn.execute("UPDATE listing SET status='FILLED' WHERE listing_id=%s", (listing_id,))
    conn.execute("UPDATE room SET allocation_status='UNAVAILABLE' WHERE room_id=%s", (listing['room_id'],))
    return listing['room_id']


def list_listings(conn, status=None, advertiser_id=None):
    return conn.execute('''SELECT l.*,r.room_type,r.suburb,r.is_furnished,r.has_ensuite,
                           r.smoking_policy,r.pet_policy,r.allocation_status
                           FROM listing l JOIN room r USING(room_id)
                           WHERE (%s::text IS NULL OR l.status=%s)
                             AND (%s::bigint IS NULL OR l.creator_user_id=%s)
                           ORDER BY l.weekly_rent,l.listing_id''',
                        (status, status, advertiser_id, advertiser_id)).fetchall()


def listing_detail(conn, listing_id):
    return conn.execute('''SELECT r.*,l.listing_id,l.creator_user_id,l.weekly_rent,
                           l.available_from,l.listing_date,l.status
                           FROM listing l JOIN room r USING(room_id) WHERE listing_id=%s''',
                        (listing_id,)).fetchone()
