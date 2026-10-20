"""Deterministic daily long-only execution, compiled with Numba.

Close-derived signals execute at the next open. Trailing stops update only
after the current bar has finished. A bar touching both stop and target
uses the stop first. This conservative convention is reported to the user.
"""
import math
import time
import numpy as np
import pandas as pd
from numba import njit
from .models import Expr, Strategy
from .rules import Rules


@njit(cache=True, nogil=True)
def simulate(o,h,l,c,entry,exit_rule,atr,capital,allocation,fee,slip,stop_kind,stop_value,target_pct,finalise):
    n=len(c)
    equity=np.empty(n)
    exposure=np.zeros(n)
    # entry bar, exit bar, quantity, entry price, exit price, pnl, fees, reason
    trades=np.zeros((n,8))
    count=0
    cash=capital
    qty=0
    buy_price=0.0
    buy_fee=0.0
    buy_bar=0
    stop=0.0
    target=0.0
    ambiguous=0
    skipped=0
    for i in range(n):
        sell=0.0
        reason=0
        was_long=qty>0
        if qty>0 and i>0 and exit_rule[i-1]:
            sell=o[i]
            reason=1
        if qty==0 and i>0 and entry[i-1] and not exit_rule[i-1]:
            # ATR is known only after the prior bar closes.
            if (stop_kind==3 or stop_kind==4) and not np.isfinite(atr[i-1]):
                skipped+=1
            else:
                price=o[i]*(1+slip)
                units=int(math.floor(cash*allocation/(price*(1+fee))))
                if units>0:
                    qty=units
                    buy_price=price
                    buy_fee=qty*price*fee
                    cash-=qty*price+buy_fee
                    buy_bar=i
                    if stop_kind==1 or stop_kind==2:
                        stop=price*(1-stop_value/100)
                    elif stop_kind==3 or stop_kind==4:
                        stop=max(0.0,price-stop_value*atr[i-1])
                    else:
                        stop=0.0
                    target=price*(1+target_pct/100) if target_pct>0 else 0.0
                else:
                    skipped+=1
        if qty>0 and sell==0:
            hit_stop=stop>0 and l[i]<=stop
            hit_target=target>0 and h[i]>=target
            if hit_stop and hit_target:
                ambiguous+=1
            # Known opening gaps precede intraday touches.
            if stop>0 and o[i]<=stop:
                sell=o[i]
                reason=2
            elif target>0 and o[i]>=target:
                sell=o[i]
                reason=3
            elif hit_stop:
                sell=stop
                reason=2
            elif hit_target:
                sell=target
                reason=3
        if qty>0 and sell==0 and i==n-1 and finalise:
            sell=c[i]
            reason=4
        exposure[i]=1.0 if qty>0 or was_long else 0.0
        if qty>0 and sell>0:
            sell*=1-slip
            sell_fee=qty*sell*fee
            pnl=qty*(sell-buy_price)-buy_fee-sell_fee
            cash+=qty*sell-sell_fee
            trades[count,0]=buy_bar
            trades[count,1]=i
            trades[count,2]=qty
            trades[count,3]=buy_price
            trades[count,4]=sell
            trades[count,5]=pnl
            trades[count,6]=buy_fee+sell_fee
            trades[count,7]=reason
            count+=1
            qty=0
        if qty>0:
            if stop_kind==2:
                stop=max(stop,h[i]*(1-stop_value/100))
            elif stop_kind==4 and np.isfinite(atr[i]):
                stop=max(stop,h[i]-stop_value*atr[i])
        equity[i]=cash+qty*c[i]
    return equity,exposure,trades[:count],ambiguous,skipped,qty,stop,target


def metrics(equity, dates, trades=None, exposure=None):
    values=np.asarray(equity,dtype=float)
    initial=float(values[0])
    ret=np.diff(values)/values[:-1]
    years=max((pd.Timestamp(dates[-1])-pd.Timestamp(dates[0])).days/365.25,1/365.25)
    total=values[-1]/initial-1
    cagr=(values[-1]/initial)**(1/years)-1 if values[-1]>0 else -1.0
    std=float(np.std(ret,ddof=1)) if len(ret)>1 else 0
    dd=values/np.maximum.accumulate(values)-1
    out={'return_pct':float(total*100),'cagr_pct':float(cagr*100),
         'max_drawdown_pct':float(-np.min(dd)*100),
         'sharpe':float(np.mean(ret)/std*np.sqrt(252)) if std>1e-12 else None,
         'volatility_pct':std*np.sqrt(252)*100,'ending_value':float(values[-1])}
    if trades is not None:
        pnl=[t['pnl'] for t in trades]
        wins=sum(x for x in pnl if x>0)
        losses=-sum(x for x in pnl if x<0)
        out.update(trades=len(pnl),win_rate_pct=100*sum(x>0 for x in pnl)/len(pnl) if pnl else None,
                   profit_factor=wins/losses if losses>0 else None,total_fees=sum(t['fees'] for t in trades),
                   exposure_pct=float(np.mean(exposure)*100) if exposure is not None else 0)
    return out


def run_backtest(strategy:Strategy, frames:dict, benchmark:pd.DataFrame, finalise=True, progress=None, details=True):
    started=time.perf_counter()
    if not strategy.symbols:
        raise ValueError('Choose at least one stock from your imported data.')
    if not strategy.price_basis_confirmed:
        raise ValueError('Confirm that OHLC prices are adjusted for splits and bonuses, but not dividends, in Data assumptions.')
    start,end=pd.Timestamp(strategy.start),pd.Timestamp(strategy.end)
    dates=benchmark.index[(benchmark.index>=start)&(benchmark.index<=end)]
    if len(dates)<3:
        raise ValueError('Add Nifty 50 price-index data covering at least three sessions in this date range.')
    curves=[]; exposures=[]; all_trades=[]; positions=[]
    warnings=[]
    if (dates[0]-start).days>7 or (end-dates[-1]).days>7:
        warnings.append("Requested dates extend beyond benchmark coverage. The report shows the actual tested dates.")
    capital=strategy.capital/len(strategy.symbols)
    kinds={'none':0,'percent':1,'trailing_percent':2,'atr':3,'trailing_atr':4}
    reasons={1:'Exit rule',2:'Stop loss',3:'Take profit',4:'End of test'}
    for j,symbol in enumerate(strategy.symbols):
        if symbol not in frames:
            raise ValueError(f'No price file is available for {symbol}.')
        frame=frames[symbol].loc[:end]
        missing=dates.difference(frame.index)
        if len(missing):
            raise ValueError(f'{symbol} is missing {len(missing)} benchmark sessions, beginning {missing[0].date()}. Fix coverage or narrow the dates.')
        extra=frame.loc[dates[0]:dates[-1]].index.difference(dates)
        if len(extra):
            raise ValueError(f"Nifty 50 is missing {len(extra)} sessions present in {symbol}, beginning {extra[0].date()}. Repair benchmark coverage.")
        rules=Rules(frame,strategy.parameters)
        entry=rules.signals(strategy.entry)
        exits=rules.signals(strategy.exit)
        atr=rules.evaluate(Expr(op='atr',window=strategy.stop.atr_period))
        locations=frame.index.get_indexer(dates)
        arrays=[np.ascontiguousarray(frame[x].to_numpy(float)[locations]) for x in ['open','high','low','close']]
        e,x=entry[locations],exits[locations]
        result=simulate(*arrays,e,x,np.ascontiguousarray(atr[locations]),capital,strategy.allocation_pct/100,
                        strategy.costs.fee_bps/10000,strategy.costs.slippage_bps/10000,
                        kinds[strategy.stop.kind],strategy.stop.value,strategy.take_profit_pct or 0,finalise)
        eq,exp,trades,ambiguous,skipped,qty,stop,target=result
        curves.append(eq);exposures.append(exp)
        if ambiguous:
            warnings.append(f'{symbol}: {ambiguous} daily bars touched both stop and target; the stop was used unless an opening gap established the first fill.')
        if skipped:
            warnings.append(f'{symbol}: {skipped} entries could not be filled because of whole-share sizing or ATR warm-up.')
        if locations[0]<max(50,int(max(strategy.parameters.values(),default=0))):
            warnings.append(f'{symbol}: limited pre-start history; indicators may spend part of this test warming up.')
        for t in trades:
            all_trades.append({'symbol':symbol,'entry_date':str(dates[int(t[0])].date()),'exit_date':str(dates[int(t[1])].date()),
                'quantity':int(t[2]),'entry_price':float(t[3]),'exit_price':float(t[4]),'pnl':float(t[5]),'fees':float(t[6]),'reason':reasons[int(t[7])]})
        action='EXIT' if qty>0 and x[-1] else ('ENTRY' if qty==0 and e[-1] and not x[-1] else 'HOLD')
        positions.append({'symbol':symbol,'model_quantity':int(qty),'next_action':action,
                          'stop':float(stop) if qty else None,'target':float(target) if qty and target else None})
        if progress:
            progress((j+1)/len(strategy.symbols))
    equity=np.sum(curves,axis=0)
    bench=benchmark.loc[dates,'close'].to_numpy(float)
    bench=bench/bench[0]*strategy.capital
    trades=sorted(all_trades,key=lambda t:(t['exit_date'],t['symbol']))
    m=metrics(equity,dates,trades,np.mean(exposures,axis=0))
    bm=metrics(bench,dates)
    m['excess_return_pp']=m['return_pct']-bm['return_pct']
    dd=(equity/np.maximum.accumulate(equity)-1)*100
    curve=[{'date':str(d.date()),'strategy':float(a),'benchmark':float(b),'drawdown':float(v)} for d,a,b,v in zip(dates,equity,bench,dd)] if details else []
    monthly=[]
    prev=equity[0]
    prev_b=bench[0]
    monthly_df=pd.DataFrame({'strategy':equity,'benchmark':bench},index=dates).resample('ME').last() if details else pd.DataFrame()
    for d,row in monthly_df.iterrows():
        monthly.append({'month':d.strftime('%Y-%m'),'strategy':float((row.strategy/prev-1)*100),'benchmark':float((row.benchmark/prev_b-1)*100)})
        prev,prev_b=row.strategy,row.benchmark
    return {'metrics':m,'benchmark_metrics':bm,'curve':curve,'trades':trades,'monthly':monthly,'positions':positions,
            'start':str(dates[0].date()),'end':str(dates[-1].date()),'sessions':len(dates),
            'elapsed_ms':round((time.perf_counter()-started)*1000,2),'warnings':list(dict.fromkeys(warnings)),
            'assumptions':['Daily, long-only cash equities; whole shares; no leverage or short selling.',
              'Close-based rules execute at the next session open. No fill is invented after the last bar.',
              'Equal initial capital sleeves per stock, with no transfers or periodic rebalancing between sleeves.',
              'Trailing stops use the completed bar high and become effective on the following bar.',
              'Fees and adverse slippage apply on both sides. Fees are user assumptions, not a historical Indian tax schedule.',
              'Nifty 50 price index, aligned sessions and initial capital. Dividends are excluded from both sides.',
              'Sharpe assumes a zero risk-free rate and 252 trading sessions per year.',
              'Final positions are liquidated at the final close with costs.' if finalise else 'Open model positions are marked to the final close.',
              'The selected universe may have survivorship bias. Delisted securities and historical membership are not supplied automatically.']}
