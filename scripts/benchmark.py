"""Synthetic, in-memory workload. Excludes disk ingestion, AI and network latency."""
import json,sys,time,statistics,platform,resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from app.models import template,RunRequest
from app.engine import run_backtest
from app.jobs import optimise
n=3200;x=np.arange(n);dates=pd.bdate_range('2014-01-01',periods=n,name='date')
frames={}
for i in range(50):
 c=100+x*.02+12*np.sin(x/11+i*.1)+5*np.sin(x/37)
 frames[f'STOCK{i:02}']=pd.DataFrame({'open':c-.1,'high':c+1,'low':c-1,'close':c,'volume':100000},index=dates)
benchmark=frames['STOCK00'][['close']]
s=template();s.symbols=['STOCK00'];s.start=dates[0].date();s.end=dates[-1].date();s.price_basis_confirmed=True;s.stop.kind='none'
def measure(fn,repeats):
 times=[]
 for _ in range(repeats):
  t=time.perf_counter();fn();times.append(round((time.perf_counter()-t)*1000,2))
 return {'median_ms':statistics.median(times),'min_ms':min(times),'max_ms':max(times),'runs':repeats}
first=measure(lambda:run_backtest(s,frames,benchmark),1)
one=measure(lambda:run_backtest(s,frames,benchmark),5)
s.symbols=list(frames)
many=measure(lambda:run_backtest(s,frames,benchmark),5)
s.symbols=list(frames)[:10]
request=RunRequest(strategy=s,mode='optimise',search_space={'fast':[5,10,15,20],'slow':[25,30,35,40,45,50,55,60,65,70]},max_trials=40,min_trades=1)
search=measure(lambda:optimise(request,frames,benchmark,lambda p:None),3)
result={'python':platform.python_version(),'platform':platform.system(),'bars_per_stock':n,'first_call':first,'one_stock_warm':one,'fifty_stocks_warm':many,'forty_trials_ten_stocks':search,'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),'scope':'Synthetic loaded frames. Includes indicators, execution and report construction; excludes ingestion, model calls, API, queue, network and browser. Not a latency guarantee.'}
Path('docs/BENCHMARK.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
