"""Strict canonical CSV/Parquet ingestion; vendor-specific parsers are adapters."""
from pathlib import Path
from functools import lru_cache
import hashlib
import os
import threading
import duckdb
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.getenv('NIYAM_DATA_DIR',ROOT/'data')).resolve()
_lock=threading.RLock()
_cache={}


def files_for(kind):
    folder=DATA/kind
    folder.mkdir(parents=True,exist_ok=True)
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in {'.csv','.parquet'} and p.is_file())


def signature():
    return tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for kind in ['prices','benchmark','fundamentals'] for p in files_for(kind))


def read_table(path):
    with duckdb.connect(':memory:') as con:
        frame=(con.read_parquet(str(path)) if path.suffix.lower()=='.parquet' else con.read_csv(str(path),header=True)).df()
    frame.columns=[str(c).strip().lower() for c in frame.columns]
    return frame


def validate_prices(frame,benchmark=False):
    required={'date','close'} if benchmark else {'date','symbol','open','high','low','close','volume'}
    missing=required-set(frame.columns)
    if missing:
        raise ValueError('Missing columns: '+', '.join(sorted(missing))+'. See the Data guide for the canonical format.')
    frame=frame.copy()
    frame['date']=pd.to_datetime(frame['date'],format='%Y-%m-%d',errors='raise').dt.normalize()
    if frame['date'].isna().any():
        raise ValueError('Every price row needs a date.')
    if benchmark:
        if 'symbol' in frame and not frame['symbol'].astype(str).str.upper().isin(['NIFTY50','NIFTY 50']).all():
            raise ValueError('The benchmark folder must contain the Nifty 50 PRICE index, labelled NIFTY50. TRI is not interchangeable.')
        frame['symbol']='NIFTY50'
    else:
        frame['symbol']=frame['symbol'].astype(str).str.strip().str.upper()
        if not frame.symbol.str.fullmatch(r'[A-Z0-9&_.-]{1,30}').all():
            raise ValueError('One or more ticker symbols are invalid.')
    cols=['close'] if benchmark else ['open','high','low','close','volume']
    for col in cols:
        frame[col]=pd.to_numeric(frame[col],errors='raise').astype(float)
        if not np.isfinite(frame[col]).all() or (frame[col] < (0 if col=='volume' else 0.00000001)).any():
            raise ValueError(f'{col} contains missing, non-finite or invalid negative/zero prices.')
    if not benchmark:
        if ((frame.high<frame[['open','low','close']].max(axis=1))|(frame.low>frame[['open','high','close']].min(axis=1))).any():
            raise ValueError('Some OHLC rows are inconsistent: high must be highest and low must be lowest.')
    if frame.duplicated(['symbol','date']).any():
        raise ValueError('Duplicate symbol/date rows found. Resolve them before running a backtest.')
    return frame.sort_values(['symbol','date'])


def join_fundamentals(frame,fundamentals,symbol):
    part=fundamentals[fundamentals.symbol==symbol].copy()
    if part.empty:
        return frame
    # A date-only publication is conservatively usable starting the next calendar day.
    # This never lets a release later in the session affect that day's close decision.
    part['usable_date']=pd.to_datetime(part['available_at'],utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None).dt.normalize()+pd.Timedelta(days=1)
    if part.duplicated('usable_date').any():
        raise ValueError(f'{symbol}: multiple fundamental records become available on the same date; consolidate these explicitly.')
    fields=[x for x in ['roe','roce','pe','pb','ps'] if x in part]
    for x in fields:
        part[x]=pd.to_numeric(part[x],errors='raise')
    return pd.merge_asof(frame.reset_index().sort_values('date'),part[['usable_date']+fields].sort_values('usable_date'),
                         left_on='date',right_on='usable_date',direction='backward').drop(columns=['usable_date']).set_index('date')


def read_price_files(paths,benchmark=False):
    manual=[p for p in paths if p.name!='_daily_feed.csv']
    feed=[p for p in paths if p.name=='_daily_feed.csv']
    parts=[]
    if feed:parts.append(validate_prices(pd.concat([read_table(p) for p in feed],ignore_index=True),benchmark))
    if manual:parts.append(validate_prices(pd.concat([read_table(p) for p in manual],ignore_index=True),benchmark))
    # Explicit historical user files win over feed updates on overlaps.
    return validate_prices(pd.concat(parts,ignore_index=True).drop_duplicates(['symbol','date'],keep='last'),benchmark)


def load_dataset():
    with _lock:
        sig=signature()
        if sig in _cache:
            return _cache[sig]
        prices=files_for('prices'); benchmarks=files_for('benchmark'); funds=files_for('fundamentals')
        frames={}
        if prices:
            all_prices=read_price_files(prices)
            frames={symbol:part.drop(columns=['symbol']).set_index('date').sort_index() for symbol,part in all_prices.groupby('symbol')}
        benchmark=pd.DataFrame(columns=['close'],index=pd.DatetimeIndex([],name='date'))
        if benchmarks:
            benchmark=read_price_files(benchmarks,True).set_index('date')[['close']]
        if funds:
            f=pd.concat([read_table(p) for p in funds],ignore_index=True)
            if not {'symbol','available_at'}.issubset(f):
                raise ValueError('Fundamentals need symbol and available_at: the actual public release date, not the financial period end.')
            f['symbol']=f.symbol.astype(str).str.upper()
            frames={s:join_fundamentals(df,f,s) for s,df in frames.items()}
        digest=hashlib.sha256()
        for path,_,_ in sig:
            digest.update(Path(path).name.encode())
            with open(path,'rb') as handle:
                for block in iter(lambda:handle.read(1024*1024),b''):
                    digest.update(block)
        result=(frames,benchmark,digest.hexdigest())
        _cache.clear()
        _cache[sig]=result
        return result


def catalog():
    try:
        frames,benchmark,version=load_dataset()
        symbols=[{'symbol':s,'rows':len(df),'start':str(df.index[0].date()),'end':str(df.index[-1].date())} for s,df in frames.items()]
        return {'symbols':symbols,'rows':sum(x['rows'] for x in symbols),'benchmark_rows':len(benchmark),
                'benchmark_start':str(benchmark.index[0].date()) if len(benchmark) else None,
                'benchmark_end':str(benchmark.index[-1].date()) if len(benchmark) else None,
                'version':version,'ready':bool(symbols and len(benchmark)),'errors':[],
                'folders':{'prices':'data/prices/','benchmark':'data/benchmark/','fundamentals':'data/fundamentals/'}}
    except Exception as e:
        return {'symbols':[],'rows':0,'benchmark_rows':0,'ready':False,'errors':[str(e)],'folders':{'prices':'data/prices/','benchmark':'data/benchmark/','fundamentals':'data/fundamentals/'}}
