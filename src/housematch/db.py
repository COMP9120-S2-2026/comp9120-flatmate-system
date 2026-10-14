import os
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]


def connect(database_url=None, schema=None):
    database_url = database_url or os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError('Set DATABASE_URL to your PostgreSQL connection string.')
    conn = psycopg.connect(database_url, autocommit=True, row_factory=dict_row)
    if schema:
        conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    return conn


def initialise(conn):
    """Create the A module and user contract in an empty schema; no reset/drop."""
    with conn.transaction():
        for name in ['00_user_contract.sql', '10_member_a.sql']:
            conn.execute((ROOT / 'sql' / name).read_text(encoding='utf-8'))
