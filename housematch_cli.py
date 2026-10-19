"""Interactive menu using the same config, schema and services as run.py."""
import json
import psycopg
import run  # Adds this repository's src directory to the import path.
from housematch.db import connect
from housematch import member_a as a, member_b as b, member_c as c


def display(result):
    print(json.dumps(result,default=str,indent=2))


def main():
    try:
        with connect() as conn:
            display(conn.execute('SELECT user_id,first_name,last_name FROM app_user ORDER BY user_id').fetchall())
            user_id=int(input('Select demo user ID (not authentication): '))
            if not conn.execute('SELECT 1 FROM app_user WHERE user_id=%s',(user_id,)).fetchone():
                raise ValueError('User does not exist.')
            while True:
                print('\nHOUSEMATCH')
                print('1. View preference profiles\n2. Save a preference profile\n3. Search listings')
                print('4. View saved listings\n5. Save a listing\n6. Book a viewing')
                print('7. Cancel a booking\n8. Reschedule a booking\n9. Submit an application')
                print('10. My applications\n11. View applicants\n12. Accept an application')
                print('13. Reject an application\n14. Withdraw an application\n15. View open listings\n0. Exit')
                choice=input('Choose an option: ').strip()
                if choice=='0': return 0
                try:
                    if choice=='1': result=b.list_profiles(conn,user_id)
                    elif choice=='2':
                        name=input('Profile name: ')
                        minimum=input('Minimum weekly rent: ')
                        maximum=input('Maximum weekly rent: ')
                        suburbs=[s.strip() for s in input('Suburbs separated by commas (blank = any): ').split(',') if s.strip()]
                        result=b.save_profile(conn,user_id,name,minimum,maximum,suburbs=suburbs)
                    elif choice=='3': result=b.search_listings(conn,user_id,input('Profile name [Default]: ') or 'Default')
                    elif choice=='4': result=b.list_saved(conn,user_id)
                    elif choice=='5': result=b.save_listing(conn,user_id,int(input('Listing ID: ')))
                    elif choice=='6': result=b.book_viewing(conn,user_id,int(input('Listing ID: ')),input('Viewing timestamp YYYY-MM-DD HH:MM:SS: '))
                    elif choice=='7': result=b.cancel_booking(conn,user_id,int(input('Booking ID: ')))
                    elif choice=='8': result=b.reschedule_booking(conn,user_id,int(input('Booking ID: ')),input('New timestamp YYYY-MM-DD HH:MM:SS: '))
                    elif choice=='9': result=c.submit_application(conn,user_id,int(input('Listing ID: ')),input('Message: '))
                    elif choice=='10': result=c.list_user_applications(conn,user_id)
                    elif choice=='11': result=c.list_listing_applicants(conn,user_id,int(input('Listing ID: ')))
                    elif choice=='12': result=c.accept_application(conn,user_id,int(input('Application ID: ')))
                    elif choice=='13': result=c.reject_application(conn,user_id,int(input('Application ID: ')))
                    elif choice=='14': result=c.withdraw_application(conn,user_id,int(input('Application ID: ')))
                    elif choice=='15': result=a.list_listings(conn,'OPEN')
                    else:
                        print('Invalid option.')
                        continue
                    display(result)
                except (ValueError,psycopg.Error) as exc:
                    print('Operation failed: '+str(exc).split('\n')[0])
    except (ValueError,psycopg.Error) as exc:
        print('Operation failed: '+str(exc).split('\n')[0])
        return 1


if __name__=='__main__':
    raise SystemExit(main())
