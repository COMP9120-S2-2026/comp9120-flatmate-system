import json
import os
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]


def connect(database_url=None, schema=None):
    # Explicit URLs (including isolated tests) win. Local config takes priority
    # over environment variables left over from an earlier terminal session.
    if database_url:
        conn = psycopg.connect(database_url, autocommit=True, row_factory=dict_row)
    elif (ROOT / 'config.json').exists():
        try:
            config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8-sig'))
            if not isinstance(config, dict):
                raise ValueError()
            required = ('host', 'port', 'dbname', 'user', 'password')
            if any(key not in config for key in required):
                raise ValueError()
            port = int(config['port'])
            if not 1 <= port <= 65535:
                raise ValueError()
            if any(not isinstance(config[key], str) for key in required if key != 'port'):
                raise ValueError()
            if config['password'] == 'REPLACE_WITH_YOUR_POSTGRES_PASSWORD':
                raise ValueError()
        except (ValueError, TypeError, OSError):
            raise ValueError('Check config.json: host, port, dbname, user and password are required.') from None
        conn = psycopg.connect(
            host=config['host'], port=port, dbname=config['dbname'],
            user=config['user'], password=config['password'],
            connect_timeout=5, autocommit=True, row_factory=dict_row,
        )
    else:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError('Create config.json from config.example.json, or set DATABASE_URL.')
        conn = psycopg.connect(database_url, autocommit=True, row_factory=dict_row)
    if schema:
        conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    return conn


def initialise(conn):
    """Create the report's ten-table schema in an empty schema; no reset/drop."""
    with conn.transaction():
        for name in ['housematch_schema.sql', 'housematch_triggers.sql']:
            conn.execute((ROOT / name).read_text(encoding='utf-8'))
