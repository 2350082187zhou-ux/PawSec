import sys,tempfile,unittest,json,threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import app as m
from auto_reader import AutoReader,validate,chunks,fingerprint
from plugins.research_plus import ACTIVE
QUOTE='We evaluate forensic artifacts from local language model applications.'
def output():return json.dumps({**{k:'Result supported by the paper [p.1]' for k in ['summary','question','method','results','limitations','reproduction']},'key_points':[{'text':'Key finding','evidence':[{'page':1,'quote':QUOTE},{'page':900,'quote':'fake'},{'page':1,'quote':'An invented quote absent from the paper'}]}],'keywords':[{'term':'Forensics','meaning':'Analysis of traces'}],'questions':['Can this generalize?']})
class AutoReaderTests(unittest.TestCase):
 def setUp(self):
  self.old=m.DATA;self.oldjobs=m.jobs;m.jobs={};self.tmp=tempfile.TemporaryDirectory();m.DATA=Path(self.tmp.name);self.s=AutoReader(m)
  self.cfg={'id':'test','base':'https://example.test/v1','key':'SECRET','model':'mock','language':'zh'};self.config=patch.object(m,'config',return_value=self.cfg);self.config.start();self.p=self.paper('a');self.client=m.app.test_client()
 def tearDown(self):self.config.stop();m.DATA=self.old;m.jobs=self.oldjobs;self.tmp.cleanup()
 def paper(self,key,text=None):
  p={'id':key*32,'title':'Test paper','pages':[{'n':1,'text':text if text is not None else QUOTE*5}],'notes':'My own note','report':'Existing report','sections':[],'chat':[],'created':1};(m.DATA/p['id']).mkdir();m.put(p);return p
 def test_settings_and_no_default_auto(self):
  self.assertFalse(self.s.settings()['enabled'])
  for c in [{'enabled':'yes'},{'language':'fr'},{'max_pages':True},{'max_pages':601},{'focus':'a'*2001}]:
   with self.assertRaises(ValueError):self.s.configure(c)
 def test_success_cache_preserves_notes_and_no_activity(self):
  self.s.configure({'language':'ja'});self.s.enqueue(self.p['id'])
  def llm(prompt):
   self.assertEqual(ACTIVE.get()['language'],'ja');return output() if 'ONLY valid JSON' in prompt else QUOTE+' [p.1]'
  with patch.object(m,'llm',side_effect=llm) as model:self.s.run_one();self.assertEqual(model.call_count,2)
  p=m.paper(self.p['id']);self.assertEqual(p['notes'],'My own note');self.assertEqual(p['report'],'Existing report');self.assertEqual(p['auto_read_result']['language'],'ja');self.assertEqual(self.s.enqueue(p['id'])['code'],'cached');self.assertFalse((m.DATA/'study_tracker.sqlite3').exists());self.assertNotIn('SECRET',self.s.state_path.read_text());self.assertIsNone(ACTIVE.get())
 def test_quote_verification(self):
  result=validate(output(),self.p);ev=result['key_points'][0]['evidence'];self.assertTrue(ev[0]['verified']);self.assertIsNone(ev[1]['page']);self.assertFalse(ev[2]['verified'])
 def test_dedup_and_cancel_queued(self):
  self.s.enqueue(self.p['id']);self.s.enqueue(self.p['id']);self.assertEqual(len(self.s.state()),1);self.s.cancel(self.p['id']);self.assertEqual(self.s.state()[self.p['id']]['status'],'cancelled')
  with patch.object(m,'llm') as call:self.assertFalse(self.s.run_one());call.assert_not_called()
 def test_cancel_during_model_call(self):
  self.s.enqueue(self.p['id'])
  def llm(prompt):self.s.cancel(self.p['id']);return 'notes'
  with patch.object(m,'llm',side_effect=llm) as call:self.s.run_one();self.assertEqual(call.call_count,1)
  self.assertEqual(self.s.state()[self.p['id']]['status'],'cancelled');self.assertNotIn('auto_read_result',m.paper(self.p['id']))
 def test_recovery_and_model_switch(self):
  self.s.enqueue(self.p['id']);self.s.recover();self.assertEqual(self.s.state()[self.p['id']]['status'],'interrupted');self.s.enqueue(self.p['id']);self.cfg['model']='changed'
  with patch.object(m,'llm') as call:self.s.run_one();call.assert_not_called()
  self.assertEqual(self.s.state()[self.p['id']]['code'],'model_changed')
 def test_error_and_legacy_exclusion(self):
  self.s.enqueue(self.p['id']);m.jobs['legacy']={'status':'running'};self.assertFalse(self.s.run_one());m.jobs.clear()
  with patch.object(m,'llm',side_effect=RuntimeError('SECRET')):self.s.run_one()
  self.assertEqual(self.s.state()[self.p['id']]['code'],'model_failed');self.assertNotIn('SECRET',self.s.state_path.read_text())
 def test_blocks_scanned_and_page_limit(self):
  p=self.paper('b','');self.assertEqual(self.s.enqueue(p['id'])['code'],'needs_ocr');p['pages']*=2;m.put(p);self.s.configure({'max_pages':1});self.assertEqual(self.s.enqueue(p['id'])['code'],'page_limit')
 def test_chunk_coverage_and_invalid_schema(self):
  p=self.p|{'pages':[{'n':1,'text':'a'*40000},{'n':2,'text':'END_OF_DOCUMENT'}]};parts=chunks(p);self.assertTrue(all(len(x)<=16000 for x in parts));self.assertIn('END_OF_DOCUMENT',''.join(parts));self.assertIn('[p.2]',''.join(parts))
  with self.assertRaises(ValueError):validate('{}',self.p)
 def test_api_and_import_hook(self):
  import pymupdf as fitz
  self.s.configure({'enabled':True});doc=fitz.open();page=doc.new_page();page.insert_text((40,80),QUOTE);raw=doc.tobytes();doc.close();p=m.ingest(raw,'fixture.pdf');self.assertEqual(self.s.state()[p['id']]['status'],'queued')
  r=self.client.post('/api/auto-reader/start',json={'ids':[self.p['id']]},base_url='http://127.0.0.1:8765');self.assertEqual(r.status_code,200)
  with patch.object(m,'llm',side_effect=lambda prompt:output() if 'ONLY valid JSON' in prompt else QUOTE):self.s.run_one();self.s.run_one()
  r=self.client.get('/api/auto-reader/'+self.p['id']+'/download',base_url='http://127.0.0.1:8765');self.assertEqual(r.status_code,200);self.assertIn(b'Key finding',r.data)
  from paper_briefs import brief
  from pawsec_reports import seed_summary
  self.assertEqual(brief(m.paper(self.p['id']))['source'],'auto');self.assertEqual(seed_summary(m.paper(self.p['id']))[1],'AI 自动阅读小结')
if __name__=='__main__':unittest.main()
