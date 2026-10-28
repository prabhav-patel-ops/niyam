"""Operator check before exposing an installed workspace. Never prints secrets."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-model',action='store_true',help='Make one paid-provider test request using only a public template.')
    args=parser.parse_args()
    # Importing main loads the private .env before data paths are resolved.
    from app import main as service,runtime,data
    from app.engine import run_backtest
    from app.models import template,completed_through
    checks={}
    try:
        runtime.validate_config();checks['configuration']=True
        frames,benchmark,version=data.load_dataset()
        if not frames or benchmark.empty or not runtime.price_basis_confirmed():
            raise ValueError('Install price/benchmark files and confirm NIYAM_PRICE_BASIS.')
        # Smoke-test every stock independently; failures identify a bad coverage universe.
        counts=[]
        for symbol,frame in frames.items():
            spec=template()
            start=max(frame.index[0].date(),benchmark.index[0].date())
            end=min(frame.index[-1].date(),benchmark.index[-1].date(),completed_through())
            spec=spec.model_validate({**spec.model_dump(mode='json'),'symbols':[symbol],'start':str(start),'end':str(end),'price_basis_confirmed':True})
            result=run_backtest(spec,{symbol:frame},benchmark)
            counts.append(result['sessions'])
        checks.update(data=True,stocks_checked=len(counts),minimum_sessions=min(counts),data_fingerprint=version)
        if not runtime.public_state()['interpretation_ready']:
            raise ValueError('Install the backend model connection.')
        checks['model_settings']=True
        if args.probe_model:
            from app.assistant import interpret
            defaults=template().model_dump(mode='json')
            defaults.update(symbols=[next(iter(frames))],price_basis_confirmed=True)
            out=interpret('Buy on a 20-day SMA crossover above 50-day SMA; exit on the reverse crossover; fixed 5 percent stop.',[],defaults)
            if out['status']!='ready' or out['strategy']['entry']!=defaults['entry'] or out['strategy']['exit']!=defaults['exit']:
                raise ValueError('The model did not reproduce the public template. Inspect provider compatibility.')
            checks['model_probe']=True
        print(json.dumps({'passed':True,'checks':checks,'note':'Schema, timing and smoke checks do not verify vendor provenance, all languages, profitability, TLS, backups or hosting capacity.'},indent=2))
        return 0
    except Exception:
        # Raw provider, file and network exceptions can contain private information.
        print(json.dumps({'passed':False,'checks':checks,'message':'Preflight failed. Check private operator configuration, data coverage and provider compatibility.'},indent=2))
        return 1

if __name__=='__main__':raise SystemExit(main())
