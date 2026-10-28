import itertools
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor,wait
import pandas as pd
from . import store
from .data import load_dataset
from .engine import run_backtest
from .models import RunRequest,Strategy,completed_through

POOL=ThreadPoolExecutor(max_workers=2,thread_name_prefix='niyam-research')
SUBMIT_LOCK=threading.Lock()
FUTURES=set()
FUTURES_LOCK=threading.Lock()


def enqueue(job_id):
    future=POOL.submit(execute,job_id)
    with FUTURES_LOCK:
        FUTURES.add(future)
    def completed(f):
        with FUTURES_LOCK:
            FUTURES.discard(f)
    future.add_done_callback(completed)


def drain():
    with FUTURES_LOCK:
        pending=list(FUTURES)
    # Keep the instance lock until active jobs stop using this database.
    if pending:
        with store.db() as c:
            c.execute("UPDATE jobs SET cancel=1 WHERE state IN ('queued','running')")
        wait(pending)


class Cancelled(Exception): pass


def set_progress(job_id,value):
    with store.db() as c:
        row=c.execute('SELECT cancel,created FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row['cancel']:
            raise Cancelled()
        if time.time()-row['created']>900:
            raise ValueError('This job reached the 15-minute limit. Reduce the universe or trial count.')
        c.execute("UPDATE jobs SET state='running',progress=? WHERE id=?",(min(0.99,value),job_id))


def execute(job_id):
    try:
        with store.db() as c:
            row=c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        request=RunRequest.model_validate_json(row['request'])
        try:
            frames,benchmark,version=load_dataset()
        except Exception:
            raise ValueError('Market research is temporarily unavailable. Please try again shortly.') from None
        if benchmark.empty:
            raise ValueError('Add daily Nifty 50 price-index data in data/benchmark/ before running a comparison.')
        set_progress(job_id,0.02)
        if request.mode=='backtest':
            result=run_backtest(request.strategy,frames,benchmark,progress=lambda p:set_progress(job_id,0.05+0.9*p))
        else:
            result=optimise(request,frames,benchmark,lambda p:set_progress(job_id,p))
        result.update(strategy=request.strategy.model_dump(mode='json'),data_version=version,engine_version='1.1.0',mode=request.mode)
        with store.db() as c:
            cancelled=c.execute('SELECT cancel FROM jobs WHERE id=?',(job_id,)).fetchone()[0]
            c.execute('UPDATE jobs SET state=?,progress=1,result=? WHERE id=?',('cancelled' if cancelled else 'completed',None if cancelled else store.dump(result),job_id))
    except Cancelled:
        with store.db() as c:
            c.execute("UPDATE jobs SET state='cancelled',error='Cancelled at the next safe checkpoint.' WHERE id=?",(job_id,))
    except Exception as error:
        with store.db() as c:
            # Validation/domain failures are actionable. Unexpected internals stay out of the UI.
            message=str(error) if isinstance(error,ValueError) else 'This test could not finish. Please try again shortly.'
            c.execute("UPDATE jobs SET state='failed',error=? WHERE id=?",(message,job_id))
        if not isinstance(error,ValueError):
            import traceback
            traceback.print_exc()


def optimise(request,frames,benchmark,progress):
    strategy=request.strategy
    space=request.search_space
    if not space or any(k not in strategy.parameters for k in space):
        raise ValueError('Choose one or more existing strategy parameters to optimise.')
    if any(not v or len(v)>20 for v in space.values()):
        raise ValueError('Each parameter needs between 1 and 20 candidate values.')
    dates=benchmark.loc[str(strategy.start):str(min(strategy.end,completed_through()))].index
    if len(dates)<60:
        raise ValueError('Optimisation needs at least 60 daily sessions, with separate training and validation periods.')
    split=int(len(dates)*request.train_pct/100)
    cutoff=dates[split-1].date();test_start=dates[split].date()
    names=list(space)
    sizes=[len(space[k]) for k in names]
    total=1
    for n in sizes: total*=n
    rng=random.Random(42)
    indices=list(range(total)) if total<=request.max_trials else sorted(rng.sample(range(total),request.max_trials))
    candidates=[]
    for index in indices:
        params=dict(strategy.parameters)
        for name,size in reversed(list(zip(names,sizes))):
            params[name]=space[name][index%size];index//=size
        # Only enforce this convention for the named MA fast/slow pair.
        if 'fast' in params and 'slow' in params and params['fast']>=params['slow']:
            continue
        try:
            candidate=Strategy.model_validate({**strategy.model_dump(mode='json'),'parameters':params,'end':str(cutoff)})
        except ValueError:
            continue
        candidates.append(candidate)
    if not candidates:
        raise ValueError('No valid parameter combinations remain. Check the ranges and fast/slow windows.')
    leaderboard=[]
    winner=None;best=float('-inf')
    for i,candidate in enumerate(candidates):
        progress(0.05+0.8*i/len(candidates))
        output=run_backtest(candidate,frames,benchmark,details=False)
        m=output['metrics']
        score=(m['sharpe'] if request.objective=='sharpe' else m['return_pct'] if request.objective=='return' else
               m['cagr_pct']/m['max_drawdown_pct'] if m['max_drawdown_pct']>1e-9 else None)
        eligible=m['trades']>=request.min_trades and score is not None
        leaderboard.append({'parameters':candidate.parameters,'score':score,'eligible':eligible,'metrics':m})
        if eligible and score>best:
            best=score;winner=candidate
    if winner is None:
        raise ValueError('No training candidate met the minimum trade count with a defined objective. Adjust the objective, dates or trade threshold.')
    # The holdout is evaluated only after selecting the winner using training data.
    training=run_backtest(winner,frames,benchmark)
    validation_strategy=Strategy.model_validate({**strategy.model_dump(mode='json'),'parameters':winner.parameters,'start':str(test_start)})
    validation=run_backtest(validation_strategy,frames,benchmark)
    progress(0.97)
    leaderboard.sort(key=lambda x:(x['eligible'],x['score'] if x['score'] is not None else float('-inf')),reverse=True)
    return {'training':training,'validation':validation,'best_parameters':winner.parameters,'selected_strategy':validation_strategy.model_dump(mode='json'),'leaderboard':leaderboard,
            'trials':len(candidates),'total_combinations':total,'training_end':str(cutoff),'validation_start':str(test_start),
            'objective':request.objective,'seed':42,'note':'Selection used training data only. Validation starts in cash with historical indicator warm-up. Repeatedly trying ideas against the same holdout reduces its independence.'}
