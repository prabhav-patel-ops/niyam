"""Publish a completed private market-data import to the backtesting engine."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.install_market_data import install

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',default='data');args=parser.parse_args()
    report=install(args.data_dir)
    print(json.dumps({k:v for k,v in report.items() if k not in {'failed_symbols','calendar_gaps','extra_stock_sessions'}},indent=2),flush=True)
