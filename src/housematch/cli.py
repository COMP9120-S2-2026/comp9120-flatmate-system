import argparse
import json
from pathlib import Path
import sys

import psycopg
from .db import connect, initialise
from . import member_a as a
from .demo import seed_demo


def main(argv=None):
    parser=argparse.ArgumentParser(description='HouseMatch Member A advertiser CLI')
    parser.add_argument('--user-id',type=int,help='Demo actor; Member C will supply authenticated identity.')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('init',help='Create contract/A tables in an empty schema.')
    sub.add_parser('seed',help='Insert synthetic fixtures into empty tables.')
    p=sub.add_parser('list'); p.add_argument('--status',choices=['OPEN','CLOSED','FILLED']); p.add_argument('--mine',action='store_true')
    p=sub.add_parser('show'); p.add_argument('listing_id',type=int)
    p=sub.add_parser('publish'); p.add_argument('room_json',type=Path); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True)
    p=sub.add_parser('relist'); p.add_argument('room_id',type=int); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True)
    p=sub.add_parser('update'); p.add_argument('listing_id',type=int); p.add_argument('--rent',required=True); p.add_argument('--available-from',required=True)
    p=sub.add_parser('close'); p.add_argument('listing_id',type=int)
    p=sub.add_parser('describe-room'); p.add_argument('room_id',type=int); p.add_argument('description')
    p=sub.add_parser('update-room'); p.add_argument('room_id',type=int); p.add_argument('room_json',type=Path)
    args=parser.parse_args(argv)
    if (args.action in ['publish','relist','update','close','describe-room','update-room'] or getattr(args,'mine',False)) and args.user_id is None:
        parser.error('--user-id is required for advertiser operations.')
    try:
        with connect() as conn:
            if args.action=='init': initialise(conn); result={'created':'User contract, Room and Listing'}
            elif args.action=='seed': result=seed_demo(conn)
            elif args.action=='list': result=a.list_listings(conn,args.status,args.user_id if args.mine else None)
            elif args.action=='show':
                result=a.listing_detail(conn,args.listing_id)
                if not result: raise a.BusinessRuleError('Listing does not exist.')
            elif args.action=='publish': result=a.publish_new_room(conn,args.user_id,json.loads(args.room_json.read_text()),args.rent,args.available_from)
            elif args.action=='relist': result={'listing_id':a.create_listing_for_room(conn,args.user_id,args.room_id,args.rent,args.available_from)}
            elif args.action=='update': result=a.update_listing(conn,args.user_id,args.listing_id,args.rent,args.available_from)
            elif args.action=='close': result=a.close_listing(conn,args.user_id,args.listing_id)
            elif args.action=='update-room': result=a.update_room(conn,args.user_id,args.room_id,json.loads(args.room_json.read_text()))
            else: result=a.update_room_description(conn,args.user_id,args.room_id,args.description)
        print(json.dumps(result,default=str,indent=2))
        return 0
    except (ValueError,psycopg.Error,OSError) as exc:
        # Error context contains no connection string or password.
        print('Operation failed: '+str(exc).split('\n')[0],file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
