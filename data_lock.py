"""One writer per library, shared by the server and offline maintenance."""
import json
import os
from pathlib import Path


def data_dir():
    return Path(os.getenv('PAWSEC_DATA_DIR', str(Path(__file__).resolve().parent / 'data'))).expanduser().resolve()


def process_identity(pid):
    try:
        text = Path(f'/proc/{pid}/stat').read_text()
        return text[text.rindex(')') + 2:].split()[19]
    except (OSError, ValueError, IndexError):
        return None


class DataLock:
    def __init__(self, directory, purpose='maintenance'):
        self.directory = Path(directory).resolve()
        self.purpose = purpose
        self.handle = None

    def __enter__(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.directory / '.pawsec.lock',
                     os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        self.handle = os.fdopen(fd, 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            raise RuntimeError('Library is in use. Stop PawSec before maintenance.') from None
        state = {'pid': os.getpid(), 'identity': process_identity(os.getpid()), 'purpose': self.purpose}
        self.handle.seek(0)
        self.handle.write(json.dumps(state).encode())
        self.handle.truncate()
        self.handle.flush()
        return self

    def __exit__(self, *_):
        if self.handle:
            self.handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()
            self.handle = None
