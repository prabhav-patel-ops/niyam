"""End-of-day paper signals. No broker orders and no fabricated live prices."""
from datetime import datetime,time as clock
from zoneinfo import ZoneInfo
import json
import threading
import time
from . import store
from .data import load_dataset
from .models import Strategy
from .engine import run_backtest

LOCK=threading.Lock()


def latest_closed_date(benchmark,now=None):
    now=now or datetime.now(ZoneInfo('Asia/Kolkata'))
    allowed=[d for d in benchmark.index if d.date()<now.date() or d.date()==now.date() and now.time()>=clock(16,0)]
    return allowed[-1].date() if allowed else None


def refresh():
    if not LOCK.acquire(blocking=False):
        return
    try:
        with store.db() as c:
            watches=c.execute('SELECT * FROM watches WHERE active=1').fetchall()
        if not watches:
            return
        frames,benchmark,_=load_dataset()
        latest=latest_closed_date(benchmark)
        if not latest:
            return
        for watch in watches:
            try:
                if watch['last_date'] and str(latest)<=watch['last_date']:
                    continue
                spec=Strategy.model_validate_json(watch['spec'])
                spec=Strategy.model_validate({**spec.model_dump(mode='json'),'end':str(latest)})
                result=run_backtest(spec,frames,benchmark,finalise=False)
                with store.db() as c:
                    if watch['last_date']:
                        for position in result['positions']:
                            if position['next_action']=='HOLD':
                                continue
                            body={'name':spec.name,**position,'data_as_of':str(latest),'timing':'Condition at close; actionable at next session open.',
                                  'basis':'Historical paper model, not actual broker holdings. Daily data cannot provide an intraday stop alert.'}
                            c.execute('INSERT OR IGNORE INTO alerts VALUES(?,?,?,?,?,?,?,?)',
                                (store.new_id(),watch['user_id'],watch['id'],str(latest),position['symbol'],position['next_action'],store.dump(body),time.time()))
                        for trade in result['trades']:
                            if trade['exit_date']==str(latest) and trade['reason']=='Stop loss':
                                body={'name':spec.name,**trade,'timing':'Stop observed in a completed daily candle, not a real-time fill notification.',
                                      'basis':'Historical paper model; verify actual holdings before acting.'}
                                c.execute('INSERT OR IGNORE INTO alerts VALUES(?,?,?,?,?,?,?,?)',
                                    (store.new_id(),watch['user_id'],watch['id'],str(latest),trade['symbol'],'STOP_OBSERVED',store.dump(body),time.time()))
                    c.execute('UPDATE watches SET last_date=?,error=NULL WHERE id=?',(str(latest),watch['id']))
            except Exception as error:
                with store.db() as c:
                    c.execute('UPDATE watches SET error=? WHERE id=?',(str(error) if isinstance(error,ValueError) else 'Signal evaluation failed; inspect data and retry.',watch['id']))
    finally:
        LOCK.release()


def loop(stop):
    while not stop.wait(60):
        try:
            from .feed import refresh as refresh_feed
            refresh_feed()
            refresh()
        except Exception:
            import logging
            logging.exception('Signal scan failed')
