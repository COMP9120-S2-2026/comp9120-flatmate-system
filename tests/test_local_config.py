"""Configuration tests; no database connection or credentials required."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from housematch import db


class LocalConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(db, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def write_config(self, **changes):
        config = dict(host='localhost', port=5432, dbname='housematch',
                      user='postgres', password='dummy-test-value')
        config.update(changes)
        (self.root / 'config.json').write_text(json.dumps(config), encoding='utf-8')

    @patch.object(db.psycopg, 'connect')
    def test_local_config_overrides_environment(self, connect):
        self.write_config()
        with patch.dict('os.environ', {'DATABASE_URL': 'old-environment-value'}):
            db.connect()
        self.assertEqual(connect.call_args.kwargs['dbname'], 'housematch')
        self.assertEqual(connect.call_args.kwargs['password'], 'dummy-test-value')

    @patch.object(db.psycopg, 'connect')
    def test_explicit_url_overrides_config(self, connect):
        self.write_config()
        db.connect('explicit-test-url')
        self.assertEqual(connect.call_args.args, ('explicit-test-url',))

    @patch.object(db.psycopg, 'connect')
    def test_environment_fallback(self, connect):
        with patch.dict('os.environ', {'DATABASE_URL': 'environment-value'}):
            db.connect()
        self.assertEqual(connect.call_args.args, ('environment-value',))

    def test_placeholder_rejected(self):
        self.write_config(password='REPLACE_WITH_YOUR_POSTGRES_PASSWORD')
        with self.assertRaises(ValueError):
            db.connect()

    def test_invalid_json_rejected_without_showing_contents(self):
        (self.root / 'config.json').write_text('invalid secret-content', encoding='utf-8')
        with self.assertRaises(ValueError) as caught:
            db.connect()
        self.assertNotIn('secret-content', str(caught.exception))

    def test_invalid_port_rejected(self):
        self.write_config(port=70000)
        with self.assertRaises(ValueError):
            db.connect()


if __name__ == '__main__':
    unittest.main()
