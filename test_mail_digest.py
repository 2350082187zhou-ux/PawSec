import sys,tempfile,json,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import app as m
from mail_digest import MailDigest,DEFAULTS,email_address
class MailTests(unittest.TestCase):
 def setUp(self):
  self.old=m.DATA;self.tmp=tempfile.TemporaryDirectory();m.DATA=Path(self.tmp.name);self.now=datetime(2026,11,4,19,0,tzinfo=timezone(timedelta(hours=-5)));self.messages=[];self.mail=MailDigest(m,lambda:self.now,lambda c,msg:self.messages.append(msg))
  self.config=DEFAULTS|{'recipient':'reader@example.com','sender':'sender@example.com','smtp_host':'smtp.example.com','smtp_user':'sender@example.com','smtp_password':'secret-test','include_discovery':False,'attach_pdf':False}
 def tearDown(self):m.DATA=self.old;self.tmp.cleanup()
 def test_secrets_and_validation(self):
  result=self.mail.save(self.config);self.assertNotIn('smtp_password',result);self.assertTrue(result['has_password']);self.assertNotIn(b'secret-test',(m.DATA/'mail_digest.enc').read_bytes());self.mail.save({'smtp_password':''});self.assertEqual(self.mail.config()['smtp_password'],'secret-test')
  for bad in [{'recipient':'a@example.com\r\nBcc:x@y.com'},{'send_time':'25:99'},{'smtp_security':'plain'},{'max_results':True},{'keywords':['x']*6}]:
   with self.assertRaises(ValueError):self.mail.save(bad)
 def test_schedule_once_and_enable_after_time(self):
  self.mail.save(self.config|{'enabled':True});self.now=self.now.replace(hour=20,minute=1)
  with patch('mail_digest.threading.Thread') as thread:
   self.mail.tick();self.assertEqual(thread.call_count,1);self.mail.running=False;self.mail.tick();self.assertEqual(thread.call_count,1)
  self.now+=timedelta(days=1);self.now=self.now.replace(hour=21);self.mail.save({'enabled':False});self.mail.save({'enabled':True})
  with patch('mail_digest.threading.Thread') as thread:self.mail.tick();self.assertEqual(thread.call_count,0)
 def test_success_and_uncertain(self):
  self.mail.save(self.config)
  with patch('mail_digest.threading.Thread'):entry=self.mail.start('test')
  self.mail.run(entry['id'],self.mail.config(),'test');self.assertEqual(self.mail.state()['history'][0]['status'],'sent');self.assertEqual(len(self.messages),1)
  with patch('mail_digest.threading.Thread'):entry=self.mail.start('manual')
  def broken(*args):raise TimeoutError('do not leak secret-test')
  self.mail.transport=broken;self.mail.run(entry['id'],self.mail.config(),'manual');self.assertEqual(self.mail.state()['history'][0]['status'],'uncertain');self.assertNotIn('secret-test',json.dumps(self.mail.public()))
 def test_discovery_date_dedup_and_escape(self):
  c=self.config|{'include_discovery':True,'keywords':['security'],'max_results':2}
  response=type('Response',(),{'raise_for_status':lambda s:None,'json':lambda s:{'results':[{'id':'https://openalex.org/W1','display_name':'<img onerror=alert(1)>','publication_date':'2026-11-04','doi':'javascript:alert(1)','authorships':[]},{'id':'https://openalex.org/W1','display_name':'duplicate'}]}})()
  with patch('mail_digest.requests.get',return_value=response) as get:
   items,errors=self.mail.discover(c,self.now,set());self.assertEqual(len(items),1);self.assertEqual(items[0]['url'],'');self.assertIn('from_publication_date:',get.call_args.kwargs['params']['filter']);self.assertFalse(errors)
   self.assertEqual(self.mail.discover(c,self.now,{'https://openalex.org/W1'})[0],[])
  digest=self.mail.build(self.config);digest['recommendations']=items;msg=self.mail.message(c,digest);html=msg.get_body(preferencelist=('html',)).get_content();self.assertIn('&lt;img',html);self.assertNotIn('<img onerror',html)
 def test_recovery(self):
  self.mail.save(self.config)
  with patch('mail_digest.threading.Thread'):self.mail.start('manual')
  self.mail.recover();self.assertEqual(self.mail.state()['history'][0]['status'],'uncertain')
 def test_pdf_attachment_and_network_failure(self):
  c=self.config|{'attach_pdf':True};digest=self.mail.build(c);message=self.mail.message(c,digest);attachments=list(message.iter_attachments());self.assertEqual(len(attachments),1);self.assertTrue(attachments[0].get_payload(decode=True).startswith(b'%PDF'))
  import requests
  with patch('mail_digest.requests.get',side_effect=requests.Timeout('secret-test')):
   papers,warnings=self.mail.discover(c,self.now,set());self.assertFalse(papers);self.assertTrue(warnings);self.assertNotIn('secret-test',str(warnings))
if __name__=='__main__':unittest.main()
