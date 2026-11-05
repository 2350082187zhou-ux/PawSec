import io, json, tempfile, time, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import pymupdf as fitz
import app as m
from research import validate_analysis

QUOTE='The attacker can observe network traffic but cannot modify the trusted server.'
def analysis(): return {'question':'研究网络入侵检测在边界条件下的表现 [p.1]','method':'对网络流量提取特征，再进行检测 [p.1]','results':'示例数据仅用于软件测试，不作为论文实验结果 [p.1]','limitations':'测试材料没有真实数据集 [p.1]','reproduction':'这是功能测试文档，没有实际复现实验','threat_model':{'attacker':'网络观察者 [p.1]','capabilities':'可观察流量 [p.1]','trust_boundary':'可信服务器 [p.1]','assumptions':'不能修改服务器 [p.1]'},'contributions':[{'claim':'明确描述攻击者权限 [p.1]','assessment':'能支持威胁模型的解释，不能据此判断全球新颖性','limits':'仅验证原文描述','evidence':[{'page':1,'quote':QUOTE}]}]}
class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.old=m.DATA; m.DATA=Path(self.temp.name); m.jobs.clear(); self.c=m.app.test_client(); self.host={'base_url':'http://127.0.0.1:8765'}
    def tearDown(self): m.DATA=self.old; self.temp.cleanup()
    def get(self,url): return self.c.get(url,**self.host)
    def post(self,url,data): return self.c.post(url,json=data,**self.host)
    def fixture(self,title='Security testing paper'):
        d=fitz.open(); p=d.new_page(); p.insert_text((50,60),title); p.insert_textbox(fitz.Rect(50,100,540,400),(QUOTE+' Network intrusion detection malware privacy. ')*6,fontsize=12)
        raw=d.tobytes(); d.close(); return m.ingest(raw,title+'.pdf')
    def wait(self,pid):
        for _ in range(300):
            if m.jobs[pid]['status']!='running': break
            time.sleep(.01)
        self.assertEqual(m.jobs[pid]['status'],'done',m.jobs[pid])
    def test_evidence_verification(self):
        p=self.fixture(); o=validate_analysis(analysis(),p); self.assertTrue(o['contributions'][0]['evidence'][0]['verified'])
        a=analysis(); a['contributions'][0]['evidence']=[{'page':999,'quote':QUOTE},{'page':1,'quote':'Invented fabricated statement'}]
        o=validate_analysis(a,p); self.assertFalse(any(e['verified'] for e in o['contributions'][0]['evidence']))
    def test_highlights_persist_and_export(self):
        p=self.fixture(); pid=p['id']; h=self.post(f'/api/papers/{pid}/highlights',{'page':1,'quote':QUOTE,'rects':[[.1,.1,.7,.15]],'color':'pink','note':'重要边界'}); self.assertEqual(h.status_code,200)
        self.assertEqual(m.paper(pid)['highlights'][0]['note'],'重要边界')
        r=self.get(f'/api/papers/{pid}/annotated.pdf'); d=fitz.open(stream=r.data,filetype='pdf'); self.assertEqual(len(list(d[0].annots())),1); self.assertIn('重要边界',list(d[0].annots())[0].info['content']); d.close()
        for data in [{'page':0,'quote':'x'},{'page':1,'quote':'x','rects':[[0,0,2,1]]},{'page':1,'quote':'x','color':'evil'}]: self.assertEqual(self.post(f'/api/papers/{pid}/highlights',data).status_code,400)
        self.c.delete(f"/api/papers/{pid}/highlights/{h.json['id']}",**self.host); self.assertEqual(m.paper(pid)['highlights'],[])
    def test_topics_and_related(self):
        p=self.fixture(); q=self.fixture('Other security paper'); r=self.get(f"/api/papers/{p['id']}/related"); self.assertEqual(r.json['local'][0]['id'],q['id']); self.assertIn('网络入侵检测',r.json['local'][0]['topics'])
    def test_analysis_and_comparison(self):
        p=self.fixture(); q=self.fixture('Second paper'); pid=p['id']
        with patch.object(m,'llm',return_value=json.dumps(analysis())),patch.object(m,'config',return_value={'model':'test-model'}):
            self.assertEqual(self.post(f'/api/papers/{pid}/analyze',{}).status_code,200); self.wait(pid)
        self.assertTrue(m.paper(pid)['analysis']['contributions'][0]['evidence'][0]['verified'])
        with patch.object(m,'llm',return_value='Two studies [A:p.1] [B:p.1]') as mock:
            self.post(f'/api/papers/{pid}/compare',{'ids':[q['id']]}); self.wait(pid); self.assertIn('[B:p.1]',mock.call_args.args[0])
        self.assertEqual(m.paper(pid)['comparison']['sources'][1]['id'],q['id'])
    def test_download_formats_and_content(self):
        p=self.fixture(); pid=p['id']; p['notes']='我的阅读笔记：信任边界'; m.put(p)
        s={'title':'网安论文重点：功能测试文稿','subtitle':'仅用于软件导出验证','sections':[{'title':x,'body':'这里是用于排版验证的重点内容。威胁模型与原文证据需要同时呈现。[p.1]'} for x in ['研究问题','核心贡献','关键方法','实验结果','局限边界','复现清单']]}
        self.assertEqual(self.post(f'/api/papers/{pid}/story',s).status_code,200)
        r=self.get(f'/api/papers/{pid}/download/notes.pdf'); self.assertEqual(r.status_code,200); d=fitz.open(stream=r.data,filetype='pdf'); self.assertIn('信任边界',''.join(x.get_text() for x in d)); d.close()
        r=self.get(f'/api/papers/{pid}/download/poster.pdf'); self.assertEqual(r.status_code,200); d=fitz.open(stream=r.data,filetype='pdf'); self.assertEqual(len(d),1); self.assertIn('核心贡献',d[0].get_text()); d.close()
        r=self.get(f'/api/papers/{pid}/download/poster.png'); self.assertEqual(r.data[:8],b'\x89PNG\r\n\x1a\n')
        r=self.get(f'/api/papers/{pid}/download/slides.pptx'); self.assertEqual(r.status_code,200,r.json if r.is_json else '')
        with zipfile.ZipFile(io.BytesIO(r.data)) as z:
            slides=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]; self.assertEqual(len(slides),7); self.assertIn('核心贡献',z.read('ppt/slides/slide3.xml').decode())
        self.assertIn('信任边界',self.get(f'/api/papers/{pid}/export').text)
        s['sections'][0]['body']='长'*221; self.assertEqual(self.post(f'/api/papers/{pid}/story',s).status_code,400)
    def test_unedited_story_not_exported(self):
        p=self.fixture(); self.assertEqual(self.get(f"/api/papers/{p['id']}/download/slides.pptx").status_code,400)
if __name__=='__main__': unittest.main(verbosity=2)
