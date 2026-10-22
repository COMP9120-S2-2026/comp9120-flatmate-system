
import psycopg
from getpass import getpass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from psycopg.errors import UniqueViolation


# DATABASE CONFIGURATION

DB_HOST = "localhost"
DB_NAME = "housematch"  
DB_USER = "postgres"
DB_PORT = 5432

# Olivia Chen from your sample data
CURRENT_USER_ID = 5


# DATABASE FUNCTIONS

def get_user_name(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT first_name, last_name
            FROM app_user
            WHERE user_id = %s;
        """, (user_id,))

        user = cursor.fetchone()

    if user is None:
        raise ValueError("User not found.")

    return f"{user[0]} {user[1]}"


# FEATURE FUNCTIONS


# PREFERENCE MANAGEMENT

def view_preference_profiles(conn, user_id, active_profile):

    # Retrieve the user's preference profiles
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT profile_name,
                   min_rent,
                   max_rent,
                   desired_move_in_date,
                   smoking_preference,
                   pet_friendly
            FROM preference_profile
            WHERE user_id = %s
            ORDER BY profile_name;
        """, (user_id,))

        profiles = cursor.fetchall()

    if not profiles:
        print("\nYou have no preference profiles yet.")
        input("\nPress Enter to go back...")
        return active_profile

    while True:
        print("\n========== YOUR PREFERENCE PROFILES ==========")

        for i, profile in enumerate(profiles, start=1):
            print(f"{i}. {profile[0]}")

        print("\n0. Back")

        choice = input("\nSelect a profile: ").strip()

        if choice == "0":
            return active_profile

        if not choice.isdigit() or not 1 <= int(choice) <= len(profiles):
            print("\nInvalid choice. Please try again.")
            continue

        # Retrieve the selected profile
        profile = profiles[int(choice) - 1]

        profile_name = profile[0]
        min_rent = profile[1]
        max_rent = profile[2]
        move_in_date = profile[3]
        smoking = profile[4]
        pets = profile[5]

        # Retrieve the suburbs associated with this profile
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT preferred_suburb
                FROM preferred_suburb
                WHERE user_id = %s
                  AND profile_name = %s
                ORDER BY preferred_suburb;
            """, (user_id, profile_name))

            suburbs = cursor.fetchall()

        suburb_names = ", ".join(row[0] for row in suburbs)

        if not suburb_names:
            suburb_names = "None specified"

        if move_in_date is None:
            move_in_text = "Not specified"
        else:
            move_in_text = move_in_date.strftime("%d/%m/%Y")

        if pets is None:
            pet_text = "No preference"
        elif pets:
            pet_text = "Yes"
        else:
            pet_text = "No"

        # Display the selected profile
        print(f"\n========== {profile_name.upper()} ==========")
        print(f"Minimum weekly rent: ${min_rent:.2f}")
        print(f"Maximum weekly rent: ${max_rent:.2f}")
        print(f"Preferred suburbs: {suburb_names}")
        print(f"Desired move-in date: {move_in_text}")
        print(f"Smoking preference: {smoking}")
        print(f"Pet friendly: {pet_text}")

        while True:
            print("\n1. Set as Active Profile")
            print("0. Back")

            action = input("\nEnter your choice: ").strip()

            if action == "1":
                active_profile = profile_name
                print(f"\n'{profile_name}' is now your active profile.")
                input("\nPress Enter to continue...")
                break

            elif action == "0":
                break

            else:
                print("\nInvalid choice. Please try again.")



def create_preference_profile(conn, user_id):
    print("\n========== CREATE PREFERENCE PROFILE ==========")

    # Get the profile name
    profile_name = input("\nProfile name: ").strip()

    if not profile_name or len(profile_name) > 100:
        print("Profile name must be between 1 and 100 characters.")
        return

    # Get the rent range
    try:
        min_rent = Decimal(input("Minimum weekly rent: ").strip())
        max_rent = Decimal(input("Maximum weekly rent: ").strip())
    except InvalidOperation:
        print("Rent must be a valid number.")
        return

    if (
        not min_rent.is_finite()
        or not max_rent.is_finite()
        or min_rent < 0
        or max_rent < min_rent
        or max_rent > Decimal("99999999.99")
        or min_rent.as_tuple().exponent < -2
        or max_rent.as_tuple().exponent < -2
    ):
        print("Invalid rent range.")
        return

    # Get preferred suburbs
    suburbs_input = input(
        "Preferred suburbs (comma-separated): "
    )

    suburbs = []
    seen = set()

    for suburb in suburbs_input.split(","):
        suburb = suburb.strip()

        if suburb and suburb.lower() not in seen:
            suburbs.append(suburb)
            seen.add(suburb.lower())

    if any(len(suburb) > 100 for suburb in suburbs):
        print("Suburb names must be 100 characters or fewer.")
        return

    # Get desired move-in date
    date_input = input(
        "Desired move-in date (YYYY-MM-DD, optional): "
    ).strip()

    if date_input:
        try:
            move_in_date = date.fromisoformat(date_input)
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD.")
            return
    else:
        move_in_date = None

    # Get smoking preference
    print("\nSmoking preference:")
    print("1. No smoking")
    print("2. Outdoor only")
    print("3. Any")

    smoking_options = {
        "1": "No smoking",
        "2": "Outdoor only",
        "3": "Any"
    }

    smoking_choice = input("Enter choice: ").strip()

    if smoking_choice not in smoking_options:
        print("Invalid smoking preference.")
        return

    smoking_preference = smoking_options[smoking_choice]

    # Get pet preference
    print("\nPet friendly preference:")
    print("1. Yes")
    print("2. No")
    print("3. No preference")

    pet_options = {
        "1": True,
        "2": False,
        "3": None
    }

    pet_choice = input("Enter choice: ").strip()

    if pet_choice not in pet_options:
        print("Invalid pet preference.")
        return

    pet_friendly = pet_options[pet_choice]

    # Save the profile and suburbs to PostgreSQL
    try:
        # Finish any transaction started by earlier SELECT queries
        conn.commit()

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO preference_profile (
                    user_id,
                    profile_name,
                    min_rent,
                    max_rent,
                    desired_move_in_date,
                    smoking_preference,
                    pet_friendly
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                user_id,
                profile_name,
                min_rent,
                max_rent,
                move_in_date,
                smoking_preference,
                pet_friendly
            ))

            for suburb in suburbs:
                cursor.execute("""
                    INSERT INTO preferred_suburb (
                        user_id,
                        profile_name,
                        preferred_suburb
                    )
                    VALUES (%s, %s, %s);
                """, (
                    user_id,
                    profile_name,
                    suburb
                ))

        conn.commit()
        print("\nPreference profile created successfully!")

    except UniqueViolation:
        conn.rollback()
        print(f"\nA preference profile named '{profile_name}' already exists.")
        print("Please choose a different name.")
    
    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to create preference profile.")
        print("Database error:", error)

    input("\nPress Enter to return...")



def manage_preferences(conn, user_id, active_profile):

    while True:
        print("\n========== MANAGE PREFERENCES ==========")
        print()
        print("1. View Preference Profiles")
        print("2. Create New Preference Profile")
        print()
        print("0. Return to Main Menu")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            active_profile = view_preference_profiles(
                conn, user_id, active_profile)

        elif choice == "2":
            create_preference_profile(conn, user_id)

        elif choice == "0":
            return active_profile

        else:
            print("\nInvalid choice. Please try again.")

def cancel_viewing(conn, user_id, booking_id):

    confirmation = input(
        "\nAre you sure you want to cancel this viewing? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":
        print("\nCancellation aborted.")
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE viewing_booking
                SET status = 'CANCELLED'
                WHERE booking_id = %s
                  AND user_id = %s
                  AND status = 'CONFIRMED'
                RETURNING booking_id;
            """, (booking_id, user_id))

            cancelled = cursor.fetchone()

        conn.commit()

        if cancelled:
            print("\nViewing cancelled successfully!")
            return True

        print("\nBooking not found or already cancelled.")
        return False

    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to cancel viewing.")
        print("Database error:", error)
        return False            

def book_viewing(conn, user_id, listing_id):

    print("\n========== BOOK A VIEWING ==========")

    # Retrieve available viewing slots
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT vs.viewing_timestamp
            FROM viewing_slot AS vs
            JOIN listing AS l
                ON vs.listing_id = l.listing_id
            WHERE vs.listing_id = %s
              AND vs.status = 'AVAILABLE'
              AND l.status = 'OPEN'
              AND vs.viewing_timestamp > CURRENT_TIMESTAMP
            ORDER BY vs.viewing_timestamp;
        """, (listing_id,))

        slots = cursor.fetchall()

    if not slots:
        print("\nNo available viewing slots for this listing.")
        input("\nPress Enter to return...")
        return

    while True:

        print("\nAvailable viewing slots:\n")

        for i, slot in enumerate(slots, start=1):
            timestamp = slot[0]
            print(f"{i}. {timestamp:%d/%m/%Y at %I:%M %p}")

        print("\n0. Cancel")

        choice = input("\nSelect a viewing slot: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not 1 <= int(choice) <= len(slots):
            print("\nInvalid choice. Please try again.")
            continue

        selected_timestamp = slots[int(choice) - 1][0]

        confirmation = input(
            f"\nConfirm booking for "
            f"{selected_timestamp:%d/%m/%Y at %I:%M %p}? (Y/N): "
        ).strip().upper()

        if confirmation != "Y":
            print("\nBooking cancelled.")
            return

        try:
            with conn.cursor() as cursor:

                # Check for an existing booking
                cursor.execute("""
                    SELECT booking_id, status
                    FROM viewing_booking
                    WHERE user_id = %s
                      AND listing_id = %s
                      AND viewing_timestamp = %s;
                """, (user_id, listing_id, selected_timestamp))

                existing_booking = cursor.fetchone()

                if existing_booking:
                    booking_id, status = existing_booking

                    if status == "CONFIRMED":
                        print("\nYou have already booked this viewing.")
                        return

                    elif status == "CANCELLED":
                        cursor.execute("""
                            UPDATE viewing_booking
                            SET status = 'CONFIRMED',
                                booking_date = CURRENT_DATE
                            WHERE booking_id = %s;
                        """, (booking_id,))

                        conn.commit()

                        print("\nViewing rebooked successfully!")
                        print(f"Booking ID: {booking_id}")
                        input("\nPress Enter to return...")
                        return

                # Insert booking into PostgreSQL
                cursor.execute("""
                    INSERT INTO viewing_booking (
                        user_id,
                        listing_id,
                        viewing_timestamp,
                        booking_date,
                        status
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        CURRENT_DATE,
                        'CONFIRMED'
                    )
                    RETURNING booking_id;
                """, (user_id, listing_id, selected_timestamp))

                booking_id = cursor.fetchone()[0]

            conn.commit()

            print("\nViewing booked successfully!")
            print(f"Booking ID: {booking_id}")
            print(f"Viewing: {selected_timestamp:%d/%m/%Y at %I:%M %p}")

        except psycopg.Error as error:
            conn.rollback()
            print("\nFailed to book viewing.")
            print("Database error:", error)

        input("\nPress Enter to return...")
        return

def apply_for_listing(conn, user_id, listing_id):

    print("\n========== APPLY FOR LISTING ==========")

    # Check whether the user has already applied
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT application_id, status
            FROM application
            WHERE user_id = %s
              AND listing_id = %s;
        """, (user_id, listing_id))

        existing_application = cursor.fetchone()

    if existing_application:
        application_id, status = existing_application

        print("\nYou have already applied for this listing.")
        print(f"Application ID: {application_id}")
        print(f"Current status: {status}")

        input("\nPress Enter to return...")
        return

    # Check whether the listing is still open
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT status, creator_user_id
            FROM listing
            WHERE listing_id = %s;
        """, (listing_id,))

        listing = cursor.fetchone()

    if listing is None:
        print("\nListing not found.")
        input("\nPress Enter to return...")
        return

    listing_status, owner_id = listing

    if listing_status != "OPEN":
        print("\nThis listing is no longer accepting applications.")
        input("\nPress Enter to return...")
        return

    if owner_id == user_id:
        print("\nYou cannot apply for your own listing.")
        input("\nPress Enter to return...")
        return

    # Collect application message
    message = input(
        "\nWrite a short message to the owner: "
    ).strip()

    if not message:
        print("\nApplication cancelled. A message is required.")
        input("\nPress Enter to return...")
        return

    # Confirm submission
    print("\n========== CONFIRM APPLICATION ==========")
    print(f"Listing ID: {listing_id}")
    print(f"Message: {message}")

    confirmation = input(
        "\nSubmit application? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":
        print("\nApplication cancelled.")
        input("\nPress Enter to return...")
        return

    # Insert application into PostgreSQL
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO application (
                    user_id,
                    listing_id,
                    application_date,
                    status,
                    message
                )
                VALUES (
                    %s,
                    %s,
                    CURRENT_DATE,
                    'PENDING',
                    %s
                )
                RETURNING application_id;
            """, (user_id, listing_id, message))

            application_id = cursor.fetchone()[0]

        conn.commit()

        print("\nApplication submitted successfully!")
        print(f"Application ID: {application_id}")
        print("Status: PENDING")

    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to submit application.")
        print("Database error:", error)

    input("\nPress Enter to return...")

def remove_saved_listing(conn, user_id, listing_id):

    confirmation = input(
        "\nRemove this listing from your saved listings? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":
        print("\nRemoval cancelled.")
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM saves
                WHERE user_id = %s
                  AND listing_id = %s
                RETURNING listing_id;
            """, (user_id, listing_id))

            removed = cursor.fetchone()

        conn.commit()

        if removed:
            print("\nListing removed successfully!")
            return True

        print("\nListing was not found in your saved listings.")
        return False

    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to remove listing.")
        print("Database error:", error)
        return False

def save_listing(conn, user_id, listing_id):

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO saves (user_id, listing_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, listing_id) DO NOTHING
                RETURNING listing_id;
            """, (user_id, listing_id))

            saved = cursor.fetchone()

        conn.commit()

        if saved:
            print("\nListing saved successfully!")
        else:
            print("\nYou have already saved this listing.")

    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to save listing.")
        print("Database error:", error)

def view_listing_details(conn, user_id, listing_id):

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                l.listing_id,
                p.unit_number,
                p.street_number,
                p.street_name,
                p.suburb,
                p.state,
                p.postcode,
                l.weekly_rent,
                l.available_from,
                r.room_type,
                r.is_furnished,
                r.has_ensuite,
                r.num_roommates,
                l.num_housemates,
                r.description,
                p.smoking_policy,
                p.pet_friendly,
                u.first_name,
                u.last_name
            FROM listing AS l
            JOIN room AS r
                ON l.room_id = r.room_id
            JOIN property_characteristics AS p
                ON r.property_id = p.property_id
            JOIN app_user AS u
                ON l.creator_user_id = u.user_id
            WHERE l.listing_id = %s;
        """, (listing_id,))

        listing = cursor.fetchone()

    if listing is None:
        print("\nListing not found.")
        input("\nPress Enter to return...")
        return

    (
        listing_id,
        unit_number,
        street_number,
        street_name,
        suburb,
        state,
        postcode,
        weekly_rent,
        available_from,
        room_type,
        is_furnished,
        has_ensuite,
        num_roommates,
        num_housemates,
        description,
        smoking_policy,
        pet_friendly,
        first_name,
        last_name
    ) = listing

    # Format the address
    address = f"{street_number} {street_name}"

    if unit_number:
        address = f"Unit {unit_number}, {address}"

    address = f"{address}, {suburb}, {state} {postcode}"

    # Convert Boolean values to readable text
    furnished_text = "Yes" if is_furnished else "No"
    ensuite_text = "Yes" if has_ensuite else "No"
    pet_text = "Yes" if pet_friendly else "No"

    print("\n========== LISTING DETAILS ==========")

    print(f"\nListing ID: {listing_id}")
    print(f"Address: {address}")
    print(f"Weekly rent: ${weekly_rent:.2f}")
    print(f"Available from: {available_from:%d/%m/%Y}")

    print(f"\nRoom type: {room_type}")
    print(f"Furnished: {furnished_text}")
    print(f"Ensuite: {ensuite_text}")
    print(f"Roommates sharing room: {num_roommates}")
    print(f"Other housemates: {num_housemates}")

    print(f"\nRoom description: {description or 'Not provided'}")
    print(f"Smoking policy: {smoking_policy}")
    print(f"Pet friendly: {pet_text}")

    print(f"\nListed by: {first_name} {last_name}")

    while True:
        print("\n1. Save Listing")
        print("2. Apply for Listing")
        print("3. Book Viewing")
        print("0. Back to Search Results")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            save_listing(conn, user_id, listing_id)
            input("\nPress Enter to continue...")

        elif choice == "2":
            apply_for_listing(conn, user_id, listing_id)

        elif choice == "3":
            book_viewing(conn, user_id, listing_id)

        elif choice == "0":
            return

        else:
            print("\nInvalid choice. Please try again.")

def search_listings(conn, user_id, active_profile):

    print("\n========== SEARCH LISTINGS ==========")

    if active_profile is None:
        print("\nPlease select an active preference profile first.")
        input("\nPress Enter to return...")
        return

    print(f"\nActive profile: {active_profile}")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                l.listing_id,
                p.suburb,
                r.room_type,
                l.weekly_rent,
                l.available_from
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
            WHERE pp.user_id = %s
                AND pp.profile_name = %s
                AND l.status = 'OPEN'
                AND l.weekly_rent BETWEEN pp.min_rent AND pp.max_rent
                AND (
                    pp.desired_move_in_date IS NULL
                    OR l.available_from <= pp.desired_move_in_date
                )
                AND (
                    pp.smoking_preference = 'Any'
                    OR (
                        pp.smoking_preference = 'No smoking'
                        AND p.smoking_policy = 'No smoking'
                    )
                    OR (
                        pp.smoking_preference = 'Outdoor only'
                        AND p.smoking_policy IN ('No smoking', 'Outdoor only')
                    )
                )
                AND (
                    pp.pet_friendly IS DISTINCT FROM TRUE
                    OR p.pet_friendly = TRUE)

            ORDER BY l.weekly_rent ASC, l.listing_id;
        """, (user_id, active_profile))

        listings = cursor.fetchall()

        if not listings:
            print("\nNo listings match your current preferences.")
            input("\nPress Enter to return...")
            return

        while True:

            print("\n========== SEARCH RESULTS ==========")
            print(f"\nActive profile: {active_profile}")
            print(f"Found {len(listings)} matching listing(s):\n")

            for i, listing in enumerate(listings, start=1):
                listing_id, suburb, room_type, rent, available_from = listing

                print(
                    f"{i}. {suburb} | ${rent:.2f}/week | "
                    f"{room_type} | Available: {available_from:%d/%m/%Y}"
                )

            print("\n0. Return to Main Menu")

            choice = input("\nSelect a listing: ").strip()

            if choice == "0":
                return

            if not choice.isdigit() or not 1 <= int(choice) <= len(listings):
                print("\nInvalid choice. Please try again.")
                continue

            selected_listing = listings[int(choice) - 1]

            listing_id = selected_listing[0]

            view_listing_details(conn, user_id, listing_id)

def saved_listings(conn, user_id):

    while True:

        # Retrieve all listings saved by the current user
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    l.listing_id,
                    p.suburb,
                    r.room_type,
                    l.weekly_rent,
                    l.available_from
                FROM saves AS s
                JOIN listing AS l
                    ON s.listing_id = l.listing_id
                JOIN room AS r
                    ON l.room_id = r.room_id
                JOIN property_characteristics AS p
                    ON r.property_id = p.property_id
                WHERE s.user_id = %s
                ORDER BY l.weekly_rent ASC, l.listing_id;
            """, (user_id,))

            listings = cursor.fetchall()

        print("\n========== SAVED LISTINGS ==========")

        if not listings:
            print("\nYou have no saved listings.")
            input("\nPress Enter to return...")
            return

        print(f"\nYou have {len(listings)} saved listing(s):\n")

        for i, listing in enumerate(listings, start=1):
            listing_id, suburb, room_type, rent, available_from = listing

            print(
                f"{i}. {suburb} | ${rent:.2f}/week | "
                f"{room_type} | Available: {available_from:%d/%m/%Y}"
            )

        print("\n0. Return to Main Menu")

        choice = input("\nSelect a listing: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not 1 <= int(choice) <= len(listings):
            print("\nInvalid choice. Please try again.")
            continue

        selected_listing = listings[int(choice) - 1]
        listing_id = selected_listing[0]

        # Display actions for the selected saved listing
        while True:

            print("\n========== SAVED LISTING ==========")
            print("\n1. View Listing Details")
            print("2. Remove from Saved Listings")
            print("0. Back to Saved Listings")

            action = input("\nEnter your choice: ").strip()

            if action == "1":
                view_listing_details(conn, user_id, listing_id)

            elif action == "2":
                removed = remove_saved_listing(
                    conn, user_id, listing_id
                )

                input("\nPress Enter to continue...")

                if removed:
                    break

            elif action == "0":
                break

            else:
                print("\nInvalid choice. Please try again.")


def my_viewings(conn, user_id):

    while True:

        # Retrieve the user's viewing bookings
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    vb.booking_id,
                    l.listing_id,
                    p.suburb,
                    l.weekly_rent,
                    vb.viewing_timestamp,
                    vb.status
                FROM viewing_booking AS vb
                JOIN listing AS l
                    ON vb.listing_id = l.listing_id
                JOIN room AS r
                    ON l.room_id = r.room_id
                JOIN property_characteristics AS p
                    ON r.property_id = p.property_id
                WHERE vb.user_id = %s
                ORDER BY vb.viewing_timestamp ASC;
            """, (user_id,))

            bookings = cursor.fetchall()

        print("\n========== MY VIEWINGS ==========")

        if not bookings:
            print("\nYou have no viewing bookings.")
            input("\nPress Enter to return...")
            return

        print(f"\nYou have {len(bookings)} viewing booking(s):\n")

        for i, booking in enumerate(bookings, start=1):
            booking_id, listing_id, suburb, rent, timestamp, status = booking

            print(
                f"{i}. {suburb} | ${rent:.2f}/week | "
                f"{timestamp:%d/%m/%Y at %I:%M %p} | {status}"
            )

        print("\n0. Return to Main Menu")

        choice = input("\nSelect a viewing: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not 1 <= int(choice) <= len(bookings):
            print("\nInvalid choice. Please try again.")
            continue

        selected_booking = bookings[int(choice) - 1]

        booking_id = selected_booking[0]
        listing_id = selected_booking[1]
        timestamp = selected_booking[4]
        status = selected_booking[5]

        while True:

            print("\n========== VIEWING DETAILS ==========")
            print(f"\nBooking ID: {booking_id}")
            print(f"Listing ID: {listing_id}")
            print(f"Viewing: {timestamp:%d/%m/%Y at %I:%M %p}")
            print(f"Status: {status}")

            print("\n1. View Listing Details")

            if status == "CONFIRMED" and timestamp > datetime.now():
                print("2. Cancel Viewing")

            print("0. Back to My Viewings")

            action = input("\nEnter your choice: ").strip()

            if action == "1":
                view_listing_details(conn, user_id, listing_id)

            elif action == "2" and status == "CONFIRMED" and timestamp > datetime.now():
                cancelled = cancel_viewing(conn, user_id, booking_id)

                input("\nPress Enter to continue...")

                if cancelled:
                    break

            elif action == "0":
                break

            else:
                print("\nInvalid choice. Please try again.")


def my_applications(conn, user_id):

    while True:

        # Retrieve applications submitted by the current user
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    a.application_id,
                    l.listing_id,
                    p.suburb,
                    l.weekly_rent,
                    a.application_date,
                    a.status,
                    a.message
                FROM application AS a
                JOIN listing AS l
                    ON a.listing_id = l.listing_id
                JOIN room AS r
                    ON l.room_id = r.room_id
                JOIN property_characteristics AS p
                    ON r.property_id = p.property_id
                WHERE a.user_id = %s
                ORDER BY a.application_date DESC, a.application_id DESC;
            """, (user_id,))

            applications = cursor.fetchall()

        print("\n========== MY APPLICATIONS ==========")

        if not applications:
            print("\nYou have not submitted any applications.")
            input("\nPress Enter to return...")
            return

        print(f"\nYou have {len(applications)} application(s):\n")

        for i, application in enumerate(applications, start=1):

            (
                application_id,
                listing_id,
                suburb,
                rent,
                application_date,
                status,
                message
            ) = application

            print(
                f"{i}. {suburb} | ${rent:.2f}/week | "
                f"Applied: {application_date:%d/%m/%Y} | "
                f"Status: {status}"
            )

        print("\n0. Return to Main Menu")

        choice = input("\nSelect an application: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not 1 <= int(choice) <= len(applications):
            print("\nInvalid choice. Please try again.")
            continue

        selected_application = applications[int(choice) - 1]

        (
            application_id,
            listing_id,
            suburb,
            rent,
            application_date,
            status,
            message
        ) = selected_application

        while True:

            print("\n========== APPLICATION DETAILS ==========")

            print(f"\nApplication ID: {application_id}")
            print(f"Listing ID: {listing_id}")
            print(f"Suburb: {suburb}")
            print(f"Weekly rent: ${rent:.2f}")
            print(f"Application date: {application_date:%d/%m/%Y}")
            print(f"Status: {status}")
            print(f"Your message: {message or 'No message provided'}")

            print("\n1. View Listing Details")
            print("0. Back to My Applications")

            action = input("\nEnter your choice: ").strip()

            if action == "1":
                view_listing_details(conn, user_id, listing_id)

            elif action == "0":
                break

            else:
                print("\nInvalid choice. Please try again.")

def update_application_status(conn, owner_id, application_id, new_status):

    if new_status not in ("ACCEPTED", "REJECTED"):
        print("\nInvalid application status.")
        return False

    confirmation = input(
        f"\nConfirm changing this application to {new_status}? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":
        print("\nStatus update cancelled.")
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE application AS a
                SET status = %s
                FROM listing AS l
                WHERE a.listing_id = l.listing_id
                  AND a.application_id = %s
                  AND l.creator_user_id = %s
                  AND a.status = 'PENDING'
                RETURNING a.application_id;
            """, (new_status, application_id, owner_id))

            updated = cursor.fetchone()

        conn.commit()

        if updated:
            print(f"\nApplication successfully {new_status.lower()}!")
            return True

        print("\nApplication not found, not pending, or not owned by you.")
        return False

    except psycopg.Error as error:
        conn.rollback()
        print("\nFailed to update application.")
        print("Database error:", error)
        return False

def manage_applications(conn, user_id):

    while True:

        # Retrieve applications for listings owned by this user
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    a.application_id,
                    a.listing_id,
                    p.suburb,
                    l.weekly_rent,
                    u.first_name,
                    u.last_name,
                    a.application_date,
                    a.status,
                    a.message
                FROM application AS a
                JOIN listing AS l
                    ON a.listing_id = l.listing_id
                JOIN room AS r
                    ON l.room_id = r.room_id
                JOIN property_characteristics AS p
                    ON r.property_id = p.property_id
                JOIN app_user AS u
                    ON a.user_id = u.user_id
                WHERE l.creator_user_id = %s
                ORDER BY
                    a.application_date DESC,
                    a.application_id DESC;
            """, (user_id,))

            applications = cursor.fetchall()

        print("\n========== MANAGE APPLICATIONS ==========")

        if not applications:
            print("\nNo applications have been received for your listings.")
            input("\nPress Enter to return...")
            return

        print(f"\nYou have {len(applications)} application(s):\n")

        for i, application in enumerate(applications, start=1):

            (
                application_id,
                listing_id,
                suburb,
                rent,
                first_name,
                last_name,
                application_date,
                status,
                message
            ) = application

            print(
                f"{i}. {first_name} {last_name} | "
                f"{suburb} | ${rent:.2f}/week | "
                f"Status: {status}"
            )

        print("\n0. Return to Main Menu")

        choice = input("\nSelect an application: ").strip()

        if choice == "0":
            return

        if not choice.isdigit() or not 1 <= int(choice) <= len(applications):
            print("\nInvalid choice. Please try again.")
            continue

        selected_application = applications[int(choice) - 1]

        (
            application_id,
            listing_id,
            suburb,
            rent,
            first_name,
            last_name,
            application_date,
            status,
            message
        ) = selected_application

        while True:

            print("\n========== APPLICATION DETAILS ==========")

            print(f"\nApplication ID: {application_id}")
            print(f"Listing ID: {listing_id}")
            print(f"Property suburb: {suburb}")
            print(f"Weekly rent: ${rent:.2f}")
            print(f"Applicant: {first_name} {last_name}")
            print(f"Application date: {application_date:%d/%m/%Y}")
            print(f"Status: {status}")
            print(f"Applicant message: {message or 'No message provided'}")

            print("\n1. View Listing Details")

            if status == "PENDING":
                print("2. Accept Application")
                print("3. Reject Application")

            print("0. Back to Applications")

            action = input("\nEnter your choice: ").strip()

            if action == "1":
                view_listing_details(conn, user_id, listing_id)

            elif action in ("2", "3") and status == "PENDING":

                new_status = (
                    "ACCEPTED" if action == "2" else "REJECTED"
                )

                updated = update_application_status(
                    conn,
                    user_id,
                    application_id,
                    new_status
                )

                input("\nPress Enter to continue...")

                if updated:
                    break

            elif action == "0":
                break

            else:
                print("\nInvalid choice. Please try again.")


# MAIN MENU

def main_menu(conn, user_id, user_name, active_profile):

    while True:
        print("\n========== HOUSEMATCH ==========")
        print(f"Signed in as: {user_name}")
        print(f"Active preference profile: {active_profile or 'None selected'}")
        print()
        print("1. Manage Preferences")
        print("2. Search Listings")
        print("3. Saved Listings")
        print("4. My Viewings")
        print("5. My Applications")
        print("6. Manage Applications (Owner)")
        print()
        print("0. Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            active_profile = manage_preferences(conn, user_id, active_profile)

        elif choice == "2":
            search_listings(conn, user_id, active_profile)

        elif choice == "3":
            saved_listings(conn, user_id)

        elif choice == "4":
            my_viewings(conn, user_id)

        elif choice == "5":
            my_applications(conn, user_id)

        elif choice == "6":
            manage_applications(conn, user_id)

        elif choice == "0":
            print("\nGoodbye!")
            break

        else:
            print("\nInvalid choice. Please try again.")


# START APPLICATION

def main():
    try:
        password = getpass("Enter PostgreSQL password: ")

        with psycopg.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=password,
            port=DB_PORT
        ) as conn:

            user_name = get_user_name(conn, CURRENT_USER_ID)

            active_profile = None

            print("\nSuccessfully connected to HouseMatch!")

            main_menu(conn, CURRENT_USER_ID, user_name, active_profile)

    except (psycopg.Error, ValueError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()
