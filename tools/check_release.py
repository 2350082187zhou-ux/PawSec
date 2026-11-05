"""Inspect tracked (or staged) source paths without reading private runtime files."""
import re,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
files=[Path(x) for x in result.stdout.decode().split('\0') if x]
if not files:raise SystemExit('No tracked files. Stage the reviewed source before running the release check.')
bad=[]
blocked={'data','secrets','backups','.qa','.venv','node_modules','preview-profile','private-backups'}
for rel in files:
 if any(p in blocked for p in rel.parts) or rel.name=='.env' or rel.suffix.lower() in {'.enc','.key','.pem','.p12','.pdf','.pptx','.sqlite3'}:bad.append(str(rel));continue
 p=root/rel
 if p.suffix not in {'.py','.js','.cjs','.json','.html','.md','.yaml','.yml','.txt'}:continue
 text=p.read_text(encoding='utf-8',errors='replace')
 if re.search(r'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',text):bad.append(str(rel)+' (credential pattern)')
 # A release must not depend on the original developer's home directory.
 if re.search(r'C:[/\\]Users[/\\][^/\\\s]+[/\\](?:PawSec|\.codex)',text,re.I):bad.append(str(rel)+' (developer path)')
if bad:print('\n'.join(bad));raise SystemExit(1)
print(f'Release check passed: {len(files)} tracked files; no blocked runtime paths or credential patterns.')
