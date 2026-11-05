"""Interactive owner password setup. Never prints or stores the plaintext password."""
from getpass import getpass
from pathlib import Path
import os
from werkzeug.security import generate_password_hash

def main():
 root=Path(__file__).resolve().parents[1];folder=root/'secrets';folder.mkdir(mode=0o700,exist_ok=True)
 if os.name!='nt':folder.chmod(0o700)
 path=folder/'admin-password.hash'
 if path.exists():raise SystemExit('Password file already exists. Rename it explicitly before creating a replacement.')
 password=getpass('New administrator password (at least 16 characters): ')
 if len(password)<16:raise SystemExit('Use at least 16 characters.')
 if password!=getpass('Repeat password: '):raise SystemExit('Passwords do not match.')
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w',encoding='utf-8') as out:out.write(generate_password_hash(password)+'\n')
 # Docker bind-mounted secrets must be readable by the non-root container UID.
 # The parent directory remains owner-only on the host.
 path.chmod(0o644)
 print('Created secrets/admin-password.hash. Keep this file private.')
if __name__=='__main__':main()
