"""Build a public preview. Accounts remain on the local backend."""
from pathlib import Path
import argparse
import shutil
parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
out=Path(args.output).resolve()
if out==root or root in out.parents:
    raise SystemExit('Choose an output directory outside the repository.')
if out.exists():
    raise SystemExit('Output directory already exists; choose a new empty path.')
shutil.copytree(root/'web',out)
(out/'deployment.js').write_text('window.NIYAM_PUBLIC_PREVIEW=true;\n')
(out/'.nojekyll').touch()
print(out)
