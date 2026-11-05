"""Fast-forward source updates only; keep a private full library backup first."""
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_lock import DataLock, data_dir
from tools.local_data import backup


def main():
    os.umask(0o077)
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise RuntimeError('Working tree has changes. Preserve them before updating; nothing was reset.')
    folder = data_dir()
    with DataLock(folder, 'update'):
        if any(p.name != '.pawsec.lock' for p in folder.iterdir()):
            output = Path.home() / 'PawSec-backups' / ('before-update-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.tar.gz')
            print('Verified backup:', backup(folder, output, already_locked=True), flush=True)
        subprocess.run(['git', 'pull', '--ff-only'], cwd=ROOT, check=True)
        subprocess.run(['bash', 'scripts/setup.sh'], cwd=ROOT, check=True)
        if (ROOT / 'node_modules/pptxgenjs').exists():
            subprocess.run(['npm', 'ci', '--omit=dev', '--ignore-scripts'], cwd=ROOT, check=True)
        subprocess.run([str(ROOT / '.venv/bin/python'), 'tools/check_release.py'], cwd=ROOT, check=True)
        subprocess.run([str(ROOT / '.venv/bin/python'), 'tools/run_tests.py'], cwd=ROOT, check=True)
    print('Source updated and tests passed. Start with: bash scripts/start.sh')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        sys.exit(f'Update stopped; no library data was removed. Review the error before restarting: {e}')
