"""Inspect tracked source paths and staged bytes; never read private runtime data."""
import re
import subprocess
import sys
from pathlib import Path
from privacy_rules import private_path, content_findings

root = Path(__file__).resolve().parents[1]
result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True)
files = [x for x in result.stdout.decode().split('\0') if x]
if not files:
    raise SystemExit('No tracked files. Stage reviewed source before running the release check.')
bad = []
for rel in files:
    if private_path(rel):
        bad.append(rel + ' (private runtime path)')
        continue
    staged = subprocess.check_output(['git', 'show', ':' + rel], cwd=root)
    path = root / rel
    blobs = [staged] + ([path.read_bytes()] if path.is_file() else [])
    for rule in sorted({r for blob in blobs for r in content_findings(blob)}):
        bad.append(rel + ' (' + rule + ')')
    if any(re.search(rb'C:[/\\]Users[/\\][^/\\\s]+[/\\](?:PawSec|\.codex)', blob, re.I) for blob in blobs):
        bad.append(rel + ' (developer path)')
if bad:
    print('\n'.join(bad)); sys.exit(1)
print(f'Release check passed: {len(files)} tracked files; no blocked paths or credential patterns.')
