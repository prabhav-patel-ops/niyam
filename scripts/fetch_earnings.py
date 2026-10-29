"""Cache Yahoo earnings calendars as evidence, never assumed fundamental release dates."""
import argparse
import concurrent.futures
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.fetch_yahoo import universe,parquet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',required=True)
    parser.add_argument('--data-dir',default='data')
    parser.add_argument('--workers',type=int,default=2,choices=[1,2])
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    import yfinance as yf
    from app.models import completed_through
    root=Path(args.data_dir).resolve()/'providers'/'yahoo';root.mkdir(parents=True,exist_ok=True)
    yf.set_tz_cache_location(str(root/'cache'));yf.config.debug.hide_exceptions=False
    symbols,_=universe(args.source_dir)
    if args.limit:symbols=symbols[:args.limit]
    state_path=root/'earnings_status.json'
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'symbols':{}}
    guard=threading.Lock();last=[0.0];stop=threading.Event()
    def fetch(symbol):
        old=state['symbols'].get(symbol)
        if old and old.get('state')!='pending':return symbol,old
        if stop.is_set():return symbol,{'state':'pending'}
        with guard:
            delay=max(0,.8-(time.monotonic()-last[0]))
            if delay:time.sleep(delay)
            last[0]=time.monotonic()
        try:
            frame=yf.Ticker(symbol).get_earnings_dates(limit=100)
            if frame is None or frame.empty:return symbol,{'state':'unavailable'}
            out=frame.copy();out['event_at_provider']=[str(x) for x in frame.index];out['symbol']=symbol
            out['is_future']=[x.date()>completed_through() for x in frame.index]
            out['usable_for_point_in_time']=False
            out=out.reset_index(drop=True)
            parquet(out,root/'earnings'/f'{symbol}.parquet')
            return symbol,{'state':'downloaded','rows':len(out),'first':min(out.event_at_provider),'last':max(out.event_at_provider),
                          'fundamental_period_match':'not supplied by this calendar endpoint','usable_for_point_in_time':False}
        except Exception as error:
            if 'RateLimit' in type(error).__name__ or '429' in str(error):stop.set()
            return symbol,{'state':'failed','error_type':type(error).__name__,'error':str(error)[:180]}
    def save():
        temp=state_path.with_suffix('.pending');temp.write_text(json.dumps(state,indent=2),encoding='utf-8');temp.replace(state_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(fetch,s) for s in symbols]
        for i,future in enumerate(concurrent.futures.as_completed(futures),1):
            symbol,result=future.result();state['symbols'][symbol]=result
            if i%25==0 or i==len(futures) or stop.is_set():
                save();print(json.dumps({'earnings_processed':i,'total':len(futures),'downloaded':sum(v.get('state')=='downloaded' for v in state['symbols'].values()),'rate_limit_stop':stop.is_set()}),flush=True)
            if stop.is_set():
                for task in futures:task.cancel()
                break
    save()

if __name__=='__main__':main()
