"""Single-owner deployment boundary; public mode fails closed without credentials."""
import os,hmac,time,threading
from collections import deque
from urllib.parse import urlsplit
from flask import request,abort,Response
from werkzeug.security import check_password_hash

def install(app):
 mode=os.getenv('PAWSEC_MODE','local')
 if mode not in ('local','public'):raise RuntimeError('PAWSEC_MODE must be local or public')
 origin=os.getenv('PAWSEC_PUBLIC_ORIGIN','').rstrip('/')
 user=os.getenv('PAWSEC_ADMIN_USER','admin')
 hashfile=os.getenv('PAWSEC_PASSWORD_HASH_FILE','')
 password_hash=''
 if mode=='public':
  u=urlsplit(origin)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:raise RuntimeError('Set PAWSEC_PUBLIC_ORIGIN to https://your-domain without a path')
  if not hashfile:raise RuntimeError('Public mode requires PAWSEC_PASSWORD_HASH_FILE')
  from pathlib import Path
  password_hash=Path(hashfile).read_text(encoding='utf-8').strip()
  if not password_hash.startswith(('scrypt:','pbkdf2:')) or len(password_hash)<80:raise RuntimeError('Create an admin password hash with tools/create_admin.py')
  if not user or ':' in user:raise RuntimeError('Invalid administrator username')
 allowed_hosts={urlsplit(origin).netloc.lower()} if mode=='public' else {'127.0.0.1:8765','localhost:8765'}
 allowed_origins={origin} if mode=='public' else {'http://127.0.0.1:8765','http://localhost:8765'}
 failures=deque();gate=threading.Lock()
 def challenge(status=401):
  return Response('Sign in to your PawSec workspace.',status,{'WWW-Authenticate':'Basic realm="PawSec", charset="UTF-8"','Cache-Control':'no-store','Retry-After':'60'} if status==429 else {'WWW-Authenticate':'Basic realm="PawSec", charset="UTF-8"','Cache-Control':'no-store'})
 @app.before_request
 def deployment_guard():
  if request.host.lower() not in allowed_hosts:abort(403)
  supplied=request.headers.get('Origin')
  if supplied and supplied not in allowed_origins:abort(403)
  if request.headers.get('Sec-Fetch-Site')=='cross-site':abort(403)
  if mode=='public':
   auth=request.authorization
   if not auth or auth.type.lower()!='basic':return challenge()
   with gate:
    now=time.monotonic()
    while failures and now-failures[0]>60:failures.popleft()
    if len(failures)>=20:return challenge(429)
   valid=hmac.compare_digest((auth.username or '').encode(),user.encode()) and check_password_hash(password_hash,auth.password or '')
   if not valid:
    with gate:failures.append(time.monotonic())
    return challenge()
   # Browser fetches send Origin for mutations; clients must explicitly supply it.
   if request.method not in ('GET','HEAD','OPTIONS') and supplied!=origin:abort(403)
 @app.after_request
 def private_headers(response):
  if mode=='public':response.headers['Cache-Control']='no-store';response.headers['Vary']='Authorization'
  return response
