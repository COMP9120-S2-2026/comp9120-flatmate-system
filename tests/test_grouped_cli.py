"""Exercise the restored interactive CLI against an isolated PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import os
import threading
import unittest
import uuid
from unittest.mock import patch
import psycopg
from psycopg import sql
from housematch.db import ROOT

spec = importlib.util.spec_from_file_location('grouped_menu', ROOT/'housematch_cli.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class GroupedCliTests(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ.get('TEST_DATABASE_URL')
        if not self.dsn:
            self.skipTest('TEST_DATABASE_URL is required.')
        self.schema = 'hm_menu_' + uuid.uuid4().hex
        self.conn = psycopg.connect(self.dsn)
        self.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        self.conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
        for filename in ('housematch_schema.sql', 'housematch_triggers.sql', 'housematch_sample_data.sql'):
            self.conn.execute((ROOT/filename).read_text())
        self.conn.commit()

    def tearDown(self):
        self.conn.rollback()
        self.conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))
        self.conn.commit()
        self.conn.close()

    def call(self, function, *args, answers=('Y',)):
        with patch('builtins.input', side_effect=answers), redirect_stdout(StringIO()) as output:
            result = function(self.conn, *args)
        return result, output.getvalue()

    def snapshot(self):
        return [self.conn.execute(f'SELECT * FROM {table} ORDER BY 1,2').fetchall()
                for table in ('application', 'listing', 'viewing_booking', 'viewing_slot')]

    def test_accept_commits_all_effects(self):
        self.assertTrue(self.call(menu.update_application_status, 1, 1, 'ACCEPTED')[0])
        self.assertEqual(self.conn.execute('SELECT status FROM application WHERE listing_id=1 ORDER BY application_id').fetchall(),
                         [('ACCEPTED',), ('REJECTED',), ('REJECTED',)])
        for table in ('viewing_booking', 'viewing_slot'):
            self.assertEqual(self.conn.execute(f"SELECT count(*) FROM {table} WHERE listing_id=1 AND status <> 'CANCELLED'").fetchone()[0], 0)
        self.assertEqual(self.conn.execute('SELECT status FROM listing WHERE listing_id=1').fetchone()[0], 'CLOSED')
        with psycopg.connect(self.dsn) as observer:
            observer.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
            self.assertEqual(observer.execute('SELECT status FROM application WHERE application_id=1').fetchone()[0], 'ACCEPTED')

    def test_failure_at_final_step_rolls_back_every_table(self):
        self.conn.execute("""CREATE FUNCTION fail_close() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.status='CLOSED' THEN RAISE EXCEPTION 'Injected failure'; END IF;
            RETURN NEW; END $$""")
        self.conn.execute('CREATE TRIGGER test_failure BEFORE UPDATE ON listing FOR EACH ROW EXECUTE FUNCTION fail_close()')
        self.conn.commit()
        before = self.snapshot()
        self.assertFalse(self.call(menu.update_application_status, 1, 1, 'ACCEPTED')[0])
        self.assertEqual(self.snapshot(), before)

    def test_invalid_owner_missing_application_and_cancel_change_nothing(self):
        before = self.snapshot()
        for owner, app in ((2, 1), (1, 999999)):
            self.assertFalse(self.call(menu.update_application_status, owner, app, 'ACCEPTED')[0])
        self.assertFalse(self.call(menu.update_application_status, 1, 1, 'ACCEPTED', answers=('N',))[0])
        self.assertEqual(self.snapshot(), before)

    def test_closed_listing_and_processed_application_are_rejected(self):
        self.conn.execute("UPDATE listing SET status='CLOSED' WHERE listing_id=1")
        self.conn.commit()
        before = self.snapshot()
        self.assertFalse(self.call(menu.update_application_status, 1, 1, 'ACCEPTED')[0])
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.call(menu.update_application_status, 1, 4, 'REJECTED')[0])
        before = self.snapshot()
        self.assertFalse(self.call(menu.update_application_status, 1, 4, 'ACCEPTED')[0])
        self.assertEqual(self.snapshot(), before)

    def test_competing_cli_acceptances_have_one_winner(self):
        barrier = threading.Barrier(2)
        def accept(app_id):
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
                conn.execute("SET lock_timeout='5s'")
                conn.commit()
                barrier.wait(timeout=5)
                return menu.update_application_status(conn, 1, app_id, 'ACCEPTED')
        with patch('builtins.input', return_value='Y'), redirect_stdout(StringIO()):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(accept, (1, 2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM application WHERE listing_id=1 AND status='ACCEPTED'").fetchone()[0], 1)

    def test_profile_creation_search_and_save_remove(self):
        self.call(menu.create_preference_profile, 5,
                  answers=('Integration', '0', '1000', 'Newtown', '', '3', '3', ''))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM preferred_suburb WHERE user_id=5 AND profile_name='Integration'").fetchone()[0], 1)
        _, output = self.call(menu.search_listings, 5, 'Integration', answers=('0',))
        self.assertIn('SEARCH RESULTS', output)
        self.call(menu.save_listing, 5, 1, answers=())
        self.call(menu.save_listing, 5, 1, answers=())
        self.assertEqual(self.conn.execute('SELECT count(*) FROM saves WHERE user_id=5 AND listing_id=1').fetchone()[0], 1)
        self.assertTrue(self.call(menu.remove_saved_listing, 5, 1)[0])

    def test_book_cancel_rebook_and_apply(self):
        self.call(menu.book_viewing, 5, 1, answers=('1', 'Y', ''))
        booking = self.conn.execute('SELECT booking_id FROM viewing_booking WHERE user_id=5 AND listing_id=1').fetchone()[0]
        self.assertTrue(self.call(menu.cancel_viewing, 5, booking)[0])
        self.call(menu.book_viewing, 5, 1, answers=('1', 'Y', ''))
        self.assertEqual(self.conn.execute('SELECT booking_id,status FROM viewing_booking WHERE user_id=5 AND listing_id=1').fetchall(), [(booking, 'CONFIRMED')])
        self.call(menu.apply_for_listing, 5, 1, answers=('Interested', 'Y', ''))
        self.call(menu.apply_for_listing, 5, 1, answers=('',))
        self.assertEqual(self.conn.execute('SELECT status FROM application WHERE user_id=5 AND listing_id=1').fetchall(), [('PENDING',)])
