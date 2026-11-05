import base64,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask,jsonify
from werkzeug.security import generate_password_hash
from deployment import install

class DeploymentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'password.hash';self.path.write_text(generate_password_hash('synthetic-test-password',method='scrypt:32768:8:1'))
  self.env={'PAWSEC_MODE':'public','PAWSEC_PUBLIC_ORIGIN':'https://papers.example.com','PAWSEC_PASSWORD_HASH_FILE':str(self.path),'PAWSEC_ADMIN_USER':'owner'}
 def tearDown(self):self.tmp.cleanup()
 def app(self,changes=None):
  app=Flask(__name__)
  with patch.dict(os.environ,self.env|(changes or {}),clear=True):install(app)
  @app.route('/api/papers',methods=['GET','POST'])
  def papers():return jsonify(ok=True)
  @app.get('/static/secret-test')
  def asset():return 'asset'
  return app
 def auth(self,password='synthetic-test-password'):return {'Authorization':'Basic '+base64.b64encode(('owner:'+password).encode()).decode()}
 def test_public_auth_covers_api_and_static(self):
  c=self.app().test_client()
  for url in ['/api/papers','/static/secret-test']:
   self.assertEqual(c.get(url,base_url='https://papers.example.com').status_code,401)
   self.assertEqual(c.get(url,headers=self.auth('wrong'),base_url='https://papers.example.com').status_code,401)
   r=c.get(url,headers=self.auth(),base_url='https://papers.example.com');self.assertEqual(r.status_code,200);self.assertEqual(r.headers['Cache-Control'],'no-store')
 def test_origin_host_and_csrf(self):
  c=self.app().test_client();base='https://papers.example.com'
  self.assertEqual(c.get('/api/papers',headers=self.auth(),base_url='https://attacker.example').status_code,403)
  self.assertEqual(c.get('/api/papers',headers=self.auth()|{'Sec-Fetch-Site':'cross-site'},base_url=base).status_code,403)
  self.assertEqual(c.post('/api/papers',headers=self.auth(),base_url=base).status_code,403)
  self.assertEqual(c.post('/api/papers',headers=self.auth()|{'Origin':'https://attacker.example'},base_url=base).status_code,403)
  self.assertEqual(c.post('/api/papers',headers=self.auth()|{'Origin':base},base_url=base).status_code,200)
 def test_missing_public_config_fails_closed(self):
  for env in [{'PAWSEC_PASSWORD_HASH_FILE':''},{'PAWSEC_PUBLIC_ORIGIN':'http://papers.example.com'},{'PAWSEC_PUBLIC_ORIGIN':'https://papers.example.com/path'},{'PAWSEC_MODE':'typo'}]:
   with self.assertRaises(RuntimeError):self.app(env)
 def test_local_mode_stays_loopback(self):
  c=self.app({'PAWSEC_MODE':'local'}).test_client()
  self.assertEqual(c.get('/api/papers',base_url='http://127.0.0.1:8765').status_code,200)
  self.assertEqual(c.get('/api/papers',base_url='http://papers.example.com').status_code,403)
 def test_no_credentials_leaked(self):
  c=self.app().test_client();r=c.get('/api/papers',base_url='https://papers.example.com');self.assertNotIn(b'scrypt',r.data);self.assertNotIn(b'synthetic',r.data)
if __name__=='__main__':unittest.main()
