"""Local dependency checks and safe Linux process control. Never reads credentials."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_lock import DataLock, data_dir, process_identity


def doctor():
    ok = sys.version_info >= (3, 12)
    print('Python >= 3.12:', 'OK' if ok else 'MISSING')
    for module in ('flask', 'cryptography', 'pymupdf', 'requests', 'reportlab', 'waitress'):
        found = importlib.util.find_spec(module) is not None
        print(module + ':', 'OK' if found else 'MISSING')
        ok = ok and found
    print('Data directory:', data_dir())
    print('Local URL: http://127.0.0.1:8765')
    print('Time zone:', time.tzname)
    print('Node.js / PPTX export:', 'available' if shutil.which('node') and (ROOT / 'node_modules/pptxgenjs').exists() else 'optional; run bash scripts/setup.sh --pptx')
    fonts = shutil.which('fc-match')
    if fonts:
        subprocess.run([fonts, 'Noto Sans CJK SC', '--format=%{family}\n'], check=False)
    else:
        print('CJK fonts: install fonts-noto-cjk on Ubuntu for Chinese report rendering.')
    return ok


def stop():
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Use Ctrl+C in the start terminal on non-Linux systems.')
    folder = data_dir()
    if not folder.exists():
        print('PawSec is not running for this library.'); return
    try:
        with DataLock(folder):
            print('PawSec is not running for this library.'); return
    except RuntimeError:
        pass
    state = json.loads((folder / '.pawsec.lock').read_text())
    pid, identity = state['pid'], state.get('identity')
    cmd = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    if state.get('purpose') != 'server' or not identity or identity != process_identity(pid) or str(ROOT / 'server.py').encode() not in cmd:
        raise RuntimeError('Lock belongs to another process; no signal was sent. Stop its own terminal.')
    fd = os.pidfd_open(pid)
    try:
        if process_identity(pid) != identity:
            raise RuntimeError('Process identity changed; no signal was sent.')
        signal.pidfd_send_signal(fd, signal.SIGINT)
        for _ in range(300):
            try:
                with DataLock(folder):
                    print('PawSec stopped.'); return
            except RuntimeError:
                time.sleep(0.1)
        raise RuntimeError('Still stopping; no forced termination was used.')
    finally:
        os.close(fd)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('doctor', 'start', 'stop', 'idle'))
    a = p.parse_args()
    try:
        if a.command == 'doctor':
            return 0 if doctor() else 1
        if a.command == 'stop':
            stop(); return 0
        if a.command == 'idle':
            if data_dir().exists():
                with DataLock(data_dir()):
                    pass
            return 0
        if not doctor():
            raise RuntimeError('Dependencies missing. Run bash scripts/setup.sh first.')
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', 8765))
            except OSError:
                raise RuntimeError('Port 8765 is occupied. No existing process was stopped.') from None
        os.environ['PAWSEC_MODE'] = 'local'
        os.environ['PAWSEC_BIND'] = '127.0.0.1'
        os.environ['PORT'] = '8765'
        os.environ['PYTHONUNBUFFERED'] = '1'
        os.umask(0o077)
        os.execv(sys.executable, [sys.executable, str(ROOT / 'server.py')])
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        p.exit(1, f'Local operation stopped: {e}\n')


if __name__ == '__main__':
    sys.exit(main())
