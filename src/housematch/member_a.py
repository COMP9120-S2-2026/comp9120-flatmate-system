"""Advertiser operations for the report's Property -> Room -> Listing schema."""
from psycopg import sql
from psycopg.pq import TransactionStatus


class BusinessRuleError(ValueError):
    pass


PROPERTY_FIELDS=('street_number','street_name','suburb','state','postcode','unit_number',
                 'property_type','total_rooms','car_spots','smoking_policy','pet_policy')
ROOM_FIELDS=('room_type','num_roommates','is_furnished','has_ensuite','description')


def _insert(conn, table, fields, values, key):
    query=sql.SQL('INSERT INTO {} ({}) VALUES ({}) RETURNING {}').format(
        sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,fields)),
        sql.SQL(',').join(sql.Placeholder() for _ in fields),sql.Identifier(key))
    return conn.execute(query,tuple(values[f] for f in fields)).fetchone()[key]


def _insert_room(conn, details):
    if set(details)==set(ROOM_FIELDS)|{'property_id'}:
        property_id=details['property_id']
    elif set(details)==set(ROOM_FIELDS)|set(PROPERTY_FIELDS):
        property_id=_insert(conn,'property_characteristics',PROPERTY_FIELDS,details,'property_id')
    else:
        raise BusinessRuleError('Supply room fields plus property_id, or room fields plus all property fields.')
    return _insert(conn,'room',ROOM_FIELDS+('property_id',),dict(details,property_id=property_id),'room_id')


def _insert_listing(conn,actor_id,room_id,weekly_rent,available_from,num_housemates=0):
    return conn.execute('''INSERT INTO listing(room_id,creator_user_id,weekly_rent,available_from,num_housemates)
        VALUES (%s,%s,%s,%s,%s) RETURNING listing_id''',
        (room_id,actor_id,weekly_rent,available_from,num_housemates)).fetchone()['listing_id']


def publish_new_room(conn,actor_id,details,weekly_rent,available_from,num_housemates=0):
    with conn.transaction():
        room_id=_insert_room(conn,details)
        listing_id=_insert_listing(conn,actor_id,room_id,weekly_rent,available_from,num_housemates)
    return dict(room_id=room_id,listing_id=listing_id)


def _lock_room(conn,room_id):
    hint=conn.execute('SELECT property_id FROM room WHERE room_id=%s',(room_id,)).fetchone()
    if not hint:
        raise BusinessRuleError('Room does not exist.')
    conn.execute('SELECT 1 FROM property_characteristics WHERE property_id=%s FOR UPDATE',(hint['property_id'],))
    room=conn.execute('SELECT * FROM room WHERE room_id=%s FOR UPDATE',(room_id,)).fetchone()
    if not room or room['property_id']!=hint['property_id']:
        raise BusinessRuleError('Room changed; retry the operation.')
    return room


def _require_room_manager(conn,actor_id,room_id):
    latest=conn.execute('SELECT creator_user_id FROM listing WHERE room_id=%s ORDER BY listing_id DESC LIMIT 1',
                        (room_id,)).fetchone()
    if not latest or latest['creator_user_id']!=actor_id:
        raise BusinessRuleError('Only the latest listing creator may manage or relist this room.')


def create_listing_for_room(conn,actor_id,room_id,weekly_rent,available_from,num_housemates=0):
    with conn.transaction():
        _lock_room(conn,room_id)
        _require_room_manager(conn,actor_id,room_id)
        if conn.execute("SELECT 1 FROM listing WHERE room_id=%s AND status IN ('OPEN','PAUSED')",(room_id,)).fetchone():
            raise BusinessRuleError('Room already has an active listing.')
        return _insert_listing(conn,actor_id,room_id,weekly_rent,available_from,num_housemates)


def lock_owned_open_listing(conn,actor_id,listing_id):
    """Requires caller's transaction; lock Property, Room, Listing in that order."""
    if conn.info.transaction_status!=TransactionStatus.INTRANS:
        raise BusinessRuleError('An outer transaction is required.')
    hint=conn.execute('SELECT room_id FROM listing WHERE listing_id=%s',(listing_id,)).fetchone()
    if not hint:
        raise BusinessRuleError('Listing does not exist.')
    _lock_room(conn,hint['room_id'])
    advert=conn.execute('SELECT * FROM listing WHERE listing_id=%s FOR UPDATE',(listing_id,)).fetchone()
    if not advert or advert['room_id']!=hint['room_id']:
        raise BusinessRuleError('Listing changed; retry the operation.')
    if advert['creator_user_id']!=actor_id:
        raise BusinessRuleError('Only the listing creator may manage this listing.')
    if advert['status']!='OPEN':
        raise BusinessRuleError('Listing is not OPEN.')
    return advert


def update_listing(conn,actor_id,listing_id,weekly_rent,available_from):
    with conn.transaction():
        lock_owned_open_listing(conn,actor_id,listing_id)
        return conn.execute('UPDATE listing SET weekly_rent=%s,available_from=%s WHERE listing_id=%s RETURNING *',
                            (weekly_rent,available_from,listing_id)).fetchone()


def close_listing(conn,actor_id,listing_id):
    with conn.transaction():
        lock_owned_open_listing(conn,actor_id,listing_id)
        return conn.execute("UPDATE listing SET status='CLOSED' WHERE listing_id=%s RETURNING *",(listing_id,)).fetchone()


def update_room_description(conn,actor_id,room_id,description):
    with conn.transaction():
        _lock_room(conn,room_id)
        _require_room_manager(conn,actor_id,room_id)
        return conn.execute('UPDATE room SET description=%s WHERE room_id=%s RETURNING *',(description,room_id)).fetchone()


def update_room(conn,actor_id,room_id,details):
    if set(details) not in (set(ROOM_FIELDS)|{'property_id'},set(ROOM_FIELDS)|set(PROPERTY_FIELDS)):
        raise BusinessRuleError('Supply the same room/property fields as publishing.')
    with conn.transaction():
        room=_lock_room(conn,room_id)
        _require_room_manager(conn,actor_id,room_id)
        if 'property_id' in details:
            if details['property_id']!=room['property_id']:
                raise BusinessRuleError('Moving rooms between properties is not supported.')
        else:
            existing=conn.execute('SELECT * FROM property_characteristics WHERE property_id=%s',(room['property_id'],)).fetchone()
            changed=any(existing[f]!=details[f] for f in PROPERTY_FIELDS)
            if changed:
                # Shared physical attributes must not be changed by an unrelated advertiser.
                others=conn.execute('''SELECT 1 FROM room r JOIN LATERAL
                    (SELECT creator_user_id FROM listing WHERE room_id=r.room_id ORDER BY listing_id DESC LIMIT 1) l ON TRUE
                    WHERE r.property_id=%s AND l.creator_user_id<>%s LIMIT 1''',(room['property_id'],actor_id)).fetchone()
                if others:
                    raise BusinessRuleError('Shared property changes require agreement with the other advertisers.')
                assignments=sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(f)) for f in PROPERTY_FIELDS)
                conn.execute(sql.SQL('UPDATE property_characteristics SET {} WHERE property_id=%s').format(assignments),
                             tuple(details[f] for f in PROPERTY_FIELDS)+(room['property_id'],))
        assignments=sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(f)) for f in ROOM_FIELDS)
        return conn.execute(sql.SQL('UPDATE room SET {} WHERE room_id=%s RETURNING *').format(assignments),
                            tuple(details[f] for f in ROOM_FIELDS)+(room_id,)).fetchone()


def list_listings(conn,status=None,advertiser_id=None):
    return conn.execute('''SELECT l.*,r.room_type,r.is_furnished,r.has_ensuite,
        p.suburb,p.smoking_policy,p.pet_policy FROM listing l JOIN room r USING(room_id)
        JOIN property_characteristics p USING(property_id)
        WHERE (%s::text IS NULL OR l.status=%s) AND (%s::integer IS NULL OR l.creator_user_id=%s)
        ORDER BY l.weekly_rent,l.listing_id''',(status,status,advertiser_id,advertiser_id)).fetchall()


def listing_detail(conn,listing_id):
    return conn.execute('''SELECT p.*,r.room_id,r.room_type,r.num_roommates,r.is_furnished,r.has_ensuite,
        r.description,l.listing_id,l.creator_user_id,l.weekly_rent,l.available_from,l.listing_date,l.status,l.num_housemates
        FROM listing l JOIN room r USING(room_id) JOIN property_characteristics p USING(property_id)
        WHERE listing_id=%s''',(listing_id,)).fetchone()
