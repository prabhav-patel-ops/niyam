import numpy as np
import pandas as pd
import pytest
from app.engine import simulate,run_backtest,metrics
from app.models import template,Expr,Strategy
from app.rules import Rules


def kernel(o,h,l,c,entries,exits=None,kind=0,value=5,target=0,fee=0,slip=0,final=True):
    n=len(c)
    return simulate(*[np.asarray(x,dtype=float) for x in [o,h,l,c]],np.asarray(entries,dtype=bool),
                    np.asarray(exits if exits is not None else [False]*n,dtype=bool),np.full(n,1.0),
                    1000.,1.,fee,slip,kind,float(value),float(target),final)


def test_next_open_execution():
    r=kernel([100,110,130,130],[101,111,131,131],[99,109,129,129],[100,110,130,130],
             [True,False,False,False],[False,True,False,False])
    t=r[2][0]
    assert t[0]==1 and t[1]==2 and t[3]==110 and t[4]==130
    assert t[2]==9 and t[5]==180
    assert r[0][-1]==1180


def test_stop_gap_fills_at_open():
    r=kernel([100,100,90,95],[101,101,95,96],[99,99,88,94],[100,100,92,95],[True,False,False,False],kind=1,value=5)
    assert r[2][0][4]==90
    assert r[0][-1]==900


def test_same_bar_stop_and_target_is_conservative():
    r=kernel([100,100,100],[101,110,101],[99,90,99],[100,100,100],[True,False,False],kind=1,value=5,target=5)
    assert r[2][0][4]==95
    assert r[3]==1


def test_opening_target_gap_precedes_later_stop():
    r=kernel([100,100,110],[101,101,112],[99,99,80],[100,100,90],[True,False,False],kind=1,value=5,target=5)
    assert r[2][0][4]==110


def test_trailing_stop_cannot_use_same_bars_high_retroactively():
    r=kernel([100,100,115,110],[101,120,130,115],[99,98,109,105],[100,115,125,111],[True,False,False,False],kind=2,value=10)
    assert r[2][0][1]==3 and r[2][0][4]==110


def test_fees_and_slippage_both_sides():
    r=kernel([100]*3,[102]*3,[98]*3,[100]*3,[True,False,False],fee=.01,slip=.005)
    t=r[2][0]
    q=int(1000//(100.5*1.01))
    assert t[2]==q
    assert t[6]==pytest.approx(q*(100.5+99.5)*.01)
    assert t[5]==pytest.approx(q*(99.5-100.5)-t[6])
    assert r[0][-1]==pytest.approx(1000+t[5])


def test_last_close_signal_never_invents_next_open():
    r=kernel([100]*3,[101]*3,[99]*3,[100]*3,[False,False,True])
    assert len(r[2])==0 and r[0][-1]==1000


def test_no_trade_metrics_are_defined_without_invented_win_rate():
    m=metrics([100,100,100],pd.bdate_range('2020-01-01',periods=3),[],[0,0,0])
    assert m['return_pct']==0 and m['max_drawdown_pct']==0
    assert m['sharpe'] is None and m['win_rate_pct'] is None and m['profit_factor'] is None


def test_full_report_benchmark_alignment_and_equity(prices):
    s=template();s.symbols=['TEST'];s.start=prices.index[0].date();s.end=prices.index[-1].date();s.price_basis_confirmed=True
    b=prices[['close']].copy()
    r=run_backtest(s,{'TEST':prices},b)
    assert r['curve'][0]['strategy']==s.capital
    assert r['curve'][0]['benchmark']==s.capital
    assert r['metrics']['ending_value']==pytest.approx(s.capital+sum(t['pnl'] for t in r['trades']))
    assert r['sessions']==len(prices)
    assert all(t['entry_date']<=t['exit_date'] for t in r['trades'])


def test_missing_stock_sessions_fail_clearly(prices):
    s=template();s.symbols=['TEST'];s.start=prices.index[0].date();s.end=prices.index[-1].date();s.price_basis_confirmed=True
    with pytest.raises(ValueError,match='missing 1 benchmark sessions'):
        run_backtest(s,{'TEST':prices.drop(prices.index[50])},prices[['close']])


def test_future_prices_do_not_change_past_equity(prices):
    s=template();s.symbols=['TEST'];s.start=prices.index[0].date();s.end=prices.index[-1].date();s.price_basis_confirmed=True
    first=run_backtest(s,{'TEST':prices},prices[['close']],finalise=False)
    changed=prices.copy()
    changed.loc[changed.index[150:],['open','high','low','close']]*=3
    second=run_backtest(s,{'TEST':changed},prices[['close']],finalise=False)
    assert first['curve'][:150]==second['curve'][:150]


def test_rsi_flat_series_is_fifty():
    df=pd.DataFrame({'close':[100.]*30})
    result=Rules(df,{}).evaluate(Expr(op='rsi',window=14,args=[Expr(op='close')]))
    assert np.isnan(result[:14]).all()
    assert (result[14:]==50).all()


def test_rule_schema_blocks_code_and_unbounded_windows():
    with pytest.raises(ValueError): Expr(op='eval',name='open(secret)')
    with pytest.raises(ValueError): Expr(op='sma',window=-1,args=[Expr(op='close')])
    with pytest.raises(ValueError): Strategy.model_validate({**template().model_dump(),'parameters':{'fast':0,'slow':50}})


def test_sma_signals_match_independent_backtesting_library(prices):
    from backtesting import Backtest,Strategy as OracleStrategy
    s=template();s.symbols=['TEST'];s.start=prices.index[0].date();s.end=prices.index[-1].date();s.price_basis_confirmed=True
    s.stop.kind='none';s.costs.fee_bps=0;s.costs.slippage_bps=0;s.allocation_pct=95
    rules=Rules(prices,s.parameters)
    entries=rules.signals(s.entry);exits=rules.signals(s.exit)
    # A forced exit before the last bar avoids different end-of-test conventions.
    entries[-3:]=False;exits[-3:]=True
    class Oracle(OracleStrategy):
        def init(self):
            self.entry_signals=self.I(lambda:entries)
            self.exit_signals=self.I(lambda:exits)
        def next(self):
            if self.position and self.exit_signals[-1]:self.position.close()
            elif not self.position and self.entry_signals[-1] and not self.exit_signals[-1]:self.buy(size=.95)
    oracle=Backtest(prices.rename(columns=str.title),Oracle,cash=100000,commission=0,exclusive_orders=True).run()
    arrays=[np.ascontiguousarray(prices[k].to_numpy(float)) for k in ['open','high','low','close']]
    ours=simulate(*arrays,entries,exits,np.ones(len(prices)),100000.,.95,0.,0.,0,5.,0.,False)
    assert ours[0][-1]==pytest.approx(oracle['Equity Final [$]'])
    assert len(ours[2])==oracle['# Trades']
