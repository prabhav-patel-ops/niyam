from __future__ import annotations

from datetime import date,datetime
from zoneinfo import ZoneInfo

def india_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Expr(Strict):
    op: Literal['open','high','low','close','volume','fundamental','constant','parameter',
                'sma','ema','rsi','atr','highest','lowest','roc','std','lag',
                'add','sub','mul','div','gt','gte','lt','lte','eq',
                'cross_above','cross_below','all','any','not']
    args: list[Expr] = Field(default_factory=list, max_length=12)
    window: int | str | None = None
    value: float | None = None
    name: str | None = None

    @model_validator(mode='after')
    def check(self):
        zero = {'open','high','low','close','volume','fundamental','constant','parameter','atr'}
        unary = {'sma','ema','rsi','highest','lowest','roc','std','lag','not'}
        if self.op in zero and self.args:
            raise ValueError(f'{self.op} does not take arguments.')
        if self.op in unary and len(self.args) != 1:
            raise ValueError(f'{self.op} needs exactly one argument.')
        if self.op not in zero | unary | {'all','any'} and len(self.args) != 2:
            raise ValueError(f'{self.op} needs two arguments.')
        if self.op in {'all','any'} and not self.args:
            raise ValueError('A condition group cannot be empty.')
        if self.op in {'sma','ema','rsi','atr','highest','lowest','roc','std','lag'}:
            if self.window is None or isinstance(self.window,int) and not 1 <= self.window <= 1000:
                raise ValueError('Indicator window must be between 1 and 1000 bars.')
        elif self.window is not None:
            raise ValueError('This expression does not use a window.')
        if self.op == 'constant' and self.value is None:
            raise ValueError('A constant needs a number.')
        if self.op in {'parameter','fundamental'} and not self.name:
            raise ValueError('A named value needs a name.')
        if self.op == 'fundamental' and self.name not in {'roe','roce','pe','pb','ps'}:
            raise ValueError('Supported fundamental fields: roe, roce, pe, pb, ps.')
        return self


class Stop(Strict):
    kind: Literal['none','percent','trailing_percent','atr','trailing_atr'] = 'percent'
    value: float = Field(default=5, gt=0, le=100)
    atr_period: int = Field(default=14, ge=2, le=500)


class Costs(Strict):
    fee_bps: float = Field(default=10, ge=0, le=1000)
    slippage_bps: float = Field(default=5, ge=0, le=1000)


class Strategy(Strict):
    name: str = Field(default='My strategy', min_length=1, max_length=100)
    symbols: list[str] = Field(default_factory=list, max_length=100)
    entry: Expr
    exit: Expr
    parameters: dict[str, float] = Field(default_factory=dict, max_length=12)
    stop: Stop = Field(default_factory=Stop)
    take_profit_pct: float | None = Field(default=None, gt=0, le=1000)
    capital: float = Field(default=100000, ge=1000, le=1e10)
    allocation_pct: float = Field(default=95, gt=0, le=100)
    costs: Costs = Field(default_factory=Costs)
    start: date = date(2014,1,1)
    end: date = Field(default_factory=india_today)
    notes: list[str] = Field(default_factory=list, max_length=20)
    price_basis_confirmed: bool = False

    @model_validator(mode='after')
    def validate_strategy(self):
        if self.start >= self.end:
            raise ValueError('The end date must be after the start date.')
        if self.end > india_today():
            raise ValueError('Choose an end date no later than today.')
        self.symbols = list(dict.fromkeys(s.strip().upper() for s in self.symbols))
        if any(not re.fullmatch(r'[A-Z0-9&_.-]{1,30}',s) for s in self.symbols):
            raise ValueError('Use exchange ticker symbols, such as INFY or M&M.')
        count = 0
        def walk(x, depth=0):
            nonlocal count
            count += 1
            if count > 100 or depth > 12:
                raise ValueError('Please split this strategy into smaller rule groups.')
            if x.op == 'parameter' and x.name not in self.parameters:
                raise ValueError(f'Missing parameter: {x.name}.')
            if isinstance(x.window,str):
                value = self.parameters.get(x.window)
                if value is None or int(value) != value or not 1 <= value <= 1000:
                    raise ValueError(f'Window parameter {x.window} must be an integer from 1 to 1000.')
            for y in x.args:
                walk(y,depth+1)
        walk(self.entry)
        walk(self.exit)
        return self


class RunRequest(Strict):
    strategy: Strategy
    mode: Literal['backtest','optimise'] = 'backtest'
    search_space: dict[str, list[float]] = Field(default_factory=dict, max_length=4)
    objective: Literal['sharpe','return','calmar'] = 'calmar'
    train_pct: int = Field(default=70, ge=50, le=85)
    max_trials: int = Field(default=40, ge=1, le=100)
    min_trades: int = Field(default=3, ge=0, le=1000)


def template(kind='trend') -> Strategy:
    close = {'op':'close'}
    c = lambda x: {'op':'constant','value':x}
    if kind == 'rsi':
        ind = {'op':'rsi','window':'period','args':[close]}
        entry = {'op':'lt','args':[ind,c(30)]}
        exit_rule = {'op':'gt','args':[ind,c(60)]}
        params = {'period':14}
        name = 'RSI mean reversion'
    elif kind == 'breakout':
        top = {'op':'lag','window':1,'args':[{'op':'highest','window':'lookback','args':[{'op':'high'}]}]}
        bottom = {'op':'lag','window':1,'args':[{'op':'lowest','window':'exit_window','args':[{'op':'low'}]}]}
        entry = {'op':'gt','args':[close,top]}
        exit_rule = {'op':'lt','args':[close,bottom]}
        params = {'lookback':55,'exit_window':20}
        name = 'Donchian breakout'
    else:
        fast = {'op':'sma','window':'fast','args':[close]}
        slow = {'op':'sma','window':'slow','args':[close]}
        entry = {'op':'cross_above','args':[fast,slow]}
        exit_rule = {'op':'cross_below','args':[fast,slow]}
        params = {'fast':20,'slow':50}
        name = 'Moving average crossover'
    return Strategy(name=name,entry=entry,exit=exit_rule,parameters=params)
