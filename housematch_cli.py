
import psycopg
from getpass import getpass
from datetime import date


# DATABASE CONFIGURATION

DB_HOST = "localhost"
DB_NAME = "housematch"  
DB_USER = "postgres"
DB_PORT = 5432

# Olivia Chen from your sample data
CURRENT_USER_ID = 1


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

def view_preference_profiles(conn, user_id):

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
        return

    while True:
        print("\n========== YOUR PREFERENCE PROFILES ==========")

        for i, profile in enumerate(profiles, start=1):
            print(f"{i}. {profile[0]}")

        print("\n0. Back")

        choice = input("\nSelect a profile: ").strip()

        if choice == "0":
            return

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

        input("\nPress Enter to go back...")


def create_preference_profile(conn, user_id):
    print("\n--- Create New Preference Profile ---")
    print("Feature coming next.")
    input("\nPress Enter to go back...")


def manage_preferences(conn, user_id):

    while True:
        print("\n========== MANAGE PREFERENCES ==========")
        print()
        print("1. View Preference Profiles")
        print("2. Create New Preference Profile")
        print()
        print("0. Return to Main Menu")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            view_preference_profiles(conn, user_id)

        elif choice == "2":
            create_preference_profile(conn, user_id)

        elif choice == "0":
            return

        else:
            print("\nInvalid choice. Please try again.")

def search_listings(conn, user_id):
    print("\n--- Search Listings ---")
    print("Feature coming soon.")
    input("\nPress Enter to return to the main menu...")


def saved_listings(conn, user_id):
    print("\n--- Saved Listings ---")
    print("Feature coming soon.")
    input("\nPress Enter to return to the main menu...")


def my_viewings(conn, user_id):
    print("\n--- My Viewings ---")
    print("Feature coming soon.")
    input("\nPress Enter to return to the main menu...")


def my_applications(conn, user_id):
    print("\n--- My Applications ---")
    print("Feature coming soon.")
    input("\nPress Enter to return to the main menu...")


def manage_applications(conn, user_id):
    print("\n--- Manage Applications (Owner) ---")
    print("Feature coming soon.")
    input("\nPress Enter to return to the main menu...")


# MAIN MENU

def main_menu(conn, user_id, user_name):

    while True:
        print("\n========== HOUSEMATCH ==========")
        print(f"Signed in as: {user_name}")
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
            manage_preferences(conn, user_id)

        elif choice == "2":
            search_listings(conn, user_id)

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

            print("\nSuccessfully connected to HouseMatch!")

            main_menu(conn, CURRENT_USER_ID, user_name)

    except (psycopg.Error, ValueError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()

