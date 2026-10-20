"""Optional operator-configured daily feed; never a user-supplied fetch target."""
from datetime import datetime,time
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
import json
import os
import threading
import time as timer
import httpx
import pandas as pd
from . import data

_LOCK=threading.Lock()
_last_attempt=0.0
_status={'configured':False,'last_success':None,'error':None}


def status():
    return {**_status,'configured':bool(os.getenv('DAILY_FEED_URL'))}


def ingest(payload,now=None):
    now=now or datetime.now(ZoneInfo('Asia/Kolkata'))
    if not isinstance(payload,dict) or set(payload)-{'prices','benchmark'}:
        raise ValueError('Feed must contain prices and/or benchmark arrays.')
    pending=[]
    with data._lock:
        for kind in ('prices','benchmark'):
            rows=payload.get(kind,[])
            if not isinstance(rows,list):raise ValueError('Feed records must be arrays.')
            if not rows:continue
            frame=data.validate_prices(pd.DataFrame(rows),kind=='benchmark')
            closed=(frame.date.dt.date<now.date())|((frame.date.dt.date==now.date())&(now.time()>=time(16)))
            frame=frame.loc[closed]
            if frame.empty:continue
            folder=data.DATA/kind;folder.mkdir(parents=True,exist_ok=True)
            target=folder/'_daily_feed.csv'
            if target.exists():
                old=data.read_table(target)
                old=data.validate_prices(old,kind=='benchmark')
                frame=pd.concat([old,frame],ignore_index=True).drop_duplicates(['symbol','date'],keep='last')
            frame=data.validate_prices(frame,kind=='benchmark')
            frame['date']=frame.date.dt.strftime('%Y-%m-%d')
            pending.append((target,frame))
        # Validate all streams before writing. Holding the catalog lock prevents partial reads.
        for target,frame in pending:
            temp=target.with_suffix('.tmp')
            frame.to_csv(temp,index=False)
            os.replace(temp,target)
        if pending:data._cache.clear()
    return sum(len(frame) for _,frame in pending)


def refresh(force=False):
    global _last_attempt
    url=os.getenv('DAILY_FEED_URL','').strip()
    if not url or not _LOCK.acquire(blocking=False):return status()
    try:
        if not force and timer.monotonic()-_last_attempt<300:return status()
        _last_attempt=timer.monotonic()
        parsed=urlsplit(url)
        if parsed.username or parsed.password or (parsed.scheme!='https' and not(parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1'})):
            raise ValueError('Use HTTPS for the daily feed, or HTTP on loopback.')
        headers={}
        if os.getenv('DAILY_FEED_API_KEY'):headers['Authorization']='Bearer '+os.environ['DAILY_FEED_API_KEY']
        with httpx.stream('GET',url,headers=headers,timeout=30,follow_redirects=False) as response:
            response.raise_for_status()
            chunks=[];size=0
            for block in response.iter_bytes():
                size+=len(block)
                if size>10*1024*1024:raise ValueError('Feed response exceeds 10 MB.')
                chunks.append(block)
        ingest(json.loads(b''.join(chunks)))
        _status.update(last_success=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),error=None)
    except Exception:
        # Provider errors can include signed URLs and credentials. Do not return raw errors.
        _status['error']='Daily feed could not be imported. Check URL, credentials, schema and completed bars.'
    finally:
        _LOCK.release()
    return status()
