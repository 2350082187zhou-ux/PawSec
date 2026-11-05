"""Backup round trips and refusal cases use synthetic data only."""
import io
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from data_lock import DataLock
from server import bind_address
from tools.local_data import backup, restore, verify
from tools.privacy_rules import private_path, content_findings


class LocalToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / 'library'; self.data.mkdir()
        self.key = Fernet.generate_key()
        (self.data / 'secret.key').write_bytes(self.key)
        (self.data / 'config.enc').write_bytes(Fernet(self.key).encrypt(b'synthetic model configuration'))
        (self.data / 'mail.enc').write_bytes(Fernet(self.key).encrypt(b'synthetic mail configuration'))
        (self.data / 'paper').mkdir()
        (self.data / 'paper/source.pdf').write_bytes(b'%PDF-1.4 synthetic fixture')
        (self.data / 'paper/paper.json').write_text(json.dumps({'notes': 'Synthetic note', 'summary': 'Synthetic summary'}))
        with closing(sqlite3.connect(self.data / 'study_tracker.sqlite3')) as db:
            db.execute('CREATE TABLE activity (seconds INTEGER)')
            db.execute('INSERT INTO activity VALUES (123)')
            db.commit()
        self.archive = self.root / 'backup.tar.gz'

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_round_trip_and_private_permissions(self):
        backup(self.data, self.archive)
        target = self.root / 'restored'
        self.assertEqual(restore(self.archive, target), 6)
        self.assertEqual(verify(self.archive), 6)
        for p in self.data.rglob('*'):
            if p.is_file() and p.name != '.pawsec.lock':
                self.assertEqual(p.read_bytes(), (target / p.relative_to(self.data)).read_bytes())
        key = (target / 'secret.key').read_bytes()
        self.assertEqual(Fernet(key).decrypt((target / 'mail.enc').read_bytes()), b'synthetic mail configuration')
        with closing(sqlite3.connect(target / 'study_tracker.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT seconds FROM activity').fetchone()[0], 123)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        if os.name != 'nt':
            self.assertEqual(self.archive.stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    def test_never_overwrite_original_or_existing_backup(self):
        backup(self.data, self.archive)
        original = (self.data / 'secret.key').read_bytes()
        with self.assertRaises(ValueError): restore(self.archive, self.data)
        with self.assertRaises(FileExistsError): backup(self.data, self.archive)
        self.assertEqual((self.data / 'secret.key').read_bytes(), original)

    def test_lock_refuses_live_backup(self):
        with DataLock(self.data, 'server'):
            with self.assertRaises(RuntimeError): backup(self.data, self.archive)
        self.assertFalse(self.archive.exists())

    def test_missing_key_and_nested_backup_rejected(self):
        with self.assertRaises(ValueError): backup(self.data, self.data / 'bad.tar.gz')
        (self.data / 'secret.key').unlink()
        with self.assertRaises(ValueError): backup(self.data, self.archive)
        self.assertFalse(self.archive.exists())

    def test_malicious_and_corrupt_archives_refused(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('data/link', tarfile.SYMTYPE)]:
            with tarfile.open(self.archive, 'w:gz') as arc:
                member = tarfile.TarInfo(name); member.type = kind; member.linkname = '../escape'
                arc.addfile(member, io.BytesIO())
            with self.assertRaises(ValueError): restore(self.archive, self.root / 'bad')
            self.assertFalse((self.root / 'bad').exists())
        self.archive.unlink()
        backup(self.data, self.archive)
        with tarfile.open(self.archive, 'r:gz') as arc:
            files = [(m, arc.extractfile(m).read()) for m in arc.getmembers()]
        with tarfile.open(self.archive, 'w:gz') as arc:
            for m, body in files:
                if m.name == 'data/secret.key': body = b'X' * len(body)
                arc.addfile(m, io.BytesIO(body))
        with self.assertRaises(ValueError): restore(self.archive, self.root / 'bad')
        self.assertFalse((self.root / 'bad').exists())

    def test_local_bind_ignores_public_environment(self):
        with patch.dict(os.environ, {'PAWSEC_MODE': 'local', 'PAWSEC_BIND': '0.0.0.0', 'PORT': '9999'}):
            self.assertEqual(bind_address(), ('127.0.0.1', 8765))
        with patch.dict(os.environ, {'PAWSEC_MODE': 'public', 'PAWSEC_BIND': '0.0.0.0', 'PORT': '8765'}):
            self.assertEqual(bind_address(), ('0.0.0.0', 8765))

    def test_private_files_policy(self):
        for name in ['.env.local', 'data/paper/paper.json', 'notes/note.md', 'study.db', 'x.sqlite3-wal', 'archive.tar.gz', 'secrets/mail.json', 'papers/source.pdf']:
            self.assertTrue(private_path(name), name)
        for name in ['.env.example', 'README.md', 'app.py', 'tools/local_data.py']:
            self.assertFalse(private_path(name), name)
        self.assertTrue(content_findings(('sk-' + 'x' * 40).encode()))

    def test_missing_key_does_not_replace_old_encryption_key(self):
        (self.data / 'secret.key').unlink()
        before = (self.data / 'config.enc').read_bytes()
        env = dict(os.environ, PAWSEC_DATA_DIR=str(self.data), PAWSEC_MODE='local')
        result = subprocess.run([sys.executable, '-c', 'import app'], cwd=Path(__file__).resolve().parent,
                                env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'secret.key is missing', result.stderr)
        self.assertFalse((self.data / 'secret.key').exists())
        self.assertEqual((self.data / 'config.enc').read_bytes(), before)

    def test_failed_update_keeps_verified_backup_and_data(self):
        from tools import update_local
        original = (self.data / 'secret.key').read_bytes()
        with patch.object(update_local, 'data_dir', return_value=self.data), patch.object(update_local.Path, 'home', return_value=self.root), patch.object(update_local.subprocess, 'check_output', return_value=b''), patch.object(update_local.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['git', 'pull'])):
            with self.assertRaises(subprocess.CalledProcessError):
                update_local.main()
        archives = list((self.root / 'PawSec-backups').glob('*.tar.gz'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(verify(archives[0]), 6)
        self.assertEqual((self.data / 'secret.key').read_bytes(), original)

    def test_gitignore_examples(self):
        root = Path(__file__).resolve().parent
        samples = ['.env.local', 'data/paper/paper.json', 'notes/note.md', 'study.db', 'x.sqlite3-wal', 'archive.tar.gz', 'secrets/mail.json', 'papers/source.pdf']
        result = subprocess.run(['git', 'check-ignore', '-z', '--stdin'], input=('\0'.join(samples) + '\0').encode(), capture_output=True, cwd=root)
        self.assertEqual(set(result.stdout.decode().strip('\0').split('\0')), set(samples))


if __name__ == '__main__':
    unittest.main()
