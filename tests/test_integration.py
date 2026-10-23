"""Compatibility checks against Max's unchanged ten-table SQL."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import StringIO
import json
import os
import threading
import unittest
import uuid
from unittest.mock import patch

import psycopg
from psycopg import sql
from housematch import member_a as a, member_c as c
from housematch import cli
from housematch.db import ROOT, connect, initialise
from housematch.demo import sample_room, seed_demo


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get('TEST_DATABASE_URL')
        if not cls.dsn:
            raise unittest.SkipTest('TEST_DATABASE_URL is required.')
        cls.schema='hm_compat_'+uuid.uuid4().hex
        cls.conn=connect(cls.dsn)
        cls.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(cls.schema)))
        cls.conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(cls.schema)))
        try:
            initialise(cls.conn)
        except Exception:
            cls.conn.rollback()
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

    def test_original_schema_domains_and_no_new_indexes(self):
        tables=self.conn.execute("SELECT tablename FROM pg_tables WHERE schemaname=current_schema()").fetchall()
        self.assertEqual(len(tables),10)
        columns=self.conn.execute("""SELECT column_name FROM information_schema.columns
            WHERE table_schema=current_schema() AND table_name='room'""").fetchall()
        self.assertEqual({r['column_name'] for r in columns},
                         {'room_id','room_type','num_roommates','is_furnished','has_ensuite','description','property_id'})
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM preference_profile').fetchone()['n'],0)
        partial=self.conn.execute("""SELECT count(*) AS n FROM pg_index i
            JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace ns ON ns.oid=t.relnamespace
            WHERE ns.nspname=current_schema() AND i.indpred IS NOT NULL""").fetchone()['n']
        self.assertEqual(partial,0)

    def test_publish_supplies_required_listing_fields(self):
        x=self.publish()
        row=a.listing_detail(self.conn,x['listing_id'])
        self.assertEqual(row['status'],'OPEN')
        self.assertEqual(row['num_housemates'],2)
        self.assertIsNotNone(row['listing_date'])
        self.assertEqual(row['suburb'],'Newtown')
        self.assertIn('pet_friendly',row)
        self.assertEqual(len(a.list_listings(self.conn,'OPEN')),1)

    def test_publish_failure_rolls_back_property_room(self):
        with self.assertRaises(psycopg.Error):
            a.publish_new_room(self.conn,1,sample_room(),-1,'2026-11-01')
        for table in ('property_characteristics','room','listing'):
            self.assertEqual(self.conn.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier(table))).fetchone()['n'],0)

    def test_publish_unknown_user_rolls_back(self):
        with self.assertRaises(psycopg.Error):
            a.publish_new_room(self.conn,999,sample_room(),320,'2026-11-01')
        self.assertEqual(self.conn.execute('SELECT count(*) AS n FROM room').fetchone()['n'],0)

    def test_existing_property_room(self):
        x=self.publish(); prop=a.listing_detail(self.conn,x['listing_id'])['property_id']
        details={f:sample_room()[f] for f in a.ROOM_FIELDS}
        y=a.publish_new_room(self.conn,1,dict(details,property_id=prop),300,'2026-11-01')
        self.assertEqual(a.listing_detail(self.conn,y['listing_id'])['property_id'],prop)

    def test_update_close_relist_without_allocation_status(self):
        x=self.publish()
        a.update_listing(self.conn,1,x['listing_id'],330,'2026-11-02')
        details=sample_room(); details['description']='Updated room'
        a.update_room(self.conn,1,x['room_id'],details)
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['description'],'Updated room')
        a.close_listing(self.conn,1,x['listing_id'])
        new_id=a.create_listing_for_room(self.conn,1,x['room_id'],340,'2026-11-03')
        self.assertEqual(a.listing_detail(self.conn,new_id)['status'],'OPEN')

    def test_room_listing_owner_checks(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError):
            a.update_listing(self.conn,2,x['listing_id'],330,'2026-11-02')
        with self.assertRaises(a.BusinessRuleError):
            a.update_room_description(self.conn,2,x['room_id'],'Not mine')

    def test_active_listing_guard_includes_paused(self):
        x=self.publish()
        self.conn.execute("UPDATE listing SET status='PAUSED' WHERE listing_id=%s",(x['listing_id'],))
        with self.assertRaises(a.BusinessRuleError):
            a.create_listing_for_room(self.conn,1,x['room_id'],340,'2026-11-03')

    def test_application_queries_use_property_join_and_dictionary_rows(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'],'Hello')
        self.assertEqual(app['user_id'],2)
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['suburb'],'Newtown')
        applicants=c.list_listing_applicants(self.conn,1,x['listing_id'])
        self.assertEqual(applicants[0]['email'],'two@example.test')
        with self.assertRaises(a.BusinessRuleError):
            c.list_listing_applicants(self.conn,3,x['listing_id'])

    def test_reject_and_original_duplicate_rule(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        self.assertEqual(c.reject_application(self.conn,1,app['application_id'])['status'],'REJECTED')
        with self.assertRaises(psycopg.Error):
            c.submit_application(self.conn,2,x['listing_id'])

    def test_withdraw_is_explicitly_unsupported(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaisesRegex(a.BusinessRuleError,'not supported'):
            c.withdraw_application(self.conn,2,app['application_id'])
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['status'],'PENDING')

    def test_application_self_and_closed_guards(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError):
            c.submit_application(self.conn,1,x['listing_id'])
        a.close_listing(self.conn,1,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError):
            c.submit_application(self.conn,2,x['listing_id'])

    def test_accept_matches_original_sql_workflow(self):
        x=self.publish(); lid=x['listing_id']
        first=c.submit_application(self.conn,2,lid)
        c.submit_application(self.conn,3,lid)
        ts=self.conn.execute("SELECT CURRENT_TIMESTAMP::timestamp + INTERVAL '7 days' AS ts").fetchone()['ts']
        self.conn.execute('INSERT INTO viewing_slot(listing_id,viewing_timestamp) VALUES (%s,%s)',(lid,ts))
        self.conn.execute('INSERT INTO viewing_booking(user_id,listing_id,viewing_timestamp) VALUES (2,%s,%s)',(lid,ts))
        self.assertEqual(c.accept_application(self.conn,1,first['application_id'])['status'],'ACCEPTED')
        self.assertEqual(c.list_user_applications(self.conn,3)[0]['status'],'REJECTED')
        self.assertEqual(a.listing_detail(self.conn,lid)['status'],'CLOSED')
        self.assertEqual(self.conn.execute('SELECT status FROM viewing_booking').fetchone()['status'],'CANCELLED')
        self.assertEqual(self.conn.execute('SELECT status FROM viewing_slot').fetchone()['status'],'CANCELLED')

    def test_accept_owner_check(self):
        x=self.publish(); app=c.submit_application(self.conn,2,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError):
            c.accept_application(self.conn,3,app['application_id'])
        self.assertEqual(c.list_user_applications(self.conn,2)[0]['status'],'PENDING')

    def test_accept_failure_rolls_back_all_updates(self):
        x=self.publish(); lid=x['listing_id']
        app=c.submit_application(self.conn,2,lid)
        c.submit_application(self.conn,3,lid)
        self.conn.execute("""CREATE FUNCTION fail_test_close() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.status='CLOSED' THEN RAISE EXCEPTION 'Injected failure'; END IF; RETURN NEW; END $$""")
        self.conn.execute('CREATE TRIGGER fail_test_close BEFORE UPDATE ON listing FOR EACH ROW EXECUTE FUNCTION fail_test_close()')
        try:
            with self.assertRaises(psycopg.Error):
                c.accept_application(self.conn,1,app['application_id'])
            self.assertEqual(a.listing_detail(self.conn,lid)['status'],'OPEN')
            self.assertEqual(c.list_user_applications(self.conn,2)[0]['status'],'PENDING')
            self.assertEqual(c.list_user_applications(self.conn,3)[0]['status'],'PENDING')
        finally:
            self.conn.execute('DROP TRIGGER fail_test_close ON listing')
            self.conn.execute('DROP FUNCTION fail_test_close()')

    def test_two_sessions_accept_one_application(self):
        x=self.publish()
        ids=[c.submit_application(self.conn,u,x['listing_id'])['application_id'] for u in (2,3)]
        barrier=threading.Barrier(2)
        def attempt(app_id):
            with connect(self.dsn,self.schema) as conn:
                conn.execute("SET lock_timeout='5s'")
                barrier.wait(timeout=5)
                try:
                    c.accept_application(conn,1,app_id)
                    return 'accepted'
                except a.BusinessRuleError:
                    return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt,ids)),['accepted','blocked'])

    def test_seed_original_queries_and_transaction_examples(self):
        self.conn.execute('TRUNCATE app_user,property_characteristics RESTART IDENTITY CASCADE')
        self.assertEqual(seed_demo(self.conn),dict(users=14,properties=10,rooms=12,listings=12))
        for filename in ('housematch_queries.sql','sql/90_pgadmin_queries.sql','housematch_transactions.sql'):
            try:
                script=(ROOT/filename).read_text(encoding='utf-8')
                if filename=='sql/90_pgadmin_queries.sql':
                    # The pgAdmin example targets public; redirect only in this isolated test.
                    script=script.replace('public.',self.schema+'.')
                self.conn.execute(script)
            finally:
                self.conn.rollback()
        self.assertEqual(a.listing_detail(self.conn,1)['status'],'CLOSED')
        with self.assertRaises(psycopg.Error):
            seed_demo(self.conn)

    def test_original_max_sql_suite(self):
        notices=[]
        self.conn.add_notice_handler(lambda notice: notices.append(notice.message_primary))
        try:
            self.conn.execute((ROOT/'housematch_tests.sql').read_text(encoding='utf-8'))
        finally:
            self.conn.rollback()
        self.assertTrue(any('HOUSEMATCH AUTOMATED TESTS PASSED' in item for item in notices),notices[-3:])

    def test_cli_list_and_application_commands(self):
        x=self.publish()
        def execute(args):
            output=StringIO()
            with patch.object(cli,'connect',side_effect=lambda: connect(self.dsn,self.schema)), redirect_stdout(output):
                self.assertEqual(cli.main(args),0)
            return json.loads(output.getvalue())
        self.assertEqual(execute(['list'])[0]['suburb'],'Newtown')
        app=execute(['--user-id','2','apply',str(x['listing_id'])])
        self.assertEqual(execute(['--user-id','2','applications'])[0]['application_id'],app['application_id'])
        self.assertEqual(execute(['--user-id','1','accept',str(app['application_id'])])['status'],'ACCEPTED')

    def test_original_grouped_menu_and_profile_view(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('original_menu',ROOT/'housematch_cli.py')
        menu=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(menu)
        self.conn.execute('TRUNCATE app_user,property_characteristics RESTART IDENTITY CASCADE')
        seed_demo(self.conn)
        # Max's entry point uses tuple rows rather than the service connection's dict rows.
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
            name=menu.get_user_name(conn,1)
            self.assertEqual(name,'Olivia Chen')
            uid=self.conn.execute('SELECT user_id FROM preference_profile LIMIT 1').fetchone()['user_id']
            output=StringIO()
            with patch('builtins.input',side_effect=['1','0','0','0']), redirect_stdout(output):
                menu.view_preference_profiles(conn,uid,None)
                menu.main_menu(conn,1,name,None)
            self.assertIn('Minimum weekly rent:',output.getvalue())
            self.assertIn('6. Manage Applications (Owner)',output.getvalue())


if __name__=='__main__':
    unittest.main()
