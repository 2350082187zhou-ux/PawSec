import sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import app as m
from paper_briefs import brief,abstract,keywords,excerpt
from plugins.research_plus import ACTIVE
class BriefTests(unittest.TestCase):
 def setUp(self):
  self.old=m.DATA;self.tmp=tempfile.TemporaryDirectory();m.DATA=Path(self.tmp.name);self.client=m.app.test_client();self.base='http://127.0.0.1:8765'
 def tearDown(self):m.DATA=self.old;self.tmp.cleanup()
 def test_sources(self):
  p={'title':'Security','publication':{'abstract':'An abstract with cautious conclusions.','keywords':['Digital forensics','Privacy']}}
  b=brief(p);self.assertEqual(b['keywords'],['Digital forensics','Privacy']);self.assertEqual(b['source'],'abstract');self.assertEqual(b['keyword_source'],'publisher')
  self.assertEqual(brief({'title':'Empty'})['source'],'missing')
  p['report']='Existing report';self.assertEqual(brief(p)['summary'],'Existing report')
 def test_extraction(self):
  text='A B S T R A C T\n'+('We study network security and digital forensics with uncertain results. '*5)+'\n1. Introduction\nSHOULD NOT APPEAR'
  a=abstract({'pages':[{'text':text}]});self.assertNotIn('SHOULD NOT APPEAR',a);self.assertIn('network security',a)
  self.assertLessEqual(len(excerpt('long words '*500)),361)
 def test_preview_no_model_call(self):
  p={'id':'a'*32,'title':'Network security','created':1,'pages':[{'n':1,'text':'text'}],'report':'Existing short report','notes':'','chat':[]};(m.DATA/p['id']).mkdir();m.put(p)
  with patch.object(m,'llm',side_effect=AssertionError('GET must not call model')):
   r=self.client.get('/api/papers',base_url=self.base);self.assertEqual(r.status_code,200);self.assertEqual(r.json[0]['brief']['summary'],'Existing short report')
 def test_pdf_two_column_abstract(self):
  import pymupdf as fitz
  from paper_briefs import pdf_preview
  pid='b'*32;(m.DATA/pid).mkdir();doc=fitz.open();pg=doc.new_page()
  pg.insert_text((30,60),'ARTICLE INFO');pg.insert_text((220,60),'A B S T R A C T')
  pg.insert_text((30,85),'Keywords:\nDigital forensics\nLocal LLM')
  pg.insert_text((220,85),'This study proposes a forensic framework.\nIt analyzes local language model artifacts.\nFurther evaluation is required.')
  pg.insert_text((30,180),'1. Introduction\nNOT ABSTRACT');doc.save(m.DATA/pid/'source.pdf');doc.close()
  text,terms=pdf_preview({'id':pid},m.DATA);self.assertIn('forensic framework',text);self.assertNotIn('NOT ABSTRACT',text);self.assertEqual(terms,['Digital forensics','Local LLM'])
  self.assertEqual(brief({'id':pid,'title':'Paper'},m.DATA)['source'],'abstract')
 def test_translation_cache_and_language(self):
  body={'title':'Security','summary':'Uncertain results','keywords':['security'],'language':'ja'}
  def fake(prompt):self.assertEqual(ACTIVE.get()['language'],'ja');return json.dumps({'summary':'結果は不確実です。','keywords':['セキュリティ']})
  with patch.object(m,'llm',side_effect=fake) as call:
   a=self.client.post('/api/paper-brief/translate',json=body,base_url=self.base);self.assertEqual(a.status_code,200);b=self.client.post('/api/paper-brief/translate',json=body,base_url=self.base);self.assertEqual(a.json,b.json);self.assertEqual(call.call_count,1)
  self.assertIsNone(ACTIVE.get())
  for invalid in [body|{'language':'xx'},body|{'summary':''},body|{'keywords':['x']*9}]:self.assertEqual(self.client.post('/api/paper-brief/translate',json=invalid,base_url=self.base).status_code,400)
if __name__=='__main__':unittest.main()
