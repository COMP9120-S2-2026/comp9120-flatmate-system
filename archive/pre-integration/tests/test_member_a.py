"""Real PostgreSQL integration tests, isolated in a newly created schema."""

from concurrent.futures import ThreadPoolExecutor
import os
import threading
import unittest
import uuid

import psycopg
from psycopg import sql
from housematch.db import connect, initialise
from housematch.demo import sample_room, seed_demo
from housematch import member_a as a


class MemberATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get('TEST_DATABASE_URL')
        if not cls.dsn:
            raise unittest.SkipTest('Set TEST_DATABASE_URL to run real PostgreSQL tests.')
        cls.schema='hm_a_test_'+uuid.uuid4().hex
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
        cls.conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(cls.schema)))
        cls.conn.close()

    def setUp(self):
        self.conn.execute('TRUNCATE listing,room,app_user RESTART IDENTITY CASCADE')
        self.conn.execute("INSERT INTO app_user(first_name,last_name,email) VALUES ('Alex','Morgan','alex@example.test'),('Jamie','Chen','jamie@example.test')")

    def publish(self, **overrides):
        room=sample_room(); room.update(overrides)
        return a.publish_new_room(self.conn,1,room,320,'2026-11-01')

    def counts(self):
        return tuple(self.conn.execute('SELECT (SELECT count(*) FROM room) AS rooms,(SELECT count(*) FROM listing) AS listings').fetchone().values())

    def test_publish_room_and_listing(self):
        x=self.publish()
        self.assertEqual(self.counts(),(1,1))
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['suburb'],'Newtown')

    def test_invalid_rent_rolls_back_room(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            a.publish_new_room(self.conn,1,sample_room(),0,'2026-11-01')
        self.assertEqual(self.counts(),(0,0))

    def test_unknown_advertiser_rolls_back_room(self):
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            a.publish_new_room(self.conn,999,sample_room(),320,'2026-11-01')
        self.assertEqual(self.counts(),(0,0))

    def test_nan_rent_rejected(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            a.publish_new_room(self.conn,1,sample_room(),'NaN','2026-11-01')
        self.assertEqual(self.counts(),(0,0))

    def test_negative_housemates_rejected(self):
        with self.assertRaises(psycopg.errors.CheckViolation): self.publish(num_housemates=-1)
        self.assertEqual(self.counts(),(0,0))

    def test_invalid_postcode_rejected(self):
        with self.assertRaises(psycopg.errors.CheckViolation): self.publish(postcode='ABC')

    def test_duplicate_open_listing_rejected_by_database(self):
        x=self.publish()
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.conn.execute("INSERT INTO listing(room_id,creator_user_id,weekly_rent,available_from) VALUES (%s,1,350,'2026-11-01')",(x['room_id'],))
        self.assertEqual(self.counts(),(1,1))

    def test_closed_history_allows_relisting(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        new=a.create_listing_for_room(self.conn,1,x['room_id'],340,'2026-11-05')
        self.assertNotEqual(new,x['listing_id']); self.assertEqual(self.counts(),(1,2))

    def test_closing_advert_does_not_occupy_room(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['allocation_status'],'AVAILABLE')

    def test_wrong_advertiser_cannot_close(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError): a.close_listing(self.conn,2,x['listing_id'])
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['status'],'OPEN')

    def test_wrong_advertiser_cannot_relist(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError): a.create_listing_for_room(self.conn,2,x['room_id'],320,'2026-11-01')

    def test_update_open_listing(self):
        x=self.publish()
        a.update_listing(self.conn,1,x['listing_id'],355,'2026-11-05')
        self.assertEqual(str(a.listing_detail(self.conn,x['listing_id'])['weekly_rent']),'355.00')

    def test_update_room_details(self):
        x=self.publish(); room=sample_room(); room.update(description='Updated',is_furnished=False)
        a.update_room(self.conn,1,x['room_id'],room)
        found=a.listing_detail(self.conn,x['listing_id'])
        self.assertEqual(found['description'],'Updated'); self.assertFalse(found['is_furnished'])

    def test_closed_listing_cannot_be_edited(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        with self.assertRaises(a.BusinessRuleError): a.update_listing(self.conn,1,x['listing_id'],330,'2026-11-01')

    def test_orphan_room_rejected_at_commit(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            with self.conn.transaction(): a._insert_room(self.conn,sample_room())
        self.assertEqual(self.counts(),(0,0))

    def test_deleting_last_listing_rejected(self):
        x=self.publish()
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute('DELETE FROM listing WHERE listing_id=%s',(x['listing_id'],))
        self.assertEqual(self.counts(),(1,1))

    def test_fill_helper_updates_both_states(self):
        x=self.publish()
        with self.conn.transaction(): a.mark_filled_in_transaction(self.conn,1,x['listing_id'])
        found=a.listing_detail(self.conn,x['listing_id'])
        self.assertEqual((found['status'],found['allocation_status']),('FILLED','UNAVAILABLE'))

    def test_fill_helper_cannot_commit_without_outer_transaction(self):
        x=self.publish()
        with self.assertRaises(a.BusinessRuleError): a.mark_filled_in_transaction(self.conn,1,x['listing_id'])

    def test_fill_helper_changes_roll_back_with_caller_failure(self):
        x=self.publish()
        with self.assertRaises(RuntimeError):
            with self.conn.transaction():
                a.mark_filled_in_transaction(self.conn,1,x['listing_id'])
                raise RuntimeError('Simulated later application failure')
        found=a.listing_detail(self.conn,x['listing_id'])
        self.assertEqual((found['status'],found['allocation_status']),('OPEN','AVAILABLE'))

    def test_unavailable_room_cannot_receive_open_listing(self):
        x=self.publish()
        with self.conn.transaction(): a.mark_filled_in_transaction(self.conn,1,x['listing_id'])
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("INSERT INTO listing(room_id,creator_user_id,weekly_rent,available_from) VALUES (%s,1,350,'2026-11-01')",(x['room_id'],))

    def test_room_cannot_be_unavailable_while_listing_open(self):
        x=self.publish()
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("UPDATE room SET allocation_status='UNAVAILABLE' WHERE room_id=%s",(x['room_id'],))

    def test_two_sessions_compete_to_relist(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id']); barrier=threading.Barrier(2)
        def attempt():
            with connect(self.dsn,self.schema) as c:
                c.execute("SET lock_timeout='5s'")
                barrier.wait(timeout=5)
                try: a.create_listing_for_room(c,1,x['room_id'],330,'2026-11-01'); return 'created'
                except a.BusinessRuleError: return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(sorted(results),['blocked','created']); self.assertEqual(self.counts(),(1,2))

    def test_parameterised_description_is_stored_as_text(self):
        x=self.publish(); text="Room'); DROP TABLE listing; --"
        a.update_room_description(self.conn,1,x['room_id'],text)
        self.assertEqual(a.listing_detail(self.conn,x['listing_id'])['description'],text)

    def test_competing_history_deletions_cannot_orphan_room(self):
        x=self.publish(); a.close_listing(self.conn,1,x['listing_id'])
        second=a.create_listing_for_room(self.conn,1,x['room_id'],330,'2026-11-01')
        a.close_listing(self.conn,1,second)
        barrier=threading.Barrier(2)
        def attempt(listing_id):
            with connect(self.dsn,self.schema) as c:
                c.execute("SET lock_timeout='5s'")
                try:
                    with c.transaction():
                        c.execute('DELETE FROM listing WHERE listing_id=%s',(listing_id,))
                        barrier.wait(timeout=5)
                    return 'removed'
                except psycopg.errors.CheckViolation: return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,[x['listing_id'],second]))
        self.assertEqual(sorted(results),['blocked','removed']); self.assertEqual(self.counts(),(1,1))

    def test_demo_seed_has_eight_rooms_and_history(self):
        self.conn.execute('TRUNCATE listing,room,app_user RESTART IDENTITY CASCADE')
        result=seed_demo(self.conn)
        self.assertEqual(self.counts(),(8,9)); self.assertEqual(len(a.list_listings(self.conn,'OPEN')),8)
        self.assertEqual(result['users'],[1,2,3])


if __name__=='__main__': unittest.main(verbosity=2)
