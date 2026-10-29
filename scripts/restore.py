"""Restore a verified account backup into a NEW private state directory."""
import argparse
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def restore(source,target):
    source=Path(source).resolve()
    target=Path(target).resolve()
    web=Path(__file__).resolve().parents[1]/'web'
    if target==web or web in target.parents or target.exists():
        raise ValueError('Choose a new private state directory outside web/. Existing state is never overwritten.')
    if not source.is_file():
        raise ValueError('The backup file does not exist.')
    with sqlite3.connect(f'{source.as_uri()}?mode=ro',uri=True) as src:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or src.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('The backup failed its integrity checks.')
        expected={'users','sessions','strategies','attachments','jobs','watches','alerts','rate_limits'}
        tables={row[0] for row in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not expected.issubset(tables):
            raise ValueError('This is not a compatible Niyam account backup.')
        # New destination only; never copy over a running WAL database.
        target.mkdir(parents=True,exist_ok=False,mode=0o700)
        database=target/'niyam.sqlite3'
        try:
            database.touch(exist_ok=False,mode=0o600)
            with sqlite3.connect(database) as dest:
                src.backup(dest)
                dest.execute('DELETE FROM sessions')
                dest.execute("UPDATE jobs SET state='interrupted',cancel=0,error='Restored from backup. Run this experiment again.' WHERE state IN ('queued','running')")
                if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                    raise ValueError('The restored database failed its integrity check.')
        except BaseException:
            # Only remove the new files this operation owns, never existing state.
            for suffix in ['', '-wal', '-shm', '-journal']:
                Path(str(database)+suffix).unlink(missing_ok=True)
            target.rmdir()
            raise
    return database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='Private SQLite backup file.')
    parser.add_argument('--state-dir',required=True,help='NEW state directory. Must not exist.')
    args=parser.parse_args()
    try:restore(args.input,args.state_dir)
    except (ValueError,sqlite3.Error):
        raise SystemExit('Restore refused. Check backup integrity, schema and a new private destination.')
    print('Backup restored and checked. Existing sessions revoked; interrupted jobs require a new run. Start one service using the new state directory.')

if __name__=='__main__':main()
