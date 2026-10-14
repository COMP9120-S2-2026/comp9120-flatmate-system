"""Run from VS Code or a terminal without setting PYTHONPATH."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from housematch.cli import main

if __name__ == '__main__':
    # The VS Code Run button lists rooms; other commands accept normal CLI args.
    raise SystemExit(main(sys.argv[1:] or ['list', '--status', 'OPEN']))
