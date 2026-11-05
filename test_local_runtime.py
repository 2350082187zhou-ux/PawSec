"""Real Ubuntu HTTP/start/stop/backup/restore integration, with temporary synthetic data."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import requests
import pymupdf
from tools.local_data import backup, restore

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(sys.platform.startswith('linux'), 'Ubuntu runtime integration')
class RuntimeTests(unittest.TestCase):
    def test_loopback_import_notes_stop_backup_and_restore(self):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', 8765))
            except OSError:
                self.skipTest('Port 8765 is in use; existing service is untouched.')
        with tempfile.TemporaryDirectory(prefix='pawsec-runtime-') as tmp:
            folder = Path(tmp)
            env = {k: v for k, v in os.environ.items() if not k.startswith('PAWSEC_')}
            env.update(PAWSEC_DATA_DIR=str(folder / 'library'), PAWSEC_MODE='local',
                       PAWSEC_BIND='0.0.0.0', PORT='9999')
            session = requests.Session(); session.trust_env = False
            base = 'http://127.0.0.1:8765'
            processes = []
            def launch(entry):
                command = ['bash', *entry] if entry[0].endswith('.sh') else [sys.executable, *entry]
                proc = subprocess.Popen(command, cwd=ROOT, env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(proc)
                for _ in range(150):
                    if proc.poll() is not None:
                        self.fail('Local server exited before readiness.')
                    try:
                        if session.get(base + '/api/site', timeout=0.2).status_code == 200:
                            return proc
                    except requests.RequestException:
                        pass
                    time.sleep(0.1)
                self.fail('Local server did not become ready.')
            def stop(proc):
                result = subprocess.run(['bash', 'scripts/stop.sh'], cwd=ROOT, env=env,
                                        capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                proc.wait(timeout=10)
            try:
                proc = launch(['scripts/start.sh'] if (ROOT / '.venv/bin/python').exists() else ['tools/local.py', 'start'])
                self.assertEqual(session.get(base + '/api/papers').json(), [])
                self.assertEqual(session.get(base + '/api/site').json()['mode'], 'local')
                self.assertFalse(session.get(base + '/api/mail/settings').json()['enabled'])
                self.assertEqual(session.get(base, headers={'Host': 'evil.example'}).status_code, 403)
                # The actual Linux listening socket is loopback, never 0.0.0.0.
                sockets = Path('/proc/net/tcp').read_text().splitlines()[1:]
                listening = [line.split()[1] for line in sockets if line.split()[3] == '0A']
                self.assertIn('0100007F:223D', listening)
                self.assertNotIn('00000000:223D', listening)
                with self.assertRaises(RuntimeError):
                    backup(folder / 'library', folder / 'live.tar.gz')
                with pymupdf.open() as pdf:
                    page = pdf.new_page()
                    page.insert_text((60, 60), 'Synthetic local backup integration paper.')
                    raw = pdf.tobytes()
                response = session.post(base + '/api/papers', files={'file': ('synthetic.pdf', raw, 'application/pdf')})
                self.assertEqual(response.status_code, 200)
                pid = response.json()['id']
                self.assertEqual(session.post(base + f'/api/papers/{pid}/notes', json={'notes': 'Synthetic persistent note'}).status_code, 200)
                self.assertEqual(session.post(base + '/api/config', json={'base': 'https://example.com/v1', 'key': 'synthetic-test-only', 'model': 'test', 'protocol': 'chat'}).status_code, 200)
                stop(proc)
                archive = backup(folder / 'library', folder / 'roundtrip.tar.gz')
                target = folder / 'restored'
                restore(archive, target)
                env['PAWSEC_DATA_DIR'] = str(target)
                proc = launch(['app.py'])
                self.assertEqual(len(session.get(base + '/api/papers').json()), 1)
                self.assertIn('Synthetic persistent note', session.get(base + f'/api/papers/{pid}/export').text)
                self.assertTrue(session.get(base + '/api/config').json()['has_key'])
                self.assertEqual(session.get(base + f'/api/papers/{pid}/pdf').content, raw)
                stop(proc)
            finally:
                session.close()
                for proc in processes:
                    if proc.poll() is None:
                        proc.send_signal(signal.SIGINT)
                        try:
                            proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            proc.kill(); proc.wait()


if __name__ == '__main__':
    unittest.main()
