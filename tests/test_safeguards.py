from datetime import datetime
from zoneinfo import ZoneInfo
import json
import numpy as np
import pandas as pd
import pytest
from app.models import Expr,template
from app.rules import Rules
from app.engine import run_backtest


def test_missing_value_cannot_become_entry_by_negation(prices):
    comparison=Expr(op='gt',args=[Expr(op='sma',window=50,args=[Expr(op='close')]),Expr(op='close')])
    rules=Rules(prices,{})
    assert not rules.signals(Expr(op='not',args=[comparison]))[:49].any()
    missing=prices.copy();missing['roe']=np.nan
    fund=Expr(op='not',args=[Expr(op='gt',args=[Expr(op='fundamental',name='roe'),Expr(op='constant',value=10)])])
    assert not Rules(missing,{}).signals(fund).any()


def test_missing_benchmark_session_does_not_skip_stock_day(prices):
    spec=template();spec.symbols=['TEST'];spec.start=prices.index[0].date();spec.end=prices.index[-1].date();spec.price_basis_confirmed=True
    with pytest.raises(ValueError,match='Nifty 50 is missing'):
        run_backtest(spec,{'TEST':prices},prices[['close']].drop(prices.index[50]))


def test_daily_feed_upsert_and_historical_precedence(client):
    from app import data,feed
    row={'date':'2020-01-02','symbol':'TEST','open':100,'high':101,'low':99,'close':100,'volume':1000}
    feed.ingest({'prices':[row],'benchmark':[{'date':row['date'],'close':12000}]})
    changed={**row,'high':103,'close':102}
    feed.ingest({'prices':[changed]})
    frames,benchmark,_=data.load_dataset()
    assert len(frames['TEST'])==1 and frames['TEST'].close.iloc[0]==102
    pd.DataFrame([row]).to_csv(data.DATA/'prices'/'history.csv',index=False)
    frames,_,_=data.load_dataset()
    assert frames['TEST'].close.iloc[0]==100
    assert benchmark.close.iloc[0]==12000


def test_daily_feed_rejects_invalid_and_excludes_unfinished_bars(client):
    from app import data,feed
    now=datetime(2020,1,3,15,tzinfo=ZoneInfo('Asia/Kolkata'))
    rows=[{'date':day,'close':100} for day in ['2020-01-02','2020-01-03','2020-01-06']]
    feed.ingest({'benchmark':rows},now)
    _,b,_=data.load_dataset()
    assert list(b.index.strftime('%Y-%m-%d'))==['2020-01-02']
    with pytest.raises(ValueError):feed.ingest({'benchmark':[{'date':'2020-01-01','close':-1}]})


def test_provider_failure_never_leaks_feed_key(client,monkeypatch):
    from app import feed
    monkeypatch.setenv('DAILY_FEED_URL','https://example.com/feed?key=private-test-value')
    def fail(*args,**kwargs):raise RuntimeError('private-test-value')
    monkeypatch.setattr(feed.httpx,'stream',fail)
    result=feed.refresh(force=True)
    assert result['error'] and 'private-test-value' not in json.dumps(result)


def test_ai_repairs_schema_without_executing_generated_text(monkeypatch):
    from app import assistant
    monkeypatch.setenv('LLM_BASE_URL','https://example.com/v1');monkeypatch.setenv('LLM_MODEL','test-model')
    responses=['{"status":"ready","summary":"invalid","strategy":{"entry":{"op":"eval"}}}',json.dumps({'status':'ready','summary':'SMA crossover','strategy':template().model_dump(mode='json')})]
    class Reply:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':responses.pop(0)}}]}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):return Reply()
    monkeypatch.setattr(assistant.httpx,'Client',Client)
    out=assistant.interpret('20 50 SMA crossover',[],{'price_basis_confirmed':False})
    assert out['status']=='ready' and out['strategy']['entry']['op']=='cross_above'
    assert out['strategy']['price_basis_confirmed'] is False and not responses


def test_signal_event_uniqueness_includes_action(client):
    from app import store
    from .conftest import register
    _,user=register(client)
    uid=user['user']['id']
    with store.db() as conn:
        conn.execute('INSERT INTO watches VALUES(?,?,?,?,?,?,?)',('watch',uid,'{}',1,'2020-01-01',0,None))
        for i,action in enumerate(['ENTRY','STOP_OBSERVED','ENTRY']):
            conn.execute('INSERT OR IGNORE INTO alerts VALUES(?,?,?,?,?,?,?,?)',(str(i),uid,'watch','2020-01-02','TEST',action,'{}',0))
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]==2
