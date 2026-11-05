import sys,tempfile,json,sqlite3,unittest
from pathlib import Path
from datetime import datetime,date
sys.path.insert(0,str(Path(__file__).resolve().parent))
import app as m
from pawsec_reports import Reports,period
from report_export import make_pdf
import pymupdf as fitz
from contextlib import closing

class ReportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.previous=m.DATA;m.DATA=Path(self.tmp.name);self.r=Reports(m);self.client=m.app.test_client()
  self.a=self.paper('a',datetime(2026,11,4,0,0));self.b=self.paper('b',datetime(2026,11,3,23,59));self.c=self.paper('c',datetime(2026,10,31,23,59))
  with closing(sqlite3.connect(m.DATA/'study_tracker.sqlite3')) as db:
   db.executescript('CREATE TABLE activity(day TEXT,pid TEXT,title TEXT,seconds REAL);CREATE TABLE completions(pid TEXT,day TEXT,title TEXT,at REAL);')
   db.execute('INSERT INTO activity VALUES(?,?,?,?)',('2026-11-04',self.b['id'],self.b['title'],120))
   db.execute('INSERT INTO completions VALUES(?,?,?,?)',(self.b['id'],'2026-11-04',self.b['title'],0))
   db.commit()
 def tearDown(self):m.DATA=self.previous;self.tmp.cleanup()
 def paper(self,key,dt):
  pid=key*32;p={'id':pid,'title':'网络安全研究 '+key,'created':dt.timestamp(),'pages':[{'n':1,'text':'Abstract\nWe study network intrusion detection using packet features. Results depend on the dataset.\nKeywords security'}],'report':'','notes':'真实笔记','chat':[]};(m.DATA/pid).mkdir();m.put(p);return p
 def test_boundaries(self):
  self.assertEqual(period('week','2026-11-01'),(date(2026,10,26),date(2026,11,2)))
  self.assertEqual(period('month','2024-02-29'),(date(2024,2,1),date(2024,3,1)))
  self.assertEqual(period('week','2027-01-01'),(date(2026,12,28),date(2027,1,4)))
  for kind,value in [('year','2026-11-04'),('day','../../x'),('day','2026-02-30')]:
   with self.assertRaises(ValueError):period(kind,value)
 def test_import_vs_activity(self):
  day=self.r.build('day','2026-11-04');self.assertEqual(day['stats'],{'imported':1,'read':1,'completed':1,'seconds':120});self.assertEqual(len(day['entries']),2)
  self.assertTrue(next(x for x in day['entries'] if x['id']==self.a['id'])['imported']);self.assertFalse(next(x for x in day['entries'] if x['id']==self.b['id'])['imported'])
  self.assertEqual(self.r.build('week','2026-11-04')['stats']['imported'],2);self.assertEqual(self.r.build('month','2026-11-04')['stats']['imported'],2)
 def test_save_reopen_conflict_and_new_import(self):
  original=self.r.build('day','2026-11-04');original['entries'][0]['summary']='手动小结保留';saved=self.r.save('day','2026-11-04',original);self.assertEqual(saved['revision'],1)
  self.assertEqual(self.r.build('day','2026-11-04')['entries'][0]['summary'],'手动小结保留')
  from werkzeug.exceptions import Conflict
  with self.assertRaises(Conflict):self.r.save('day','2026-11-04',original)
  self.paper('d',datetime(2026,11,4,15));merged=self.r.build('day','2026-11-04');self.assertEqual(len(merged['entries']),3);self.assertTrue(any(x['summary']=='手动小结保留' for x in merged['entries']))
 def test_api_and_exports(self):
  base='http://127.0.0.1:8765';url='/api/reports?kind=week&date=2026-11-04'
  report=self.client.get(url,base_url=base).json;self.assertEqual(self.client.post(url,json=report,base_url=base).status_code,200)
  self.assertEqual(self.client.post(url,json=report,base_url=base).status_code,409)
  for fmt in ['pdf','md','json']:
   result=self.client.get('/api/reports/download/'+fmt+'?kind=week&date=2026-11-04',base_url=base);self.assertEqual(result.status_code,200);self.assertGreater(len(result.data),100)
  self.assertEqual(self.client.get('/api/reports?kind=day&date=bad',base_url=base).status_code,400)
 def test_long_pdf(self):
  r=self.r.build('month','2026-11-04');r['title']='网络安全研究月报 / 2026年11月';r['achievements']='完成两篇文献的威胁模型比较，明确攻击者能力与方法适用范围。'
  r['entries'][0]['summary']=('研究问题：检测网络中的可疑行为。方法：分析流量特征与模型输出。结果：现有材料未报告具体指标。局限：跨数据集泛化需要进一步验证。[p.1]\n')*18
  raw=make_pdf(r);dest=Path(__file__).resolve().parent/'.qa'/'report-sample.pdf';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  doc=fitz.open(stream=raw,filetype='pdf');self.assertGreater(len(doc),1);self.assertIn('网络安全研究', ''.join(p.get_text() for p in doc));print('PDF pages:',len(doc))
  for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(1.1,1.1)).save(str(dest.with_name(f'report-sample-{i+1}.png')))
 def test_summary_cache_across_periods(self):
  original=m.llm;m.llm=lambda prompt:'论文小结：数据集泛化仍需验证。[p.1]'
  try:
   response=self.client.post('/api/reports/summary/'+self.a['id'],json={},base_url='http://127.0.0.1:8765');self.assertEqual(response.status_code,200)
   for kind in ['day','week','month']:
    entry=next(e for e in self.r.build(kind,'2026-11-04')['entries'] if e['id']==self.a['id']);self.assertEqual(entry['summary'],response.json['summary'])
  finally:m.llm=original

if __name__=='__main__':unittest.main()
