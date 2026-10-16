"""
Member C - Users and Applications.

Responsibilities:
- submit applications
- view a user's applications
- view applicants for a listing
- withdraw applications
- reject applications
- accept applications

The acceptance workflow is the main multi-step transaction for
the HouseMatch project.
"""


def submit_application(conn, user_id, listing_id, message=None):
    """
    Submit a new application to an OPEN listing.

    Database constraints/triggers enforce:
    - listing must be OPEN
    - user cannot apply to own listing
    - user cannot have another PENDING application for same listing

    Returns:
        dict containing the newly created application.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO application (
                user_id,
                listing_id,
                message
            )
            VALUES (%s, %s, %s)
            RETURNING
                application_id,
                user_id,
                listing_id,
                application_date,
                status,
                message
            """,
            (user_id, listing_id, message),
        )

        row = cur.fetchone()

    conn.commit()

    return _application_row(row)


def list_user_applications(conn, user_id):
    """
    Return all applications submitted by one user.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.application_id,
                a.user_id,
                a.listing_id,
                a.application_date,
                a.status,
                a.message,
                l.weekly_rent,
                l.available_from,
                l.status AS listing_status,
                r.room_type,
                r.suburb
            FROM application AS a
            JOIN listing AS l
              ON l.listing_id = a.listing_id
            JOIN room AS r
              ON r.room_id = l.room_id
            WHERE a.user_id = %s
            ORDER BY a.application_date DESC,
                     a.application_id DESC
            """,
            (user_id,),
        )

        columns = [description.name for description in cur.description]

        return [
            dict(zip(columns, row))
            for row in cur.fetchall()
        ]


def list_listing_applicants(conn, advertiser_user_id, listing_id):
    """
    Return applications for a listing, but only if that listing
    belongs to the advertiser requesting the data.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT creator_user_id
            FROM listing
            WHERE listing_id = %s
            """,
            (listing_id,),
        )

        listing = cur.fetchone()

        if listing is None:
            raise ValueError("Listing does not exist")

        if listing[0] != advertiser_user_id:
            raise PermissionError(
                "Only the listing creator can view its applicants"
            )

        cur.execute(
            """
            SELECT
                a.application_id,
                a.application_date,
                a.status,
                a.message,
                u.user_id,
                u.first_name,
                u.last_name,
                u.email,
                u.phone_num,
                u.bio
            FROM application AS a
            JOIN app_user AS u
              ON u.user_id = a.user_id
            WHERE a.listing_id = %s
            ORDER BY a.application_date,
                     a.application_id
            """,
            (listing_id,),
        )

        columns = [description.name for description in cur.description]

        return [
            dict(zip(columns, row))
            for row in cur.fetchall()
        ]


def withdraw_application(conn, user_id, application_id):
    """
    A user can withdraw their own PENDING application.
    """

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE application
                   SET status = 'WITHDRAWN'
                 WHERE application_id = %s
                   AND user_id = %s
                   AND status = 'PENDING'
                RETURNING
                    application_id,
                    user_id,
                    listing_id,
                    application_date,
                    status,
                    message
                """,
                (application_id, user_id),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    "Application does not exist, does not belong to this "
                    "user, or is no longer PENDING"
                )

        conn.commit()

        return _application_row(row)

    except Exception:
        conn.rollback()
        raise


def reject_application(conn, advertiser_user_id, application_id):
    """
    Reject a PENDING application.

    Only the creator of the corresponding listing can reject it.
    """

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.listing_id,
                    a.status,
                    l.creator_user_id
                FROM application AS a
                JOIN listing AS l
                  ON l.listing_id = a.listing_id
                WHERE a.application_id = %s
                FOR UPDATE
                """,
                (application_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("Application does not exist")

            listing_id, status, creator_user_id = row

            if creator_user_id != advertiser_user_id:
                raise PermissionError(
                    "Only the listing creator can reject applications"
                )

            if status != "PENDING":
                raise ValueError(
                    "Only PENDING applications can be rejected"
                )

            cur.execute(
                """
                UPDATE application
                   SET status = 'REJECTED'
                 WHERE application_id = %s
                RETURNING
                    application_id,
                    user_id,
                    listing_id,
                    application_date,
                    status,
                    message
                """,
                (application_id,),
            )

            updated = cur.fetchone()

        conn.commit()

        return _application_row(updated)

    except Exception:
        conn.rollback()
        raise


def accept_application(conn, advertiser_user_id, application_id):
    """
    Accept one application.

    This is the main HouseMatch multi-step transaction.

    Transaction:
    1. Lock the application.
    2. Lock its listing.
    3. Verify application is PENDING.
    4. Verify listing is OPEN.
    5. Verify current user owns the listing.
    6. Mark listing FILLED.
    7. Mark its room UNAVAILABLE.
    8. Mark selected application ACCEPTED.
    9. Reject all other PENDING applications.

    If any step fails, the complete operation is rolled back.

    Row locks also prevent two advertisers/sessions from accepting
    competing applications for the same listing concurrently.
    """

    try:
        with conn.cursor() as cur:

            # Lock selected application first.
            cur.execute(
                """
                SELECT
                    application_id,
                    listing_id,
                    status
                FROM application
                WHERE application_id = %s
                FOR UPDATE
                """,
                (application_id,),
            )

            application = cur.fetchone()

            if application is None:
                raise ValueError("Application does not exist")

            _, listing_id, application_status = application

            if application_status != "PENDING":
                raise ValueError(
                    "Only a PENDING application can be accepted"
                )

            # Lock the listing.
            #
            # This is important for concurrency:
            # another transaction trying to accept an applicant for the same
            # listing must wait until this transaction finishes.
            cur.execute(
                """
                SELECT
                    room_id,
                    creator_user_id,
                    status
                FROM listing
                WHERE listing_id = %s
                FOR UPDATE
                """,
                (listing_id,),
            )

            listing = cur.fetchone()

            if listing is None:
                raise ValueError("Listing does not exist")

            room_id, creator_user_id, listing_status = listing

            if creator_user_id != advertiser_user_id:
                raise PermissionError(
                    "Only the listing creator can accept applications"
                )

            if listing_status != "OPEN":
                raise ValueError(
                    "Applications can only be accepted for an OPEN listing"
                )

            # IMPORTANT:
            # Member A's room trigger prevents an AVAILABLE room becoming
            # UNAVAILABLE while an OPEN listing still exists.
            #
            # Therefore listing must become FILLED first.
            cur.execute(
                """
                UPDATE listing
                   SET status = 'FILLED'
                 WHERE listing_id = %s
                """,
                (listing_id,),
            )

            # Now Member A's trigger allows the room to become unavailable.
            cur.execute(
                """
                UPDATE room
                   SET allocation_status = 'UNAVAILABLE'
                 WHERE room_id = %s
                """,
                (room_id,),
            )

            # Accept the selected application.
            cur.execute(
                """
                UPDATE application
                   SET status = 'ACCEPTED'
                 WHERE application_id = %s
                """,
                (application_id,),
            )

            # Reject all remaining active applications.
            cur.execute(
                """
                UPDATE application
                   SET status = 'REJECTED'
                 WHERE listing_id = %s
                   AND application_id <> %s
                   AND status = 'PENDING'
                """,
                (listing_id, application_id),
            )

            cur.execute(
                """
                SELECT
                    application_id,
                    user_id,
                    listing_id,
                    application_date,
                    status,
                    message
                FROM application
                WHERE application_id = %s
                """,
                (application_id,),
            )

            result = cur.fetchone()

        conn.commit()

        return _application_row(result)

    except Exception:
        conn.rollback()
        raise


def _application_row(row):
    """
    Convert the basic application query result into a dictionary.
    """

    if row is None:
        return None

    return {
        "application_id": row[0],
        "user_id": row[1],
        "listing_id": row[2],
        "application_date": row[3],
        "status": row[4],
        "message": row[5],
    }