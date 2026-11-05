import io, tempfile, unittest, time
from pathlib import Path
from unittest.mock import patch, Mock
import fitz
import app as m

class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.original=m.DATA; m.DATA=Path(self.temp.name); m.jobs.clear()
        self.client=m.app.test_client(); self.host={'base_url':'http://127.0.0.1:8765'}
    def tearDown(self): m.DATA=self.original; self.temp.cleanup()
    def get(self,url): return self.client.get(url,**self.host)
    def post(self,url,**kw): return self.client.post(url,**self.host,**kw)
    def upload(self):
        d=fitz.open()
        for i in range(3):
            p=d.new_page(); p.insert_text((60,60),f'Page {i+1}: Security experiment. Attacker controls the network. Accuracy 95 percent. Dataset has 100 samples.')
        raw=d.tobytes(); d.close()
        r=self.post('/api/papers',data={'file':(io.BytesIO(raw),'test.pdf')}); self.assertEqual(r.status_code,200); return r.json
    def test_import_read_notes_export(self):
        p=self.upload(); self.assertEqual(len(p['pages']),3); self.assertIn('95',p['pages'][1]['text']); pid=p['id']
        self.assertEqual(len(self.get('/api/papers').json),1)
        self.assertEqual(self.get(f'/api/papers/{pid}/pdf').mimetype,'application/pdf')
        self.post(f'/api/papers/{pid}/notes',json={'notes':'My note'})
        self.assertIn('My note',self.get(f'/api/papers/{pid}/export').text)
    def test_invalid_pdf_and_origin(self):
        self.assertEqual(self.post('/api/papers',data={'file':(io.BytesIO(b'bad'),'bad.pdf')}).status_code,400)
        self.assertEqual(self.post('/api/config',json={},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/papers',base_url='http://evil.example').status_code,403)
    def test_credentials_not_returned(self):
        r=self.post('/api/config',json={'base':'https://example.com/v1','model':'test','protocol':'chat','key':'secret-token'})
        self.assertNotIn('secret-token',r.text); self.assertNotIn(b'secret-token',(m.DATA/'config.enc').read_bytes())
        self.post('/api/config',json={'base':'https://example.com/v1','model':'test','protocol':'chat','key':''})
        self.assertEqual(m.config()['key'],'secret-token')
    def test_all_api_protocols(self):
        for protocol,response,endpoint in [('chat',{'choices':[{'message':{'content':'ok'}}]},'/chat/completions'),('responses',{'output':[{'content':[{'type':'output_text','text':'ok'}]}]},'/responses'),('claude',{'content':[{'type':'text','text':'ok'}]},'/messages')]:
            with patch.object(m,'config',return_value={'base':'https://example.com/v1','key':'test','model':'model','protocol':protocol}),patch.object(m.requests,'post',return_value=Mock(status_code=200,json=lambda:response)) as req:
                self.assertEqual(m.llm('question'),'ok'); self.assertTrue(req.call_args.args[0].endswith(endpoint))
    def test_summary_covers_pages_and_question(self):
        p=self.upload(); prompts=[]
        def fake(prompt,*args): prompts.append(prompt); return 'Verified [p.2]'
        with patch.object(m,'llm',side_effect=fake):
            self.post('/api/papers/'+p['id']+'/summarize',json={})
            for _ in range(200):
                if m.jobs[p['id']]['status']!='running': break
                time.sleep(.01)
            self.assertEqual(m.jobs[p['id']]['status'],'done')
            self.assertTrue(all(f'[p.{i}]' in prompts[0] for i in range(1,4)))
            r=self.post('/api/papers/'+p['id']+'/ask',json={'question':'attacker','page':2}); self.assertEqual(r.status_code,200)
            self.assertIn('[p.2]',r.json['answer']); self.assertEqual(len(m.paper(p['id'])['chat']),1)
    def test_private_download_rejected(self):
        with self.assertRaises(ValueError): m.public_get('https://127.0.0.1/private')
        with self.assertRaises(ValueError): m.public_get('file:///etc/passwd')
if __name__=='__main__': unittest.main(verbosity=2)
