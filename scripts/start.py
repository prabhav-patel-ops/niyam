"""Cross-platform local launcher. No third-party keys or data are required to start."""
import os
from pathlib import Path
import subprocess
import sys
import venv

root=Path(__file__).resolve().parents[1]
os.chdir(root)
venv_path=root/'.venv'
python=venv_path/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists():
    print('Creating a local Python environment…')
    venv.create(venv_path,with_pip=True)
requirements=root/'requirements.lock'
import hashlib
fingerprint=hashlib.sha256(requirements.read_bytes()).hexdigest()
marker=venv_path/'niyam-requirements.sha256'
if not marker.exists() or marker.read_text()!=fingerprint:
    print('Installing the pinned dependencies…')
    subprocess.run([str(python),'-m','pip','install','-r',str(requirements)],check=True)
    marker.write_text(fingerprint)
for name in ['prices','benchmark','fundamentals']:
    (root/'data'/name).mkdir(parents=True,exist_ok=True)
print('\nNiyam is ready at http://127.0.0.1:8000\nKeep this terminal open. Press Ctrl+C to stop.\n')
subprocess.run([str(python),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],check=True)
