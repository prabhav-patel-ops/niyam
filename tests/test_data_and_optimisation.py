import numpy as np
import pandas as pd
import pytest
from app.data import validate_prices,join_fundamentals
from app.models import template,RunRequest
from app.jobs import optimise
from app.signals import latest_closed_date
from datetime import datetime
from zoneinfo import ZoneInfo


def test_bad_ohlc_and_duplicates_rejected(prices):
    table=prices.reset_index();table['symbol']='TEST'
    invalid=table.copy();invalid.loc[1,'high']=1
    with pytest.raises(ValueError,match='inconsistent'):validate_prices(invalid)
    with pytest.raises(ValueError,match='Duplicate'):validate_prices(pd.concat([table,table.iloc[:1]]))


def test_dividend_benchmark_rejected():
    with pytest.raises(ValueError,match='PRICE index'):
        validate_prices(pd.DataFrame({'date':['2020-01-01'],'symbol':['NIFTY50TRI'],'close':[100]}),True)


def test_fundamentals_never_available_before_publication(prices):
    f=pd.DataFrame({'symbol':['TEST'],'available_at':['2020-01-03T17:00:00+05:30'],'roe':[22]})
    out=join_fundamentals(prices,f,'TEST')
    assert np.isnan(out.loc['2020-01-03','roe'])
    assert out.loc['2020-01-06','roe']==22


def test_optimizer_holdout_is_not_used_for_selection(prices):
    s=template();s.symbols=['TEST'];s.start=prices.index[0].date();s.end=prices.index[-1].date();s.price_basis_confirmed=True;s.stop.kind='none'
    request=RunRequest(strategy=s,mode='optimise',search_space={'fast':[5,10,20],'slow':[30,50]},min_trades=1)
    original=optimise(request,{'TEST':prices},prices[['close']],lambda _:None)
    changed=prices.copy();cut=int(len(prices)*.7)
    changed.iloc[cut:,changed.columns.get_indexer(['open','high','low','close'])]*=3
    altered=optimise(request,{'TEST':changed},prices[['close']],lambda _:None)
    assert original['best_parameters']==altered['best_parameters']
    assert original['leaderboard']==altered['leaderboard']
    assert original['validation']['metrics']!=altered['validation']['metrics']
    assert original['training_end']<original['validation_start']


def test_today_is_not_a_completed_bar_before_cutoff(prices):
    b=prices[['close']].iloc[:5]
    last=b.index[-1].date()
    now=datetime.combine(last,datetime.min.time()).replace(hour=15,tzinfo=ZoneInfo('Asia/Kolkata'))
    assert latest_closed_date(b,now)==b.index[-2].date()
    assert latest_closed_date(b,now.replace(hour=16))==last
