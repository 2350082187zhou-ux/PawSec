import io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import pymupdf as fitz
import app as m
from plugins.research_plus import rankings_for,ACTIVE
class PlusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=m.DATA;m.DATA=Path(self.tmp.name);m.jobs.clear();self.c=m.app.test_client();self.host={'base_url':'http://127.0.0.1:8765'}
 def tearDown(self):m.DATA=self.old;self.tmp.cleanup()
 def post(self,url,v):return self.c.post(url,json=v,**self.host)
 def get(self,url):return self.c.get(url,**self.host)
 def profile(self,name='One',model='model-a'):
  return self.post('/api/models/profiles',{'name':name,'model':model,'base':'https://example.com/v1','protocol':'chat','key':'SECRET-XYZ'}).json
 def paper(self,title):
  d=fitz.open();p=d.new_page();p.insert_textbox(fitz.Rect(40,60,550,700),('Differential privacy protects neighboring datasets with epsilon privacy guarantees. We compare privacy loss and noise mechanisms.\n\n')*6);raw=d.tobytes();d.close();return m.ingest(raw,title+'.pdf')
 def test_profiles_and_secret(self):
  s=self.profile();self.assertNotIn('SECRET',json.dumps(s));a=s['active'];s=self.profile('Two','model-b');b=s['active'];self.post('/api/models/activate',{'id':a});self.assertEqual(m.config()['model'],'model-a');self.assertEqual(m.config()['key'],'SECRET-XYZ');self.assertNotIn(b'SECRET-XYZ',(m.DATA/'models.enc').read_bytes());self.post('/api/models/profiles',{'id':a,'name':'Edited','model':'model-a','base':'https://example.com/v1','protocol':'chat','key':''});self.assertEqual(m.config()['key'],'SECRET-XYZ');self.assertEqual(self.post('/api/models/activate',{'id':'invalid'}).status_code,400)
 def test_discovery(self):
  s=self.profile();response=Mock(status_code=200,json=lambda:{'data':[{'id':'alpha'},{'id':'beta'},{'id':'alpha'}]})
  with patch('plugins.research_plus.requests.get',return_value=response) as req:
   r=self.post('/api/models/discover',{'id':s['active']});self.assertEqual(r.json['models'],['alpha','beta']);self.assertEqual(req.call_args.kwargs['headers']['Authorization'],'Bearer SECRET-XYZ')
  self.assertEqual(self.post('/api/models/discover',{'base':'http://example.com','key':'x'}).status_code,400)
 def test_language_and_schema_preservation(self):
  self.profile();self.post('/api/preferences',{'language':'ja','motion':False});self.assertEqual(m.config()['language'],'ja')
  with patch.object(m.requests,'post',return_value=Mock(status_code=200,json=lambda:{'choices':[{'message':{'content':'ok'}}]})) as req:
   m.llm('test');body=req.call_args.kwargs['json'];self.assertIn('Japanese',body['messages'][0]['content']);self.assertIn('JSON keys',body['messages'][0]['content'])
  self.assertEqual(self.post('/api/preferences',{'language':'xx'}).status_code,400)
 def test_background_model_snapshot(self):
  a=self.profile()['active'];p=self.paper('A');seen=[]
  with m.app.test_request_context(base_url='http://127.0.0.1:8765'):
   m.launch(p['id'],'test',lambda:(time.sleep(.15),seen.append(m.config()['model'])))
  self.profile('B','model-b')
  for _ in range(100):
   if m.jobs[p['id']]['status']!='running':break
   time.sleep(.01)
  self.assertEqual(seen,['model-a'])
 def test_passage_matches_and_theory(self):
  p=self.paper('A');q=self.paper('B');r=self.post('/api/papers/'+p['id']+'/connections',{'selection':'Differential privacy protects neighboring datasets with epsilon privacy guarantees.','page':1});self.assertEqual(r.status_code,200);self.assertTrue(r.json['selection_verified']);self.assertEqual(r.json['theories'][0]['id'],'dp');self.assertTrue(any(x['paper_id']==q['id'] for x in r.json['local']));self.assertEqual(r.json['online'],[])
  with patch.object(m,'llm',return_value='Relation [L1] [T1]') as llm:
   r=self.post('/api/papers/'+p['id']+'/connections',{'selection':'Differential privacy protects neighboring datasets with epsilon privacy guarantees.','page':1,'explain':True});self.assertIn('[L1]',r.json['explanation']);self.assertIn('not proof',llm.call_args.args[0])
 def test_ranking_import_and_matching(self):
  rows=[{'venue':'Journal X','system':'JCR','rank':'Q1','year':'2025','category':'Security','source':'https://jcr.clarivate.com/','issns':['1234-5678']},{'venue':'Journal X','system':'CAS','rank':'2','year':'2024','category':'Computer Science','source':'https://www.fenqubiao.com/'}]
  r=self.post('/api/rankings/import',{'rows':rows});self.assertEqual(r.status_code,200);data=self.get('/api/rankings').json['rows'];found=rankings_for('Journal X',[],data);self.assertEqual(len(found),2);self.assertTrue(all(x['status']=='user_supplied' for x in found));self.assertEqual(rankings_for('Journal X supplement',[],data),[]);self.assertEqual(rankings_for('Different name',['1234-5678'],data)[0]['rank'],'Q1');rows[0]['year']='';self.assertEqual(self.post('/api/rankings/import',{'rows':rows}).status_code,400)
 def test_ccf_snapshot(self):
  rows=self.get('/api/rankings').json['rows'];found=rankings_for('ACM Conference on Computer and Communications Security',[],rows);self.assertEqual(found[0]['rank'],'A');self.assertEqual(found[0]['status'],'community_snapshot');self.assertIn('github.com',found[0]['source'])
if __name__=='__main__':unittest.main(verbosity=2)
