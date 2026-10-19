"""Application operations on the canonical schema.

Every write uses an explicit transaction, including on autocommit connections.
Shared lock order: Property -> Room -> Listing -> Application. Results use dict_row.
"""
from .member_a import BusinessRuleError, _lock_room, lock_owned_open_listing


def _lock_listing(conn, listing_id):
    hint = conn.execute('SELECT room_id FROM listing WHERE listing_id=%s', (listing_id,)).fetchone()
    if not hint:
        raise BusinessRuleError('Listing does not exist.')
    _lock_room(conn, hint['room_id'])
    return conn.execute('SELECT * FROM listing WHERE listing_id=%s FOR UPDATE', (listing_id,)).fetchone()


def submit_application(conn, user_id, listing_id, message=None):
    with conn.transaction():
        advert = _lock_listing(conn, listing_id)
        if advert['status'] != 'OPEN' or advert['creator_user_id'] == user_id:
            raise BusinessRuleError("Apply to another user's OPEN listing.")
        return conn.execute(
            'INSERT INTO application(user_id,listing_id,message) VALUES (%s,%s,%s) RETURNING *',
            (user_id, listing_id, message)).fetchone()


def list_user_applications(conn, user_id):
    return conn.execute('''SELECT a.*,l.weekly_rent,l.available_from,l.status AS listing_status,
        r.room_type,p.suburb FROM application a JOIN listing l USING(listing_id)
        JOIN room r USING(room_id) JOIN property_characteristics p USING(property_id)
        WHERE a.user_id=%s ORDER BY a.application_id''',
        (user_id,)).fetchall()


def list_listing_applicants(conn, advertiser_user_id, listing_id):
    advert = conn.execute('SELECT creator_user_id FROM listing WHERE listing_id=%s', (listing_id,)).fetchone()
    if not advert or advert['creator_user_id'] != advertiser_user_id:
        raise BusinessRuleError('Only the listing creator may view applicants.')
    return conn.execute('''SELECT a.*,u.first_name,u.last_name,u.email,u.phone_num,u.bio
        FROM application a JOIN app_user u USING(user_id)
        WHERE a.listing_id=%s ORDER BY a.application_id''', (listing_id,)).fetchall()


def _lock_application(conn, application_id):
    hint = conn.execute('SELECT listing_id FROM application WHERE application_id=%s', (application_id,)).fetchone()
    if not hint:
        raise BusinessRuleError('Application does not exist.')
    advert = _lock_listing(conn, hint['listing_id'])
    application = conn.execute('SELECT * FROM application WHERE application_id=%s FOR UPDATE',
                               (application_id,)).fetchone()
    if not application or application['status'] != 'PENDING':
        raise BusinessRuleError('Only PENDING applications can be changed.')
    return advert, application


def withdraw_application(conn, user_id, application_id):
    with conn.transaction():
        _, application = _lock_application(conn, application_id)
        if application['user_id'] != user_id:
            raise BusinessRuleError('Only the applicant may withdraw this application.')
        return conn.execute("UPDATE application SET status='WITHDRAWN' WHERE application_id=%s RETURNING *",
                            (application_id,)).fetchone()


def reject_application(conn, advertiser_user_id, application_id):
    with conn.transaction():
        advert, _ = _lock_application(conn, application_id)
        if advert['creator_user_id'] != advertiser_user_id:
            raise BusinessRuleError('Only the listing creator may reject applications.')
        return conn.execute("UPDATE application SET status='REJECTED' WHERE application_id=%s RETURNING *",
                            (application_id,)).fetchone()


def accept_application(conn, advertiser_user_id, application_id):
    with conn.transaction():
        advert, application = _lock_application(conn, application_id)
        lock_owned_open_listing(conn, advertiser_user_id, advert['listing_id'])
        conn.execute("UPDATE application SET status='ACCEPTED' WHERE application_id=%s", (application_id,))
        conn.execute("""UPDATE application SET status='REJECTED'
            WHERE listing_id=%s AND application_id<>%s AND status='PENDING'""",
            (advert['listing_id'], application_id))
        # Match the merged SQL transaction: cancel viewings, then close the advert.
        conn.execute("UPDATE viewing_booking SET status='CANCELLED' WHERE listing_id=%s AND status='CONFIRMED'",
                     (advert['listing_id'],))
        conn.execute("UPDATE viewing_slot SET status='CANCELLED' WHERE listing_id=%s AND status<>'CANCELLED'",
                     (advert['listing_id'],))
        conn.execute("UPDATE listing SET status='CLOSED' WHERE listing_id=%s",(advert['listing_id'],))
        return conn.execute('SELECT * FROM application WHERE application_id=%s', (application_id,)).fetchone()
