"""Publish validated Yahoo OHLCV plus the supplied Nifty 50 benchmark privately."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import duckdb
import pandas as pd
from .private_import import sha256
from .models import completed_through


def sql_path(path):return "'"+str(Path(path)).replace("'","''")+"'"


def install(data_dir):
    root=Path(data_dir).resolve()
    imports=root/'imports'
    collection=json.loads((imports/'latest.json').read_text(encoding='utf-8'))['collection']
    folder=(imports/collection).resolve()
    if folder.parent!=imports:raise ValueError('Invalid private collection pointer.')
    state=json.loads((root/'providers/yahoo/download_status.json').read_text(encoding='utf-8'))
    cached=root/'providers/yahoo/prices'
    paths=[cached/(symbol+'.parquet') for symbol,status in state['symbols'].items() if symbol!='^NSEI' and status.get('state')=='downloaded']
    if not paths:raise ValueError('No validated Yahoo equity history has been downloaded.')
    if any(not p.is_file() for p in paths):raise ValueError('A completed download is missing its private cache file.')
    for kind in ['prices','benchmark','fundamentals']:(root/kind).mkdir(parents=True,exist_ok=True)
    price_file=root/'prices/yahoo_equities.parquet';benchmark_file=root/'benchmark/managed_nifty50.parquet'
    for kind,allowed in [('prices',price_file),('benchmark',benchmark_file)]:
        if any(p!=allowed and p.name!='_daily_feed.csv' for p in (root/kind).iterdir() if p.suffix.lower() in {'.csv','.parquet'}):
            raise ValueError('Existing canonical files need an explicit merge review before installing this collection.')
    report={'created_at':datetime.now(timezone.utc).isoformat(),'collection':collection,'source_files':len(json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['files']),
            'prices':'Yahoo OHLC, auto_adjust=False, no dividend-adjusted Adj Close',
            'fundamentals':'staged only; verified availability dates and units required',
            'failed_symbols':{k:v for k,v in state['symbols'].items() if k!='^NSEI' and v.get('state')!='downloaded'}}
    with duckdb.connect(':memory:') as con:
        con.execute("SET memory_limit='768MB'")
        con.execute('SET temp_directory='+sql_path(root/'providers/yahoo/work'))
        con.execute('ATTACH '+sql_path(folder/'warehouse.duckdb')+' AS supplied (READ_ONLY)')
        con.execute('CREATE TEMP TABLE base_benchmark AS SELECT date,close FROM supplied.indices WHERE index_name=\'NIFTY 50\'')
        if con.execute('SELECT COUNT(*)-COUNT(DISTINCT date) FROM base_benchmark').fetchone()[0]:raise ValueError('Duplicate Nifty dates in supplied data.')
        provider_index=cached/'INDEX_NSEI.parquet'
        if provider_index.is_file():
            con.execute('CREATE TEMP VIEW provider_benchmark AS SELECT date,close FROM read_parquet('+sql_path(provider_index)+')')
            overlap,median,maximum=con.execute('SELECT COUNT(*),MEDIAN(ABS(b.close-y.close)/b.close),MAX(ABS(b.close-y.close)/b.close) FROM base_benchmark b JOIN provider_benchmark y USING(date)').fetchone()
            report['benchmark_reconciliation']={'overlap_sessions':overlap,'median_relative_difference':median,'maximum_relative_difference':maximum}
            if overlap<3 or maximum>.005:raise ValueError('Nifty price-index histories disagree. Inspect the private sources before merging.')
            con.execute('INSERT INTO base_benchmark SELECT y.date,y.close FROM provider_benchmark y ANTI JOIN base_benchmark b USING(date)')
        cutoff=str(completed_through())
        con.execute('DELETE FROM base_benchmark WHERE date>?',[cutoff])
        if con.execute('SELECT COUNT(*) FROM base_benchmark WHERE date IS NULL OR close IS NULL OR NOT isfinite(close) OR close<=0').fetchone()[0]:raise ValueError('Invalid Nifty benchmark rows.')
        con.execute('CREATE TEMP VIEW equity AS SELECT date,symbol,open,high,low,close,volume FROM read_parquet(['+','.join(sql_path(p) for p in paths)+'])')
        invalid=con.execute('SELECT COUNT(*) FROM equity WHERE date IS NULL OR symbol IS NULL OR NOT regexp_full_match(symbol,\'[A-Z0-9&_.-]{1,30}\') OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL OR NOT isfinite(open) OR NOT isfinite(high) OR NOT isfinite(low) OR NOT isfinite(close) OR NOT isfinite(volume) OR least(open,high,low,close)<=0 OR volume<0 OR high<greatest(open,low,close) OR low>least(open,high,close)').fetchone()[0]
        if invalid:raise ValueError('Invalid cached OHLCV rows; rerun provider validation.')
        if con.execute('SELECT COUNT(*) FROM (SELECT symbol,date FROM equity GROUP BY symbol,date HAVING COUNT(*)>1)').fetchone()[0]:raise ValueError('Duplicate cached symbol/date rows.')
        summary=con.execute('SELECT symbol,COUNT(*),CAST(MIN(date) AS VARCHAR),CAST(MAX(date) AS VARCHAR) FROM equity WHERE date<=? GROUP BY symbol ORDER BY symbol',[cutoff]).fetchall()
        symbol_rows=[{'symbol':s,'rows':n,'start':a[:10],'end':b[:10]} for s,n,a,b in summary if n>=3]
        report['symbols']=len(symbol_rows);report['price_rows']=sum(x['rows'] for x in symbol_rows)
        report['benchmark_rows'],report['benchmark_start'],report['benchmark_end']=con.execute('SELECT COUNT(*),CAST(MIN(date) AS VARCHAR),CAST(MAX(date) AS VARCHAR) FROM base_benchmark').fetchone()
        con.execute('CREATE TEMP VIEW ranges AS SELECT symbol,MIN(date) AS first_date,MAX(date) AS last_date FROM equity GROUP BY symbol')
        missing=con.execute('SELECT r.symbol,COUNT(*) FROM ranges r JOIN base_benchmark b ON b.date BETWEEN r.first_date AND r.last_date LEFT JOIN equity e ON e.symbol=r.symbol AND e.date=b.date WHERE e.date IS NULL GROUP BY r.symbol ORDER BY r.symbol').fetchall()
        extra=con.execute('SELECT symbol,COUNT(*) FROM equity e ANTI JOIN base_benchmark b USING(date) GROUP BY symbol ORDER BY symbol').fetchall()
        report['calendar_gaps']={s:n for s,n in missing};report['extra_stock_sessions']={s:n for s,n in extra}
        report['full_coverage_symbols']=len([x for x in symbol_rows if x['symbol'] not in dict(missing) and x['symbol'] not in dict(extra)])
        for item in symbol_rows:
            item['missing_sessions']=dict(missing).get(item['symbol'],0)
            item['extra_sessions']=dict(extra).get(item['symbol'],0)
        # Offer a working default before histories that need coverage repair.
        symbol_rows.sort(key=lambda x:(bool(x['missing_sessions'] or x['extra_sessions']),-x['rows'],x['symbol']))
        # Never add fabricated OHLCV, prices for missing sessions or pre-listing rows.
        price_temp=price_file.with_suffix('.pending');benchmark_temp=benchmark_file.with_suffix('.pending')
        con.execute('COPY (SELECT * FROM equity WHERE date<='+sql_path(cutoff)+' ORDER BY symbol,date) TO '+sql_path(price_temp)+' (FORMAT PARQUET)')
        con.execute('COPY (SELECT date,\'NIFTY50\' AS symbol,close FROM base_benchmark ORDER BY date) TO '+sql_path(benchmark_temp)+' (FORMAT PARQUET)')
        price_temp.replace(price_file);benchmark_temp.replace(benchmark_file)
    from . import data
    with data._lock:
        prior=data.DATA
        try:
            data.DATA=root
            sig=data.signature()
        finally:data.DATA=prior
    digest=hashlib.sha256()
    for p,_,_ in sig:
        digest.update(str(Path(p).relative_to(root)).replace('\\','/').encode());digest.update(b'\0')
        with Path(p).open('rb') as handle:
            for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
        digest.update(b'\0')
    version=digest.hexdigest()
    catalog={'symbols':symbol_rows,'rows':report['price_rows'],'benchmark_rows':report['benchmark_rows'],'benchmark_start':report['benchmark_start'],'benchmark_end':report['benchmark_end'],'version':version,'ready':bool(symbol_rows and report['benchmark_rows']>=3),'errors':[],
             'folders':{'prices':'data/prices/','benchmark':'data/benchmark/','fundamentals':'data/fundamentals/'}}
    metadata={'signature':[[str(Path(p).relative_to(root)).replace('\\','/'),size,mtime] for p,size,mtime in sig],'catalog':catalog}
    temp=root/'managed_catalog.pending';temp.write_text(json.dumps(metadata,indent=2),encoding='utf-8');temp.replace(root/'managed_catalog.json')
    report['data_version']=version
    (folder/'installation.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    data._cache.clear()
    return report
