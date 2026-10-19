"""Real PostgreSQL checks against the report's ten-table schema."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
import threading
import unittest
import uuid
from unittest.mock import patch
import psycopg
from psycopg import sql
from housematch import member_a as a, member_b as b, member_c as c
from housematch.db import connect, initialise
from housematch.demo import sample_room, seed_demo


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get('TEST_DATABASE_URL')
        if not cls.dsn:
            raise unittest.SkipTest('TEST_DATABASE_URL is required for PostgreSQL tests.')
        cls.schema='hm_alignment_'+uuid.uuid4().hex
        cls.conn=connect(cls.dsn)
        cls.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(cls.schema)))
        cls.conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(cls.schema)))
        try:
            initialise(cls.conn)
        except Exception:
            cls.conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
            cls.conn.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
        cls.conn.close()

    def setUp(self):
        self.conn.rollback()
        self.conn.execute('TRUNCATE app_user,property_characteristics RESTART IDENTITY CASCADE')
        self.conn.execute("""INSERT INTO app_user(first_name,last_name,email)
            VALUES ('Owner','One','one@example.test'),('Applicant','Two','two@example.test'),
            ('Applicant','Three','three@example.test')""")

    def publish(self):
        return a.publish_new_room(self.conn,1,sample_room(),320,'2026-11-01',2)

    def slot(self, listing_id, days=7):
        timestamp=self.conn.execute(
            "SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Sydney')::date + %s + TIME '10:00' AS ts",
            (days,)).fetchone()['ts']
        b.create_slot(self.conn,1,listing_id,timestamp)
        return timestamp

    def test_exact_report_columns(self):
        expected={
          'app_user':'user_id first_name last_name phone_num email bio',
          'preference_profile':'user_id profile_name min_rent max_rent desired_move_in_date smoking_preference pet_preference',
          'preferred_suburb':'user_id profile_name preferred_suburb',
          'property_characteristics':'property_id street_number street_name suburb state postcode unit_number property_type total_rooms car_spots smoking_policy pet_policy',
          'room':'room_id room_type num_roommates is_furnished has_ensuite description property_id',
          'listing':'listing_id room_id creator_user_id weekly_rent available_from listing_date status num_housemates',
          'saves':'user_id listing_id preference_rank',
          'application':'application_id user_id listing_id application_date status message',
          'viewing_slot':'listing_id viewing_timestamp status',
          'viewing_booking':'booking_id user_id listing_id viewing_timestamp booking_date status'}
        actual={}
        for row in self.conn.execute('''SELECT table_name,column_name FROM information_schema.columns
            WHERE table_schema=%s ORDER BY table_name,ordinal_position''',(self.schema,)):
            actual.setdefault(row['table_name'],[]).append(row['column_name'])
        self.assertEqual(actual,{k:v.split() for k,v in expected.items()})

    def test_publish_and_update(self):
        x=self.publish()
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['num_housemates'],2)
        a.update_listing(self.conn,1,x['listing_id'],350,'2026-12-01')
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['weekly_rent'],350)
        details=sample_room(); details['description']='Updated'
        a.update_room(self.conn,1,x['room_id'],details)
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['description'],'Updated')

    def test_invalid_rent_rolls_back_room(self):
        for rent in (0,-1,'NaN'):
            with self.assertRaises(psycopg.errors.CheckViolation):
                a.publish_new_room(self.conn,1,sample_room(),rent,'2026-11-01')
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM room').fetchone()['n'],0)

    def test_unknown_advertiser_rollback(self):
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            a.publish_new_room(self.conn,999,sample_room(),320,'2026-11-01')
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM room').fetchone()['n'],0)

    def test_invalid_room_domain(self):
        for field,value in (('postcode','ABC'),('total_rooms',0),('num_roommates',-1)):
            details=sample_room(); details[field]=value
            with self.assertRaises(psycopg.errors.CheckViolation):
                a.publish_new_room(self.conn,1,details,320,'2026-11-01')

    def test_close_then_relist(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        new=a.create_listing_for_room(self.conn,1,x['room_id'],330,'2026-12-01')
        self.assertNotEqual(new,x['listing_id'])

    def test_duplicate_active_listing(self):
        x=self.publish()
        with self.assertRaises(psycopg.errors.RaiseException):
            self.conn.execute("""INSERT INTO listing(room_id,creator_user_id,weekly_rent,available_from)
                VALUES (%s,1,300,CURRENT_DATE)""",(x['room_id'],))

    def test_advertiser_ownership(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError): a.close_listing(self.conn,2,x['listing_id'])

    def test_room_mandatory_listing(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            with self.conn.transaction(): a._insert_room(self.conn,sample_room())
        x=self.publish()
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute('DELETE FROM listing WHERE listing_id=%s',(x['listing_id'],))

    def test_default_profile_and_last_profile_rule(self):
        self.assertEqual(len(b.list_profiles(self.conn,2)),1)
        with self.assertRaises(psycopg.errors.CheckViolation): b.delete_profile(self.conn,2,'Default')

    def test_profile_search_filters(self):
        self.publish()
        b.save_profile(self.conn,2,'Budget',0,350,'2026-12-01','No smoking',None,['Newtown'])
        self.assertEqual(len(b.search_listings(self.conn,2,'Budget')),1)
        b.save_profile(self.conn,2,'Budget',0,300,suburbs=['Newtown'])
        self.assertEqual(b.search_listings(self.conn,2,'Budget'),[])
        b.save_profile(self.conn,2,'Budget',0,350,suburbs=['Glebe'])
        self.assertEqual(b.search_listings(self.conn,2,'Budget'),[])
        self.assertEqual(len(b.search_listings(self.conn,2,'Default')),1)

    def test_profile_composite_fk(self):
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self.conn.execute("INSERT INTO preferred_suburb VALUES (2,'Missing','Glebe')")

    def test_save_duplicate_and_unsave(self):
        x=self.publish(); b.save_listing(self.conn,2,x['listing_id'],1)
        with self.assertRaises(psycopg.errors.UniqueViolation): b.save_listing(self.conn,2,x['listing_id'])
        self.assertEqual(len(b.list_saved(self.conn,2)),1)
        b.unsave_listing(self.conn,2,x['listing_id'])
        self.assertEqual(b.list_saved(self.conn,2),[])

    def test_application_dictionary_results(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'],'Hello')
        self.assertEqual(app['user_id'],2)
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['message'],'Hello')
        self.assertEqual(c.list_listing_applicants(self.conn,1,x['listing_id'])[0]['first_name'],'Applicant')

    def test_application_self_and_closed_rejected(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError): c.submit_application(self.conn,1,x['listing_id'])
        a.close_listing(self.conn,1,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError): c.submit_application(self.conn,2,x['listing_id'])

    def test_withdraw_then_reapply(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaises(psycopg.errors.UniqueViolation): c.submit_application(self.conn,2,x['listing_id'])
        c.withdraw_application(self.conn,2,app['application_id'])
        self.assertNotEqual(c.submit_application(self.conn,2,x['listing_id'])['application_id'],app['application_id'])

    def test_accept_atomic_and_reject_others(self):
        x=self.publish()
        app=c.submit_application(self.conn,2,x['listing_id'])
        c.submit_application(self.conn,3,x['listing_id'])
        self.assertEqual(c.accept_application(self.conn,1,app['application_id'])['status'],'ACCEPTED')
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['status'],'CLOSED')
        self.assertEqual(c.list_user_applications(self.conn,3)[0]['status'],'REJECTED')
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['status'],'ACCEPTED')

    def test_accept_rolls_back_on_injected_failure(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaises(RuntimeError):
            with self.conn.transaction():
                c.accept_application(self.conn,1,app['application_id'])
                raise RuntimeError('Injected failure after acceptance before outer commit')
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['status'],'OPEN')
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['status'],'PENDING')

    def test_accept_owner_check(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError): c.accept_application(self.conn,3,app['application_id'])

    def test_cannot_accept_without_closing_listing(self):
        x=self.publish()
        app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("UPDATE application SET status='ACCEPTED' WHERE application_id=%s",(app['application_id'],))

    def test_cancel_and_rebook_retains_history(self):
        x=self.publish(); ts=self.slot(x['listing_id'])
        old=b.book_viewing(self.conn,2,x['listing_id'],ts)
        b.cancel_booking(self.conn,2,old['booking_id'])
        new=b.book_viewing(self.conn,3,x['listing_id'],ts)
        self.assertNotEqual(old['booking_id'],new['booking_id'])
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM viewing_booking').fetchone()['n'],2)

    def test_reschedule_retains_identity_and_releases_slot(self):
        x=self.publish(); ts=self.slot(x['listing_id']); later=self.slot(x['listing_id'],8)
        old=b.book_viewing(self.conn,2,x['listing_id'],ts)
        new=b.reschedule_booking(self.conn,2,old['booking_id'],later)
        self.assertEqual((old['booking_id'],old['booking_date']),(new['booking_id'],new['booking_date']))
        self.assertEqual(self.conn.execute('SELECT status FROM viewing_slot WHERE viewing_timestamp=%s',
                                          (ts,)).fetchone()['status'],'AVAILABLE')

    def test_closed_listing_blocks_new_booking(self):
        x=self.publish(); ts=self.slot(x['listing_id']); a.close_listing(self.conn,1,x['listing_id'])
        with self.assertRaises(psycopg.Error): b.book_viewing(self.conn,2,x['listing_id'],ts)

    def test_accept_cancels_existing_booking(self):
        x=self.publish(); ts=self.slot(x['listing_id'])
        booking=b.book_viewing(self.conn,2,x['listing_id'],ts)
        app=c.submit_application(self.conn,2,x['listing_id'])
        c.accept_application(self.conn,1,app['application_id'])
        self.assertEqual(self.conn.execute('SELECT status FROM viewing_booking WHERE booking_id=%s',
                                          (booking['booking_id'],)).fetchone()['status'],'CANCELLED')
        b.cancel_booking(self.conn,1,booking['booking_id'])

    def test_two_sessions_compete_to_accept(self):
        x=self.publish()
        ids=[c.submit_application(self.conn,u,x['listing_id'])['application_id'] for u in (2,3)]
        barrier=threading.Barrier(2)
        def attempt(app_id):
            with connect(self.dsn,self.schema) as conn:
                conn.execute("SET lock_timeout='5s'")
                barrier.wait(timeout=5)
                try: c.accept_application(conn,1,app_id); return 'accepted'
                except a.BusinessRuleError: return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,ids))
        self.assertEqual(sorted(results),['accepted','blocked'])

    def test_two_sessions_compete_to_book(self):
        x=self.publish(); ts=self.slot(x['listing_id']); barrier=threading.Barrier(2)
        def attempt(user_id):
            with connect(self.dsn,self.schema) as conn:
                conn.execute("SET lock_timeout='5s'")
                barrier.wait(timeout=5)
                try: b.book_viewing(conn,user_id,x['listing_id'],ts); return 'booked'
                except psycopg.errors.RaiseException: return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,(2,3)))
        self.assertEqual(sorted(results),['blocked','booked'])

    def test_seed_and_queries(self):
        self.conn.execute('TRUNCATE app_user,property_characteristics RESTART IDENTITY CASCADE')
        self.assertEqual(seed_demo(self.conn),dict(users=14,properties=10,rooms=12,listings=12))
        from housematch.db import ROOT
        self.conn.execute((ROOT/'housematch_queries.sql').read_text())
        with self.assertRaises(psycopg.Error): seed_demo(self.conn)

    def test_max_sql_suite(self):
        from housematch.db import ROOT
        notices=[]
        self.conn.add_notice_handler(lambda notice: notices.append(notice.message_primary))
        try:
            self.conn.execute((ROOT/'housematch_tests.sql').read_text(encoding='utf-8'))
        finally:
            self.conn.rollback()
        self.assertTrue(any('HOUSEMATCH AUTOMATED TESTS PASSED' in notice for notice in notices),notices[-3:])

    def test_delete_profile_with_suburbs_and_last_profile_rollback(self):
        b.save_profile(self.conn,2,'Extra',0,500,suburbs=['Newtown'])
        self.assertIsNotNone(b.delete_profile(self.conn,2,'Extra'))
        b.save_profile(self.conn,2,'Default',0,500,suburbs=['Newtown'])
        with self.assertRaises(psycopg.Error):
            b.delete_profile(self.conn,2,'Default')
        self.assertEqual(b.list_profiles(self.conn,2)[0]['suburbs'],['Newtown'])

    def test_shared_property_room_capacity(self):
        details=sample_room(); details['total_rooms']=1
        x=a.publish_new_room(self.conn,1,details,300,'2026-11-01')
        prop=a.listing_detail(self.conn,x['listing_id'])['property_id']
        another={f:details[f] for f in a.ROOM_FIELDS}; another['property_id']=prop
        with self.assertRaises(psycopg.errors.RaiseException):
            a.publish_new_room(self.conn,1,another,300,'2026-11-01')

    def test_existing_property_used_without_duplication(self):
        x=self.publish(); prop=a.listing_detail(self.conn,x['listing_id'])['property_id']
        details={f:sample_room()[f] for f in a.ROOM_FIELDS}; details['property_id']=prop
        y=a.publish_new_room(self.conn,1,details,300,'2026-11-01')
        self.assertEqual(a.listing_detail(self.conn,y['listing_id'])['property_id'],prop)
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM property_characteristics').fetchone()['n'],1)

    def test_shared_property_edit_requires_consistent_owner(self):
        x=self.publish()
        prop=a.listing_detail(self.conn,x['listing_id'])['property_id']
        details={f:sample_room()[f] for f in a.ROOM_FIELDS}
        a.publish_new_room(self.conn,2,dict(details,property_id=prop),300,'2026-11-01')
        changed=sample_room(); changed['street_name']='Changed Street'
        with self.assertRaises(a.BusinessRuleError):
            a.update_room(self.conn,1,x['room_id'],changed)
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['street_name'],sample_room()['street_name'])

    def test_sql_transaction_examples(self):
        from housematch.db import ROOT
        self.conn.execute('TRUNCATE app_user,property_characteristics RESTART IDENTITY CASCADE')
        seed_demo(self.conn)
        try:
            self.conn.execute((ROOT/'housematch_transactions.sql').read_text(encoding='utf-8'))
        finally:
            self.conn.rollback()
        self.assertEqual(a.listing_detail(self.conn,1)['status'],'CLOSED')
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM listing').fetchone()['n'],13)


if __name__=='__main__':
    unittest.main(verbosity=2)
