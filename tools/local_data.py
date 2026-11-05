"""Offline checksummed backups. Restore only to a new directory; never overwrite."""
import argparse
from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_lock import DataLock, data_dir


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(folder):
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not supported in library backups.')
        if path.name == '.pawsec.lock':
            continue
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = {'size': path.stat().st_size, 'sha256': digest(path)}
        elif not path.is_dir():
            raise ValueError('Special files are not supported in library backups.')
    return result


def backup(source, output, *, already_locked=False):
    source, output = Path(source).resolve(), Path(output).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('Library does not exist; nothing to back up.')
    if output == source or source in output.parents:
        raise ValueError('Backup must be outside the library.')
    if output.exists():
        raise FileExistsError('Backup already exists; choose a new name.')
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (nullcontext() if already_locked else DataLock(source)):
        entries = inventory(source)
        if not entries:
            raise ValueError('Library is empty; no backup created.')
        if any(n.endswith('.enc') for n in entries) and 'secret.key' not in entries:
            raise ValueError('Encrypted settings exist without secret.key; backup aborted.')
        manifest = {'format': 1, 'created': datetime.now(timezone.utc).isoformat(), 'files': entries}
        # Build and verify privately before publishing a complete archive.
        with tempfile.TemporaryDirectory(prefix='.pawsec-backup-', dir=output.parent) as tmp:
            staged = Path(tmp) / 'backup.tar.gz'
            with tarfile.open(staged, 'w:gz') as archive:
                metadata = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode('utf-8')
                member = tarfile.TarInfo('manifest.json')
                member.size, member.mode = len(metadata), 0o600
                archive.addfile(member, io.BytesIO(metadata))
                for name in entries:
                    archive.add(source / name, arcname='data/' + name, recursive=False)
            staged.chmod(0o600)
            if entries != inventory(source):
                raise ValueError('Library changed. Stop older PawSec processes and retry.')
            verify(staged)
            # Hard-link publication is atomic and refuses existing files.
            os.link(staged, output)
    return output


def unpack(archive_path, destination):
    with tarfile.open(archive_path, 'r:gz') as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries.')
        for m in members:
            p = PurePosixPath(m.name)
            if not m.isfile() or p.is_absolute() or '..' in p.parts or chr(92) in m.name or ':' in m.name:
                raise ValueError('Unsafe archive entry.')
        manifest_member = archive.getmember('manifest.json')
        if manifest_member.size > 32 * 1024 * 1024:
            raise ValueError('Manifest too large.')
        manifest = json.load(archive.extractfile(manifest_member))
        if manifest.get('format') != 1 or not isinstance(manifest.get('files'), dict):
            raise ValueError('Unsupported backup manifest.')
        expected = manifest['files']
        if set(names) != {'manifest.json'} | {'data/' + n for n in expected}:
            raise ValueError('Backup contents do not match manifest.')
        for name, info in expected.items():
            p = PurePosixPath(name)
            if not name or p.is_absolute() or '..' in p.parts or p.as_posix() != name or '.pawsec.lock' in p.parts:
                raise ValueError('Invalid library path.')
            member = archive.getmember('data/' + name)
            if member.size != info['size']:
                raise ValueError('Backup size mismatch.')
            target = destination / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with target.open('xb') as out, archive.extractfile(member) as src:
                shutil.copyfileobj(src, out)
            target.chmod(0o600)
            if digest(target) != info['sha256']:
                raise ValueError('Backup checksum mismatch.')
        if any(n.endswith('.enc') for n in expected) and 'secret.key' not in expected:
            raise ValueError('Backup is missing its encryption key.')
        return len(expected)


def verify(archive):
    with tempfile.TemporaryDirectory(prefix='pawsec-verify-') as tmp:
        return unpack(archive, Path(tmp))


def restore(archive, target):
    target = Path(target).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Restore requires a NEW directory. Existing data is never overwritten.')
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.pawsec-restore-', dir=target.parent) as tmp:
        count = unpack(archive, Path(tmp))
        target.mkdir(mode=0o700)  # exclusive reservation, never replaces an existing directory
        shutil.copytree(tmp, target, dirs_exist_ok=True)
    return count


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    b = commands.add_parser('backup')
    b.add_argument('--data-dir', type=Path, default=data_dir())
    b.add_argument('--output', type=Path, default=Path.home() / 'PawSec-backups' / ('pawsec-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.tar.gz'))
    v = commands.add_parser('verify'); v.add_argument('archive', type=Path)
    r = commands.add_parser('restore'); r.add_argument('archive', type=Path); r.add_argument('--to', required=True, type=Path)
    a = p.parse_args()
    try:
        if a.command == 'backup':
            print('Verified private backup:', backup(a.data_dir, a.output))
        elif a.command == 'verify':
            print('Verified files:', verify(a.archive))
        else:
            print('Restored files:', restore(a.archive, a.to))
            print('Original library unchanged. To use this copy, set PAWSEC_DATA_DIR to:', a.to)
    except (OSError, ValueError, RuntimeError, tarfile.TarError, KeyError) as e:
        p.exit(1, f'Backup/restore stopped: {e}\n')


if __name__ == '__main__':
    main()
