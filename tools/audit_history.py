"""Read-only scan of all reachable refs and local reflogs. Never rewrites history."""
import subprocess
import sys
from pathlib import Path
from privacy_rules import private_path, content_findings


def audit(root):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)
    commits = git('rev-list', '--all', '--reflog').decode().splitlines()
    blobs = {}
    findings = set()
    for commit in commits:
        for entry in git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
            if not entry:
                continue
            metadata, raw_path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            path = raw_path.decode('utf-8', errors='replace')
            if private_path(path):
                findings.add((commit[:12], path, 'private runtime path'))
            if kind == 'blob':
                blobs.setdefault(oid, set()).add(path)
    for oid, paths in blobs.items():
        blob = git('cat-file', 'blob', oid)
        for rule in content_findings(blob):
            for path in paths:
                findings.add((oid[:12], path, rule))
    print(f'History audit: {len(commits)} commits, {len(blobs)} unique blobs, {len(findings)} findings.')
    for revision, path, rule in sorted(findings):
        print(f'{revision} {path}: {rule}')
    print('Read-only scan; no history changed. Pattern scans cannot prove absence of all secrets.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(audit(Path(__file__).resolve().parents[1]))
