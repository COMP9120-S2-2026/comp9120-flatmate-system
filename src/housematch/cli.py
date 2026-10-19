import argparse
import json
from pathlib import Path
import sys

import psycopg
from .db import connect, initialise
from . import member_a as a
from . import member_b as b
from . import member_c as c
from .demo import seed_demo


def main(argv=None):
    parser=argparse.ArgumentParser(description='HouseMatch shared database CLI')
    parser.add_argument('--user-id',type=int,help='Demo actor; Member C will supply authenticated identity.')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('init',help='Create all ten tables and triggers in an empty schema.')
    sub.add_parser('seed',help='Insert synthetic fixtures into empty tables.')
    p=sub.add_parser('list'); p.add_argument('--status',choices=['OPEN','PAUSED','CLOSED']); p.add_argument('--mine',action='store_true')
    p=sub.add_parser('show'); p.add_argument('listing_id',type=int)
    p=sub.add_parser('publish'); p.add_argument('room_json',type=Path); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True); p.add_argument('--housemates',type=int,default=0)
    p=sub.add_parser('relist'); p.add_argument('room_id',type=int); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True); p.add_argument('--housemates',type=int,default=0)
    p=sub.add_parser('update'); p.add_argument('listing_id',type=int); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True)
    p=sub.add_parser('close'); p.add_argument('listing_id',type=int)
    p=sub.add_parser('describe-room'); p.add_argument('room_id',type=int); p.add_argument('description')
    p=sub.add_parser('update-room'); p.add_argument('room_id',type=int); p.add_argument('room_json',type=Path)
    sub.add_parser('profiles')
    p=sub.add_parser('profile-save'); p.add_argument('profile_json',type=Path)
    p=sub.add_parser('profile-delete'); p.add_argument('profile_name')
    p=sub.add_parser('search'); p.add_argument('profile_name',nargs='?',default='Default')
    sub.add_parser('saved')
    p=sub.add_parser('save'); p.add_argument('listing_id',type=int); p.add_argument('--rank',type=int)
    p=sub.add_parser('unsave'); p.add_argument('listing_id',type=int)
    p=sub.add_parser('slot'); p.add_argument('listing_id',type=int); p.add_argument('timestamp')
    p=sub.add_parser('book'); p.add_argument('listing_id',type=int); p.add_argument('timestamp')
    p=sub.add_parser('cancel-booking'); p.add_argument('booking_id',type=int)
    p=sub.add_parser('reschedule'); p.add_argument('booking_id',type=int); p.add_argument('timestamp')
    p=sub.add_parser('apply'); p.add_argument('listing_id',type=int); p.add_argument('--message')
    sub.add_parser('applications')
    p=sub.add_parser('applicants'); p.add_argument('listing_id',type=int)
    for action in ('withdraw','reject','accept'):
        p=sub.add_parser(action); p.add_argument('application_id',type=int)
    args=parser.parse_args(argv)
    if (args.action not in ['init','seed','list','show'] or getattr(args,'mine',False)) and args.user_id is None:
        parser.error('--user-id is required for user-specific operations.')
    try:
        with connect() as conn:
            if args.action=='init': initialise(conn); result={'created':'Ten tables and integrity triggers'}
            elif args.action=='seed': result=seed_demo(conn)
            elif args.action=='list': result=a.list_listings(conn,args.status,args.user_id if args.mine else None)
            elif args.action=='show':
                result=a.listing_detail(conn,args.listing_id)
                if not result: raise a.BusinessRuleError('Listing does not exist.')
            elif args.action=='publish': result=a.publish_new_room(conn,args.user_id,json.loads(args.room_json.read_text(encoding='utf-8')),args.rent,args.available_from,args.housemates)
            elif args.action=='relist': result={'listing_id':a.create_listing_for_room(conn,args.user_id,args.room_id,args.rent,args.available_from,args.housemates)}
            elif args.action=='update': result=a.update_listing(conn,args.user_id,args.listing_id,args.rent,args.available_from)
            elif args.action=='close': result=a.close_listing(conn,args.user_id,args.listing_id)
            elif args.action=='update-room': result=a.update_room(conn,args.user_id,args.room_id,json.loads(args.room_json.read_text(encoding='utf-8')))
            elif args.action=='describe-room': result=a.update_room_description(conn,args.user_id,args.room_id,args.description)
            elif args.action=='profiles': result=b.list_profiles(conn,args.user_id)
            elif args.action=='profile-save': result=b.save_profile(conn,args.user_id,**json.loads(args.profile_json.read_text(encoding='utf-8')))
            elif args.action=='profile-delete': result=b.delete_profile(conn,args.user_id,args.profile_name)
            elif args.action=='search': result=b.search_listings(conn,args.user_id,args.profile_name)
            elif args.action=='saved': result=b.list_saved(conn,args.user_id)
            elif args.action=='save': result=b.save_listing(conn,args.user_id,args.listing_id,args.rank)
            elif args.action=='unsave': result=b.unsave_listing(conn,args.user_id,args.listing_id)
            elif args.action=='slot': result=b.create_slot(conn,args.user_id,args.listing_id,args.timestamp)
            elif args.action=='book': result=b.book_viewing(conn,args.user_id,args.listing_id,args.timestamp)
            elif args.action=='cancel-booking': result=b.cancel_booking(conn,args.user_id,args.booking_id)
            elif args.action=='reschedule': result=b.reschedule_booking(conn,args.user_id,args.booking_id,args.timestamp)
            elif args.action=='apply': result=c.submit_application(conn,args.user_id,args.listing_id,args.message)
            elif args.action=='applications': result=c.list_user_applications(conn,args.user_id)
            elif args.action=='applicants': result=c.list_listing_applicants(conn,args.user_id,args.listing_id)
            elif args.action=='withdraw': result=c.withdraw_application(conn,args.user_id,args.application_id)
            elif args.action=='reject': result=c.reject_application(conn,args.user_id,args.application_id)
            elif args.action=='accept': result=c.accept_application(conn,args.user_id,args.application_id)
        print(json.dumps(result,default=str,indent=2))
        return 0
    except (ValueError,psycopg.Error,OSError) as exc:
        # Error context contains no connection string or password.
        print('Operation failed: '+str(exc).split('\n')[0],file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
