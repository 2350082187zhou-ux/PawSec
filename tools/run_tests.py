"""Run each module in an isolated process and temporary application data directory."""
import os,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for test in sorted(root.glob('test_*.py')):
 with tempfile.TemporaryDirectory(prefix='pawsec-tests-') as folder:
  env={k:v for k,v in os.environ.items() if not k.startswith('PAWSEC_')}
  env['PAWSEC_DATA_DIR']=folder;env['PAWSEC_MODE']='local';env['PYTHONUTF8']='1'
  result=subprocess.run([sys.executable,str(test)],cwd=root,env=env)
  if result.returncode:raise SystemExit(result.returncode)
print('All isolated test modules passed.')
