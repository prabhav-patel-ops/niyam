"""Import the supplied CSV/XLSX collection into a private backend warehouse."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.private_import import import_collection

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',required=True)
    parser.add_argument('--data-dir',default='data')
    parser.add_argument('--adjustment-basis',choices=['split_bonus_adjusted_ex_dividend','unverified'],default='unverified')
    args=parser.parse_args()
    path,manifest=import_collection(args.source_dir,args.data_dir,args.adjustment_basis)
    print('Private collection: '+str(path),flush=True)
    print('All source files archived; period fundamentals are staged without publication dates.',flush=True)
