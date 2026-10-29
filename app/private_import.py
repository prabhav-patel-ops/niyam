"""Private source warehouse. Fiscal periods are never treated as release dates."""
import calendar
import csv
from datetime import date,datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET
import duckdb
import pandas as pd

SOURCE_FILES=(
 'all_stocks_BV_data_20y.csv','all_stocks_EPS_data_20y.csv','all_stocks_FCF_data_20y.csv',
 'all_stocks_revenue_data_20y.csv','all_stocks_ROCE_data_20y.csv','all_stocks_ROE_data_20y.csv',
 'all_stocks_shares_outstanding_20y.csv','BV_EPS_SharesOutstanding_capitalEmployed.csv',
 'capital Employed.csv','CFO_Capex.csv','CFo_Capex_2009.csv','company_ticker_map.csv',
 'InterestExpense_PBT.csv','merged_adjusted_close.csv','merged_indices_close.csv',
 'merged_unadjusted_close.csv','Mkt Cap.csv','osc_sheet_W188.csv','other fundamentals 1.csv',
 'other fundamentals.csv','PBT_Interest_Expense.csv','portfolio_metrics_reference.csv',
 'Revenue_Consolidated2009.csv','Revenue_Standalone2009.csv','ROE.csv','ROE-2009.csv',
 'sector_map.xlsx','turnover_daily.csv')
TABLES={
 'closes':'source_file VARCHAR,source_row BIGINT,source_column BIGINT,company VARCHAR,symbol VARCHAR,mapping_status VARCHAR,date DATE,price_basis VARCHAR,close DOUBLE',
 'indices':'source_file VARCHAR,source_row BIGINT,source_column BIGINT,index_name VARCHAR,date DATE,close DOUBLE',
 'fundamentals':'source_file VARCHAR,source_row BIGINT,source_column BIGINT,company VARCHAR,symbol VARCHAR,mapping_status VARCHAR,metric VARCHAR,period_label VARCHAR,period_month DATE,value DOUBLE,unit VARCHAR,reporting_basis VARCHAR,available_at TIMESTAMP',
 'turnover':'source_file VARCHAR,source_row BIGINT,source_column BIGINT,company VARCHAR,symbol VARCHAR,mapping_status VARCHAR,date DATE,value DOUBLE,unit VARCHAR',
 'mapping':'company VARCHAR,symbol VARCHAR,match_method VARCHAR,match_score DOUBLE,review_status VARCHAR',
 'sectors':'source_file VARCHAR,source_sheet VARCHAR,source_row BIGINT,company VARCHAR,symbol VARCHAR,mapping_status VARCHAR,industry_group VARCHAR,industry_type VARCHAR,available_at TIMESTAMP',
 'reference':'source_file VARCHAR,source_sheet VARCHAR,source_row BIGINT,cells_json VARCHAR',
 'non_numeric':'source_file VARCHAR,source_row BIGINT,source_column BIGINT,company VARCHAR,field VARCHAR,period_label VARCHAR,value VARCHAR'}
METRICS={'BV':'bv','EPS':'eps','FCF':'fcf','Revenue':'revenue','ROCE':'roce','ROE':'roe','Shares':'shares_outstanding',
 'Capital employed':'capital_employed','Shares Outstanding':'shares_outstanding','Adjusted EPS':'eps','Book Value per Share':'bv',
 'Net cash flow from operating activities':'cfo','Cash (outflow) due to purchase of fixed assets':'capex',
 'Interest expenses':'interest_expense','Interest expense':'interest_expense','PBT':'pbt','Net sales':'revenue',
 'Return on net worth (Return on Equity)':'roe','Market Capitalisation':'market_cap'}
MONTHS={name:i for i,name in enumerate(calendar.month_abbr) if name}


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def month(label):
    match=re.fullmatch(r'([A-Za-z]{3})[ _](\d{2}|\d{4})',label.strip())
    if not match or match[1].title() not in MONTHS:return None
    year=int(match[2]);year=year+2000 if year<100 else year
    return date(year,MONTHS[match[1].title()],1)


def number(value):
    if value.strip().lower() in {'','-','--','na','n/a','nan','null','none'}:return None
    try:out=float(value.replace(',','').strip())
    except ValueError:return None
    return out if math.isfinite(out) else None


def ticker(value):
    value=value.strip().upper()
    return value if re.fullmatch(r'[A-Z0-9&_.-]{1,30}',value) else None


class Writer:
    def __init__(self,path):
        self.con=duckdb.connect(str(path));self.buffers={k:[] for k in TABLES};self.counts={k:0 for k in TABLES}
        for name,schema in TABLES.items():self.con.execute(f'CREATE TABLE {name} ({schema})')
    def add(self,table,row):
        self.buffers[table].append(row);self.counts[table]+=1
        if len(self.buffers[table])>=25000:self.flush(table)
    def flush(self,table):
        if not self.buffers[table]:return
        columns=[x.strip().split()[0] for x in TABLES[table].split(',')]
        frame=pd.DataFrame.from_records(self.buffers[table],columns=columns)
        self.con.register('import_batch',frame)
        self.con.execute(f'INSERT INTO {table} SELECT * FROM import_batch')
        self.con.unregister('import_batch');self.buffers[table].clear()
    def finish(self):
        for table in TABLES:self.flush(table)
        self.con.execute('CHECKPOINT')


def workbook_rows(path):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    relns='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    with zipfile.ZipFile(path) as archive:
        shared=[]
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared=[''.join(t.text or '' for t in node.findall('.//s:t',ns)) for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        relationships={node.attrib['Id']:node.attrib['Target'] for node in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns):
            target=relationships[sheet.attrib[relns]];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            rows=[]
            for row in ET.fromstring(archive.read(target)).findall('s:sheetData/s:row',ns):
                values={}
                for cell in row.findall('s:c',ns):
                    letters=re.match(r'[A-Z]+',cell.attrib['r'])[0];column=0
                    for letter in letters:column=column*26+ord(letter)-64
                    value=cell.find('s:v',ns);value=value.text if value is not None else ''.join(t.text or '' for t in cell.findall('.//s:t',ns))
                    if cell.attrib.get('t')=='s':value=shared[int(value)]
                    values[column-1]=value
                rows.append([values.get(i,'') for i in range(max(values,default=-1)+1)])
            yield sheet.attrib['name'],rows


def import_collection(source,data_dir,adjustment_basis):
    source=Path(source).resolve();data_dir=Path(data_dir).resolve()
    missing=[name for name in SOURCE_FILES if not (source/name).is_file()]
    if missing:raise ValueError('Missing supplied files: '+', '.join(missing))
    destination=data_dir/'imports'/('algoanalytics-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6])
    raw=destination/'raw';raw.mkdir(parents=True,exist_ok=False)
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'source_directory':str(source),'warehouse':'warehouse.duckdb','files':[],
              'source_adjustment_basis':adjustment_basis,'fundamental_publication_dates':'not supplied; no point-in-time activation',
              'fundamental_period_policy':'period_month is the first day of the labelled month, never a publication date',
              'turnover_policy':'currency turnover is not share volume','source_data_uploaded':False}
    for name in SOURCE_FILES:
        path=source/name;before=sha256(path);shutil.copy2(path,raw/name)
        if sha256(raw/name)!=before or sha256(path)!=before:raise ValueError('Source changed during import: '+name)
        manifest['files'].append({'name':name,'bytes':path.stat().st_size,'sha256':before})
    writer=Writer(destination/'warehouse.duckdb')
    mapping={}
    with (raw/'company_ticker_map.csv').open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            symbol=ticker(row['Ticker']);score=number(row.get('match_score',''))
            status='candidate' if symbol else 'unmapped'
            if row['Company'] in mapping:raise ValueError('Duplicate company mapping.')
            mapping[row['Company']]=(symbol,status)
            writer.add('mapping',(row['Company'],symbol,row.get('match_method'),score,status))
    def identity(company):return mapping.get(company,(None,'unmapped'))
    def numeric_fund(name,rownum,col,company,symbol,status,field,label,value,unit,basis):
        metric=METRICS.get(field,field);numeric=number(value)
        if numeric is not None:
            writer.add('fundamentals',(name,rownum,col,company,symbol,status,metric,label,month(label),numeric,unit,basis,None))
        elif value.strip():writer.add('non_numeric',(name,rownum,col,company,field,label,value))
    try:
        for info in manifest['files']:
            name=info['name'];before=writer.counts.copy()
            if name=='company_ticker_map.csv':continue
            if name=='sector_map.xlsx':
                for sheet,rows in workbook_rows(raw/name):
                    for i,row in enumerate(rows,1):
                        writer.add('reference',(name,sheet,i,json.dumps(row,ensure_ascii=False)))
                        if sheet=='All companies with sectors' and i>1 and len(row)>=2:
                            symbol,status=identity(row[0]);writer.add('sectors',(name,sheet,i,row[0],symbol,status,row[1],row[2] if len(row)>2 else None,None))
                info['kind']='current sector reference; historical availability unknown'
            else:
                with (raw/name).open(encoding='utf-8-sig',newline='') as handle:
                    reader=csv.reader(handle);header=next(reader)
                    if name=='portfolio_metrics_reference.csv':
                        for i,row in enumerate(reader,2):writer.add('reference',(name,None,i,json.dumps(dict(zip(header,row)),ensure_ascii=False)))
                        info['kind']='reference text only; formulas are not executed'
                    elif name=='merged_indices_close.csv':
                        for i,row in enumerate(reader,2):
                            day=date.fromisoformat(row[0])
                            for j,value in enumerate(row[1:],1):
                                val=number(value)
                                if val is not None:writer.add('indices',(name,i,j+1,header[j],day,val))
                        info['kind']='index closes'
                    elif name=='merged_unadjusted_close.csv':
                        for i,row in enumerate(reader,2):
                            day=date.fromisoformat(row[0])
                            for j,value in enumerate(row[1:],1):
                                val=number(value)
                                if val is not None:writer.add('closes',(name,i,j+1,None,ticker(header[j]),'direct_ticker',day,'unadjusted',val))
                        info['kind']='unadjusted close reference; not OHLCV'
                    elif name in {'merged_adjusted_close.csv','turnover_daily.csv'}:
                        offset=2 if name=='turnover_daily.csv' else 1
                        dates=[date.fromisoformat(v) for v in header[offset:]]
                        for i,row in enumerate(reader,2):
                            company=row[0];symbol,status=(ticker(row[1]),'direct_ticker') if offset==2 else identity(company)
                            for j,(day,value) in enumerate(zip(dates,row[offset:]),offset):
                                val=number(value)
                                if val is None:continue
                                if offset==1:writer.add('closes',(name,i,j+1,company,symbol,status,day,adjustment_basis,val))
                                else:writer.add('turnover',(name,i,j+1,company,symbol,status,day,val,'unverified'))
                        info['kind']='monetary turnover; not volume' if offset==2 else 'adjusted close reference; not OHLCV'
                    elif name.startswith('all_stocks_'):
                        for i,row in enumerate(reader,2):
                            symbol=ticker(row[0])
                            for j,value in enumerate(row[1:],1):
                                field,label=header[j].split('_',1)
                                unit='percentage_points' if field in {'ROE','ROCE'} else 'unverified'
                                numeric_fund(name,i,j+1,None,symbol,'direct_ticker',field,label.replace('_',' '),value,unit,'derived source; statement basis unverified')
                        info['kind']='period financial values; publication dates missing'
                    elif name=='osc_sheet_W188.csv':
                        meta=[header]+[next(reader) for _ in range(7)];companies=meta[7]
                        for i,row in enumerate(reader,9):
                            day=datetime.strptime(row[0],'%d %b %Y').date()
                            for j,value in enumerate(row[1:],1):
                                val=number(value)
                                if val is not None:
                                    company=companies[j];symbol,status=identity(company)
                                    writer.add('turnover',(name,i,j+1,company,symbol,status,day,val,meta[5][j]))
                        info['kind']='monetary turnover; not volume'
                    else:
                        meta=[header]+[next(reader) for _ in range(5)]
                        if meta[5][0]!='Company Name':raise ValueError('Unknown multi-row header in '+name)
                        for i,row in enumerate(reader,7):
                            company=row[0];symbol,status=identity(company)
                            for j,value in enumerate(row[1:],1):
                                field=meta[5][j];basis=meta[2][j]
                                if field=='Information Type':
                                    if value.strip():writer.add('non_numeric',(name,i,j+1,company,field,meta[4][j],value))
                                    continue
                                numeric_fund(name,i,j+1,company,symbol,status,field,meta[4][j],value,meta[3][j] or 'unverified',basis)
                        info['kind']='vendor financial values; publication dates missing'
            info['normalised_rows']={k:writer.counts[k]-before[k] for k in TABLES if writer.counts[k]!=before[k]}
            print(json.dumps({'imported':name,'rows':info.get('normalised_rows',{})}),flush=True)
        writer.finish()
        manifest['table_rows']=writer.counts
        con=writer.con
        manifest['mapping_summary']=con.execute("SELECT COUNT(*),COUNT(symbol),COUNT(DISTINCT symbol),SUM(CASE WHEN match_score<0.95 THEN 1 ELSE 0 END) FROM mapping").fetchone()
        manifest['close_coverage']=[dict(zip(['source_file','observations','symbols','first_date','last_date'],row)) for row in con.execute('SELECT source_file,COUNT(*),COUNT(DISTINCT symbol),CAST(MIN(date) AS VARCHAR),CAST(MAX(date) AS VARCHAR) FROM closes GROUP BY source_file').fetchall()]
        manifest['benchmark_candidates']=con.execute("SELECT COUNT(*),CAST(MIN(date) AS VARCHAR),CAST(MAX(date) AS VARCHAR),COUNT(DISTINCT date) FROM indices WHERE index_name='NIFTY 50'").fetchone()
        manifest['source_files']=len(SOURCE_FILES)
        manifest['remaining_requirements']=['Daily OHLCV, not only closes','Verified publication timestamps and historical vintages for fundamentals','Review ambiguous/company ticker mappings and statement/monetary units','Reconcile calendars, corporate actions, delistings and costs','Backend AI credentials and a running backend host']
    finally:writer.con.close()
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    pointer=data_dir/'imports'/'latest.json';temp=pointer.with_suffix('.pending')
    temp.write_text(json.dumps({'collection':destination.name}),encoding='utf-8');temp.replace(pointer)
    return destination,manifest
