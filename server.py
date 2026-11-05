"""One production process owns HTTP, the serial AI queue, and periodic tasks."""
import os,threading
from waitress import serve
import app as m

def start_background():
 for name,worker in m.app.extensions.get('background_workers',[]):
  threading.Thread(target=worker,daemon=True,name=name).start()
 auto=m.app.extensions['auto_reader'];auto.recover()
 threading.Thread(target=auto.worker,daemon=True,name='auto-paper-reader').start()

if __name__=='__main__':
 start_background()
 serve(m.app,host=os.getenv('PAWSEC_BIND','127.0.0.1'),port=int(os.getenv('PORT','8765')),threads=12,max_request_body_size=50*1024*1024,channel_timeout=240,clear_untrusted_proxy_headers=True)
