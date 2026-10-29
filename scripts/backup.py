"""Create a consistent SQLite backup while the service is running."""
import argparse
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='New private .sqlite3 backup path, outside the web folder.')
    args=parser.parse_args()
    from app import main as service,store
    target=Path(args.output).resolve()
    web=service.ROOT/'web'
    if target==web or web in target.parents or target.exists():
        raise SystemExit('Use a new private path outside web/.')
    source=store.STATE/'niyam.sqlite3'
    if not source.is_file():raise SystemExit('No existing account database to back up.')
    target.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents overwriting an existing backup.
    target.touch(exist_ok=False,mode=0o600)
    try:
        with sqlite3.connect(f'{source.as_uri()}?mode=ro',uri=True) as src,sqlite3.connect(target) as dest:
            src.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Backup integrity check failed.')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    print('Private database backup created and integrity checked.')

if __name__=='__main__':main()
