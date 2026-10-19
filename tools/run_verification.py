"""Record integrated test evidence from an actual PostgreSQL run."""
from pathlib import Path
from datetime import datetime
import contextlib
import io
import json
import os
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from housematch.db import connect


def main():
    if not os.environ.get('TEST_DATABASE_URL'):
        raise SystemExit('TEST_DATABASE_URL is required to record verification evidence.')
    with connect(os.environ['TEST_DATABASE_URL']) as conn:
        version=conn.execute('SHOW server_version').fetchone()['server_version']
    output=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    evidence=dict(server_version=version,tests_run=result.testsRun,
                  failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
                  success=result.wasSuccessful() and not result.skipped)
    evidence_dir=ROOT/'docs'
    evidence_dir.mkdir(parents=True,exist_ok=True)
    recorded_date=datetime.now().astimezone().strftime('%d %B %Y')
    (evidence_dir/'alignment_test_results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    (evidence_dir/'ALIGNMENT_TEST_RESULTS.md').write_text('# Integrated verification results\n\n'
        +'Recorded verification on '+recorded_date+' using PostgreSQL '+version+'.\n\n'
        +f"Tests run: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}; skipped: {len(result.skipped)}.\n\n"
        +'The run covers the canonical ten-table schema, A/B/C service integration, rollback, competing acceptances and bookings.\n\n'
        +'```text\n'+output.getvalue()+'```\n',encoding='utf-8')
    print(output.getvalue())
    print(json.dumps(evidence))
    return 0 if evidence['success'] else 1


if __name__=='__main__': raise SystemExit(main())
