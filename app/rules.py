"""A closed expression language. No eval, exec, user SQL, or generated Python."""
import json
import numpy as np
import pandas as pd
from .models import Expr


def wilder(values, period):
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if len(valid) < period:
        return result
    start = valid[0]
    end = start + period - 1
    if end >= len(values):
        return result
    result[end] = np.mean(values[start:end+1])
    for i in range(end+1,len(values)):
        result[i] = (result[i-1]*(period-1)+values[i])/period
    return result


class Rules:
    def __init__(self, frame, parameters):
        self.frame = frame
        self.parameters = parameters
        self.cache = {}

    def evaluate(self, expr: Expr):
        key = json.dumps(expr.model_dump(exclude_none=True),sort_keys=True)
        if key in self.cache:
            return self.cache[key]
        op = expr.op
        args = [self.evaluate(x) for x in expr.args]
        n = len(self.frame)
        window = int(self.parameters[expr.window]) if isinstance(expr.window,str) else expr.window
        if op in {'open','high','low','close','volume'}:
            if op not in self.frame:
                raise ValueError(f'This strategy requires {op} data.')
            out = self.frame[op].to_numpy(dtype=float)
        elif op == 'fundamental':
            if expr.name not in self.frame:
                raise ValueError(f'Add point-in-time {expr.name.upper()} data before running this rule.')
            out = self.frame[expr.name].to_numpy(dtype=float)
        elif op == 'constant':
            out = np.full(n,expr.value)
        elif op == 'parameter':
            out = np.full(n,self.parameters[expr.name])
        elif op in {'sma','highest','lowest','std'}:
            roll = pd.Series(args[0]).rolling(window,min_periods=window)
            out = {'sma':roll.mean,'highest':roll.max,'lowest':roll.min,'std':lambda:roll.std(ddof=0)}[op]().to_numpy()
        elif op == 'ema':
            out = pd.Series(args[0]).ewm(span=window,adjust=False,min_periods=window).mean().to_numpy()
        elif op == 'lag':
            out = pd.Series(args[0]).shift(window).to_numpy()
        elif op == 'roc':
            out = (pd.Series(args[0])/pd.Series(args[0]).shift(window)-1).to_numpy()*100
        elif op == 'rsi':
            diff = np.r_[np.nan,np.diff(args[0])]
            gain = wilder(np.maximum(diff,0),window)
            loss = wilder(np.maximum(-diff,0),window)
            with np.errstate(divide='ignore',invalid='ignore'):
                out = 100-100/(1+gain/loss)
            out[(loss==0)&(gain>0)] = 100
            out[(loss==0)&(gain==0)] = 50
        elif op == 'atr':
            high,low,close = [self.frame[x].to_numpy(dtype=float) for x in ['high','low','close']]
            prev = np.r_[close[0],close[:-1]]
            out = wilder(np.maximum(high-low,np.maximum(np.abs(high-prev),np.abs(low-prev))),window)
        elif op in {'add','sub','mul','div'}:
            with np.errstate(divide='ignore',invalid='ignore'):
                out = {'add':np.add,'sub':np.subtract,'mul':np.multiply,'div':np.divide}[op](*args)
            out[~np.isfinite(out)] = np.nan
        elif op in {'gt','gte','lt','lte','eq'}:
            valid = np.isfinite(args[0]) & np.isfinite(args[1])
            out = np.where(valid, {'gt':np.greater,'gte':np.greater_equal,'lt':np.less,'lte':np.less_equal,'eq':np.equal}[op](*args), np.nan)
        elif op in {'cross_above','cross_below'}:
            a,b=args
            valid=np.isfinite(a)&np.isfinite(b)
            out=np.full(n,np.nan)
            if op=='cross_above':
                out[1:]=np.where(valid[1:]&valid[:-1],(a[1:]>b[1:])&(a[:-1]<=b[:-1]),np.nan)
            else:
                out[1:]=np.where(valid[1:]&valid[:-1],(a[1:]<b[1:])&(a[:-1]>=b[:-1]),np.nan)
        elif op in {'all','any'}:
            values=np.asarray(args)
            known=np.isfinite(values)
            if op=='all':
                out=np.where(np.any(known&(values==0),axis=0),0,np.where(np.all(known,axis=0),1,np.nan))
            else:
                out=np.where(np.any(known&(values!=0),axis=0),1,np.where(np.all(known,axis=0),0,np.nan))
        elif op == 'not':
            out=np.where(np.isfinite(args[0]),~args[0].astype(bool),np.nan)
        self.cache[key]=out
        return out

    def signals(self, expr):
        values=self.evaluate(expr)
        return np.ascontiguousarray(np.isfinite(values)&values.astype(bool))


def describe(expr):
    if expr.op in {'open','high','low','close','volume'}:
        return expr.op.title()
    if expr.op == 'constant':
        return f'{expr.value:g}'
    if expr.op in {'fundamental','parameter'}:
        return expr.name.upper()
    args=[describe(x) for x in expr.args]
    if expr.window is not None:
        return f'{expr.op.upper()}({", ".join(args+[str(expr.window)])})'
    names={'gt':'>','gte':'≥','lt':'<','lte':'≤','eq':'=','cross_above':'crosses above','cross_below':'crosses below','add':'+','sub':'−','mul':'×','div':'÷','all':'AND','any':'OR'}
    return 'NOT '+args[0] if expr.op=='not' else '('+f' {names[expr.op]} '.join(args)+')'
