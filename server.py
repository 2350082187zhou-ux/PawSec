"""One process owns HTTP, the serial AI queue, and periodic tasks."""
import os
import threading
from data_lock import DataLock, data_dir


def bind_address():
    if os.getenv('PAWSEC_MODE', 'local') == 'local':
        return '127.0.0.1', 8765
    return os.getenv('PAWSEC_BIND', '127.0.0.1'), int(os.getenv('PORT', '8765'))


def start_background(m):
    for name, worker in m.app.extensions.get('background_workers', []):
        threading.Thread(target=worker, daemon=True, name=name).start()
    auto = m.app.extensions['auto_reader']
    auto.recover()
    threading.Thread(target=auto.worker, daemon=True, name='auto-paper-reader').start()


def main():
    os.umask(0o077)
    with DataLock(data_dir(), 'server'):
        from waitress import serve
        import app as m
        start_background(m)
        host, port = bind_address()
        print(f'PawSec: http://{host}:{port} (Ctrl+C to stop)', flush=True)
        serve(m.app, host=host, port=port, threads=12,
              max_request_body_size=50 * 1024 * 1024, channel_timeout=240,
              clear_untrusted_proxy_headers=True)


if __name__ == '__main__':
    main()
