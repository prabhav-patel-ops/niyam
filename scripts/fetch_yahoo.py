"""Resumable, operator-only Yahoo OHLCV enrichment. No data is committed to Git."""
import argparse
import concurrent.futures
import csv
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import re
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import duckdb
import pandas as pd


def parquet(frame,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.pending')
    with duckdb.connect(':memory:') as con:
        con.register('frame',frame)
        con.execute("COPY frame TO '"+str(temp).replace("'","''")+"' (FORMAT PARQUET)")
    temp.replace(path)


def universe(source):
    with (Path(source)/'merged_unadjusted_close.csv').open(encoding='utf-8-sig',newline='') as handle:
        names=next(csv.reader(handle))[1:]
    valid=sorted({s.strip().upper() for s in names if re.fullmatch(r'[A-Za-z0-9&_.-]{1,30}',s.strip())})
    return valid,[s for s in names if s.strip().upper() not in valid]


def normalise_history(frame,symbol,end):
    from app.data import validate_prices
    if frame is None or frame.empty:raise ValueError('No price history returned.')
    frame=frame.copy()
    dates=pd.DatetimeIndex(frame.index)
    if dates.tz is not None:dates=dates.tz_convert('Asia/Kolkata').tz_localize(None)
    frame.index=dates.normalize()
    frame=frame.loc[frame.index<pd.Timestamp(end)]
    required=['Open','High','Low','Close','Volume']
    if any(k not in frame for k in required):raise ValueError('Provider history lacks OHLCV columns.')
    prices=frame[required].rename(columns=str.lower)
    prices.index.name='date';prices=prices.reset_index();prices['symbol']='NIFTY50' if symbol=='^NSEI' else symbol
    complete=prices[['open','high','low','close','volume']].notna().all(axis=1)
    removed=int((~complete).sum());prices=prices.loc[complete]
    prices=validate_prices(prices)
    actions=frame[[x for x in ['Dividends','Stock Splits','Capital Gains'] if x in frame]].copy()
    actions=actions.loc[(actions.fillna(0)!=0).any(axis=1)].reset_index();actions['symbol']=symbol
    return prices,actions,removed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',required=True)
    parser.add_argument('--data-dir',default='data')
    parser.add_argument('--start',default='2009-01-01')
    parser.add_argument('--end',default=None,help='Exclusive end; defaults to latest completed IST day plus one.')
    parser.add_argument('--workers',type=int,default=3,choices=[1,2,3,4])
    parser.add_argument('--limit',type=int)
    parser.add_argument('--retry-failed',action='store_true')
    parser.add_argument('--symbols',help='Optional comma-separated subset, including ^NSEI for the benchmark.')
    args=parser.parse_args()
    from app.models import completed_through
    end=args.end or str(completed_through()+timedelta(days=1))
    date.fromisoformat(args.start);date.fromisoformat(end)
    import yfinance as yf
    yf.config.debug.hide_exceptions=False
    root=Path(args.data_dir).resolve()/'providers'/'yahoo'
    root.mkdir(parents=True,exist_ok=True);yf.set_tz_cache_location(str(root/'cache'))
    symbols,rejected=universe(args.source_dir)
    if args.symbols:symbols=[s.strip().upper() for s in args.symbols.split(',') if s.strip()]
    if args.limit:symbols=symbols[:args.limit]
    symbols=list(dict.fromkeys(['^NSEI']+symbols))
    state_path=root/'download_status.json'
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'symbols':{}}
    state.update(start=args.start,end=end,adjustment='Yahoo Close/OHLC with auto_adjust=False; Adj Close excluded',rejected_identifiers=rejected)
    stop=threading.Event();guard=threading.Lock();last_start=[0.0]
    def fetch(symbol):
        filename=symbol.replace('^','INDEX_')
        old=state['symbols'].get(symbol,{})
        if old.get('state')=='downloaded' and old.get('start')==args.start and old.get('end')==end and (root/'prices'/f'{filename}.parquet').is_file():return symbol,old
        if old.get('state')=='failed' and old.get('start')==args.start and old.get('end')==end and not args.retry_failed:return symbol,old
        if stop.is_set():return symbol,{'state':'pending'}
        with guard:
            delay=max(0,.35-(time.monotonic()-last_start[0]))
            if delay:time.sleep(delay)
            last_start[0]=time.monotonic()
        try:
            frame=yf.Ticker(symbol).history(start=args.start,end=end,interval='1d',auto_adjust=False,back_adjust=False,actions=True,repair=False,keepna=True,timeout=25)
            prices,actions,removed=normalise_history(frame,symbol,end)
            parquet(prices,root/'prices'/f'{filename}.parquet')
            if not actions.empty:parquet(actions,root/'actions'/f'{filename}.parquet')
            return symbol,{'state':'downloaded','rows':len(prices),'first':str(prices.date.min().date()),'last':str(prices.date.max().date()),'incomplete_rows_removed':removed,'start':args.start,'end':end,'fetched_at':datetime.now(timezone.utc).isoformat()}
        except Exception as error:
            if 'RateLimit' in type(error).__name__ or '429' in str(error):stop.set()
            return symbol,{'state':'failed','error_type':type(error).__name__,'error':str(error)[:220],'start':args.start,'end':end}
    def save():
        temporary=state_path.with_suffix('.pending');temporary.write_text(json.dumps(state,indent=2,allow_nan=False),encoding='utf-8');temporary.replace(state_path)
    total=len(symbols)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(fetch,s):s for s in symbols}
        for i,future in enumerate(concurrent.futures.as_completed(pending),1):
            symbol,result=future.result();state['symbols'][symbol]=result
            if i%10==0 or i==total or stop.is_set():
                save();counts={k:sum(v.get('state')==k for v in state['symbols'].values()) for k in ['downloaded','failed','pending']}
                print(json.dumps({'processed':i,'total':total,**counts,'rate_limit_stop':stop.is_set()}),flush=True)
            if stop.is_set():
                for task in pending:task.cancel()
                break
    save()
    print('Private download checkpoint: '+str(state_path),flush=True)

if __name__=='__main__':main()
