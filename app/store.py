import contextlib
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=Path(os.getenv('NIYAM_STATE_DIR',ROOT/'var')).resolve()


@contextlib.contextmanager
def db():
    STATE.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(STATE/'niyam.sqlite3',timeout=20)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,name TEXT NOT NULL,password TEXT NOT NULL,created REAL NOT NULL,recovery_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS strategies(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),name TEXT NOT NULL,spec TEXT NOT NULL,updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),name TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),state TEXT NOT NULL,progress REAL NOT NULL DEFAULT 0,request TEXT NOT NULL,result TEXT,error TEXT,created REAL NOT NULL,cancel INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS watches(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),spec TEXT NOT NULL,active INTEGER NOT NULL,last_date TEXT,created REAL NOT NULL,error TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),watch_id TEXT NOT NULL REFERENCES watches(id),bar_date TEXT NOT NULL,symbol TEXT NOT NULL,action TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL,UNIQUE(watch_id,bar_date,symbol,action));
        CREATE INDEX IF NOT EXISTS jobs_owner ON jobs(user_id,created);
        CREATE INDEX IF NOT EXISTS alerts_owner ON alerts(user_id,created);
        ''')
        c.execute("UPDATE jobs SET state='interrupted',error='The backend restarted. You can run this job again.' WHERE state IN ('queued','running')")
        c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))


def password_hash(password):
    salt=secrets.token_bytes(16)
    value=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=64)
    return salt.hex()+':'+value.hex()


def verify(password,encoded):
    try:
        salt,wanted=encoded.split(':')
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64)
        return hmac.compare_digest(actual.hex(),wanted)
    except (ValueError,TypeError):
        return False


def session(user_id):
    token=secrets.token_urlsafe(40)
    with db() as c:
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user_id,time.time()+12*3600))
    return token


def user_for(token):
    with db() as c:
        return c.execute('SELECT u.id,u.email,u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',
                         (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()


def new_id():
    return secrets.token_hex(16)


def dump(value):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))
