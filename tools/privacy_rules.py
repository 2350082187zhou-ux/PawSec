"""Shared source-only policy. Findings expose paths and rule names, never values."""
from pathlib import PurePosixPath
import re

BLOCKED_DIRS = {'data', 'secrets', 'backups', 'notes', 'papers', 'uploads', 'exports',
                '.qa', '.venv', 'venv', 'node_modules', 'preview-profile', 'private-backups', '.local'}
SUFFIXES = ('.enc', '.key', '.pem', '.p12', '.pfx', '.pdf', '.pptx', '.db', '.db-wal', '.db-shm',
            '.sqlite', '.sqlite3', '.sqlite-wal', '.sqlite-shm', '.sqlite3-wal', '.sqlite3-shm',
            '.tar', '.tar.gz', '.tgz', '.zip', '.7z', '.bak', '.backup')
PRIVATE_NAMES = {'paper.json', 'config.enc', 'models.enc', 'mail_config.json', 'mail_settings.json',
                 'credentials.json', 'credentials.yaml', 'credentials.yml', '.netrc', '.npmrc',
                 'id_rsa', 'id_ed25519', 'admin-password.hash'}
PATTERNS = {
    'API or GitHub token': re.compile(rb'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})'),
    'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'AWS access key': re.compile(rb'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'Slack token': re.compile(rb'xox[baprs]-[0-9A-Za-z-]{20,}'),
    'credential in URL': re.compile(rb'https?://[^\s/\x22\x27:@]+:[^\s/\x22\x27@]{8,}@'),
}


def private_path(name):
    p = PurePosixPath(name.lower())
    return (any(part in BLOCKED_DIRS or part.startswith('private-backups') for part in p.parts)
            or p.name in PRIVATE_NAMES or p.name.endswith(SUFFIXES)
            or (p.name.startswith('.env') and p.name != '.env.example'))


def content_findings(blob):
    return [label for label, pattern in PATTERNS.items() if pattern.search(blob)]
