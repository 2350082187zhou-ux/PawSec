from paper_briefs import brief,keywords,excerpt
"""Local daily research digest. SMTP secrets are encrypted; schedules survive restarts."""
import copy, html, json, re, smtplib, ssl, threading, time, uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from urllib.parse import urlparse
import requests
from flask import Blueprint, request, jsonify
from pawsec_reports import Reports
from report_export import make_pdf

DEFAULTS={'enabled':False,'recipient':'','send_time':'20:00','reading_day':'yesterday','include_read':True,'include_discovery':True,
 'keywords':['network security','digital forensics','LLM security'],'lookback_days':30,'max_results':6,'attach_pdf':True,
 'smtp_host':'','smtp_port':465,'smtp_security':'ssl','smtp_user':'','sender':'','smtp_password':'','openalex_key':''}

def safe_url(value):
    value=str(value or '')
    try:return value if urlparse(value).scheme in ('https','http') else ''
    except ValueError:return ''

def email_address(value):
    return isinstance(value,str) and len(value)<=254 and bool(re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}',value))

class MailDigest:
    def __init__(self,m,clock=None,transport=None):
        self.m=m;self.clock=clock or (lambda:datetime.now().astimezone());self.transport=transport or self.smtp_send
        self.guard=threading.RLock();self.running=False
    def path(self,name):return Path(self.m.DATA)/name
    def config(self):
        f=self.path('mail_digest.enc')
        return copy.deepcopy(DEFAULTS)| (json.loads(self.m.cipher.decrypt(f.read_bytes())) if f.exists() else {})
    def state(self):
        f=self.path('mail_digest_state.json')
        return json.loads(f.read_text(encoding='utf-8')) if f.exists() else {'history':[],'seen':[]}
    def write_state(self,state):
        state['history']=state.get('history',[])[:100];state['seen']=state.get('seen',[])[-5000:];self.m.save(self.path('mail_digest_state.json'),state)
    def public(self):
        c=self.config();now=self.clock();due=now.replace(hour=int(c['send_time'][:2]),minute=int(c['send_time'][3:]),second=0,microsecond=0)
        if due<=now:due+=timedelta(days=1)
        return {k:v for k,v in c.items() if k not in ('smtp_password','openalex_key')}|{'has_password':bool(c['smtp_password']),'has_openalex_key':bool(c['openalex_key']),
         'timezone':now.tzname(),'local_time':now.isoformat(),'next_send':due.isoformat() if c['enabled'] else None,'running':self.running,'history':self.state()['history'][:20]}
    def validate(self,body,old):
        if not isinstance(body,dict):raise ValueError('设置格式无效。')
        c=copy.deepcopy(old)
        for key in ('enabled','include_read','include_discovery','attach_pdf'):
            if key in body:
                if not isinstance(body[key],bool):raise ValueError('开关值无效。')
                c[key]=body[key]
        for key in ('recipient','send_time','reading_day','smtp_host','smtp_security','smtp_user','sender'):
            if key in body:
                if not isinstance(body[key],str) or len(body[key])>254 or any(x in body[key] for x in '\r\n\x00'):raise ValueError('设置包含无效字符。')
                c[key]=body[key].strip()
        for key,low,high in [('smtp_port',1,65535),('lookback_days',1,365),('max_results',1,20)]:
            if key in body:
                n=body[key]
                if isinstance(n,bool) or not isinstance(n,int) or not low<=n<=high:raise ValueError('端口、检索天数或文章数量超出范围。')
                c[key]=n
        if 'keywords' in body:
            words=body['keywords']
            if not isinstance(words,list) or len(words)>5 or any(not isinstance(s,str) or not s.strip() or len(s)>160 for s in words):raise ValueError('关键词最多 5 组，每组 1 至 160 字。')
            c['keywords']=list(dict.fromkeys(s.strip() for s in words))
        for key in ('smtp_password','openalex_key'):
            if body.get(key):
                if not isinstance(body[key],str) or len(body[key])>4096:raise ValueError('密钥格式无效。')
                c[key]=body[key]
        if body.get('clear_password') is True:c['smtp_password']=''
        if body.get('clear_openalex_key') is True:c['openalex_key']=''
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',c['send_time']):raise ValueError('发送时间无效。')
        if c['reading_day'] not in ('today','yesterday'):raise ValueError('阅读日期无效。')
        if c['smtp_security'] not in ('ssl','starttls'):raise ValueError('请选择 SSL/TLS 或 STARTTLS。')
        if c['recipient'] and not email_address(c['recipient']):raise ValueError('收件邮箱格式无效。')
        if c['sender'] and not email_address(c['sender']):raise ValueError('发件邮箱格式无效。')
        if c['smtp_host'] and not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',c['smtp_host']):raise ValueError('SMTP 主机只填写域名，不含协议或路径。')
        if not c['include_read'] and not c['include_discovery']:raise ValueError('至少选择一种邮件内容。')
        if c['include_discovery'] and not c['keywords']:raise ValueError('请填写至少一组论文关键词。')
        if c['enabled']:self.ready(c)
        if c['enabled'] and (not old.get('enabled') or c['send_time']!=old.get('send_time')):c['enabled_at']=self.clock().timestamp()
        return c
    def ready(self,c):
        if not all([email_address(c['recipient']),email_address(c['sender']),c['smtp_host'],c['smtp_user'],c['smtp_password']]):raise ValueError('请先填写收件邮箱、发件邮箱、SMTP 主机、登录账号和授权码。')
    def save(self,body):
        with self.guard:
            if self.running:raise ValueError('邮件任务运行中，请完成后再修改设置。')
            c=self.validate(body,self.config());target=self.path('mail_digest.enc');temp=target.with_suffix('.tmp');temp.write_bytes(self.m.cipher.encrypt(json.dumps(c,ensure_ascii=False).encode('utf-8')));temp.replace(target)
            return self.public()
    def discover(self,c,now,seen):
        items={};errors=[];since=(now.date()-timedelta(days=c['lookback_days'])).isoformat()
        for query in c['keywords']:
            try:
                params={'search':query,'filter':'from_publication_date:'+since+',to_publication_date:'+now.date().isoformat(),'sort':'publication_date:desc','per-page':min(50,c['max_results']*3)}
                if c['openalex_key']:params['api_key']=c['openalex_key']
                r=requests.get('https://api.openalex.org/works',params=params,timeout=(10,30));r.raise_for_status()
                for x in r.json().get('results',[]):
                    identifier=str(x.get('id') or x.get('doi') or '')
                    if not identifier or identifier in seen or identifier in items:continue
                    items[identifier]={'id':identifier,'title':str(x.get('display_name') or 'Untitled'),'date':str(x.get('publication_date') or ''),
                     'authors':', '.join(str(a.get('author',{}).get('display_name','')) for a in x.get('authorships',[])[:4]),
                     'url':safe_url(x.get('doi') or (x.get('primary_location') or {}).get('landing_page_url') or identifier),
                     'abstract':self.m.abstract_text(x.get('abstract_inverted_index'))[:2000],'matched':query,'keywords':keywords(str(x.get('display_name') or ''),self.m.abstract_text(x.get('abstract_inverted_index')),x.get('keywords'))[0]}
            except (requests.RequestException,ValueError,TypeError):errors.append('关键词“'+query+'”检索失败；请检查网络或 OpenAlex API Key。')
        for item in items.values():item['brief']=brief(item)
        return sorted(items.values(),key=lambda x:x['date'],reverse=True)[:c['max_results']],errors
    def build(self,c=None):
        c=c or self.config();now=self.clock();day=(now-timedelta(days=c['reading_day']=='yesterday')).date().isoformat()
        report=Reports(self.m).build('day',day)
        report['entries']=[e for e in report['entries'] if e.get('read') or e.get('completed')]
        report['title']=day+' 已读论文简报';report['stats']['imported']=sum(e.get('imported',False) for e in report['entries'])
        report['overview']=f"{day} 有效阅读 {report['stats']['read']} 篇，读完 {report['stats']['completed']} 篇，累计记录阅读 {report['stats']['seconds']/60:.1f} 分钟。"
        if not c['include_read']:report['entries']=[]
        found,errors=self.discover(c,now,set(self.state()['seen'])) if c['include_discovery'] else ([],[])
        return {'created':now.isoformat(),'reading_date':day,'subject':'PawSec 研究简报 · '+now.date().isoformat(),'recipient':c['recipient'],
                'report':report,'papers':report['entries'],'recommendations':found,'warnings':errors,'include_read':c['include_read'],'include_discovery':c['include_discovery'],
                'note':'阅读小结优先采用已编辑或已生成的小结；未整理条目显示原文摘录。推荐论文仅依据公开元数据与摘要，尚未阅读。'}
    def message(self,c,digest):
        msg=EmailMessage();msg['Subject']=digest['subject'];msg['From']=c['sender'];msg['To']=c['recipient'];msg['Date']=formatdate(localtime=True);msg['Message-ID']=make_msgid(domain=c['sender'].split('@')[-1])
        esc=html.escape;plain=[digest['subject'],'',digest['note'],''];blocks=[]
        if c['include_read']:
            plain+=['已读论文 · '+digest['reading_date'],digest['report']['overview'],''];blocks += ['<h2>已读论文 · '+esc(digest['reading_date'])+'</h2><p>'+esc(digest['report']['overview'])+'</p>']
            if not digest['papers']:plain+=['该日暂无达到统计条件的阅读记录。'];blocks+=['<p>该日暂无达到统计条件的阅读记录。</p>']
            for p in digest['papers']:
                plain += [p['title'],p['summary'],'来源：'+p['summary_source'],'我的工作与收获：'+(p.get('reflection') or '未填写'),'']
                blocks += ['<article><h3>'+esc(p['title'])+'</h3><p>'+esc(p['summary']).replace('\n','<br>')+'</p><small>'+esc(p['summary_source'])+'</small>'+(('<p>我的工作与收获：'+esc(p['reflection'])+'</p>') if p.get('reflection') else '')+'</article>']
        if c['include_discovery']:
            plain+=['相关新论文（尚未阅读）',''];blocks+=['<h2>相关新论文</h2><p>按关键词检索 · 尚未阅读</p>']
            if not digest['recommendations']:plain+=['本次没有未发送的新论文。'];blocks+=['<p>本次没有未发送的新论文。</p>']
            for p in digest['recommendations']:
                abstract=p['abstract'] or '来源未提供摘要，请打开原文查看。';plain += [p['title'],p['date']+' · '+p['authors'],abstract,p['url'],'']
                blocks+=['<article><h3>'+esc(p['title'])+'</h3><small>'+esc(p['date']+' · '+p['authors'])+'</small><p>'+esc(abstract)+'</p>'+('<a href="'+esc(p['url'],quote=True)+'">查看论文来源 →</a>' if p['url'] else '')+'</article>']
        plain+=digest['warnings'];blocks+=['<p>'+esc(w)+'</p>' for w in digest['warnings']]
        plain+=['','在 PawSec 的“邮件订阅”页面关闭自动发送。定时任务按本机时区运行。']
        msg.set_content('\n'.join(plain));msg.add_alternative('<!doctype html><html><body style="margin:0;background:#f3f6ef;color:#243c36;font:15px/1.8 Arial,sans-serif"><main style="max-width:680px;margin:auto;padding:32px;background:white"><p style="color:#287b66;letter-spacing:2px">PAWSEC / RESEARCH DIGEST</p><h1>'+esc(digest['subject'])+'</h1>'+''.join(blocks)+'<p style="color:#68766c;font-size:12px">'+esc(digest['note'])+'</p><p style="font-size:12px">在本机 PawSec 的“邮件订阅”页面关闭自动发送。</p></main></body></html>',subtype='html')
        if c['attach_pdf'] and c['include_read']:msg.add_attachment(make_pdf(digest['report']),maintype='application',subtype='pdf',filename='PawSec-reading-'+digest['reading_date']+'.pdf')
        return msg
    def smtp_send(self,c,msg):
        context=ssl.create_default_context()
        if c['smtp_security']=='ssl':client=smtplib.SMTP_SSL(c['smtp_host'],c['smtp_port'],timeout=35,context=context)
        else:
            client=smtplib.SMTP(c['smtp_host'],c['smtp_port'],timeout=35)
            try:client.ehlo();client.starttls(context=context);client.ehlo()
            except Exception:client.close();raise
        try:
            client.login(c['smtp_user'],c['smtp_password']);refused=client.send_message(msg)
            if refused:raise smtplib.SMTPRecipientsRefused(refused)
        finally:
            # Once accepted, QUIT failure must not cause a duplicate resend.
            try:client.quit()
            except Exception:client.close()
    def record(self,identifier,**updates):
        with self.guard:
            s=self.state();entry=next(x for x in s['history'] if x['id']==identifier);entry.update(updates);self.write_state(s)
    def run(self,identifier,c,mode):
        sending=False
        try:
            digest=self.build(c);msg=self.message(c,digest)
            if mode=='test':msg.replace_header('Subject','[测试] '+digest['subject'])
            self.record(identifier,status='sending',message='正在提交邮件给 SMTP 服务');sending=True;self.transport(c,msg)
            with self.guard:
                s=self.state();entry=next(x for x in s['history'] if x['id']==identifier);entry.update(status='sent',message='SMTP 服务已接受邮件，请查看收件箱',finished=self.clock().isoformat(),warnings=digest['warnings'])
                if mode!='test':s['seen']=list(dict.fromkeys(s['seen']+[p['id'] for p in digest['recommendations']]))
                self.write_state(s)
        except Exception as e:
            if isinstance(e,smtplib.SMTPAuthenticationError):status='failed';message='SMTP 登录失败，请检查账号、授权码和服务是否开启。'
            elif isinstance(e,smtplib.SMTPRecipientsRefused):status='failed';message='SMTP 拒绝了收件地址，请检查邮箱。'
            elif sending:status='uncertain';message='发送连接中断，是否投递成功未知。请先查看收件箱；不会自动重试，避免重复邮件。'
            else:status='failed';message='简报准备失败，请检查论文数据、检索网络和设置后手动重试。'
            self.record(identifier,status=status,message=message,finished=self.clock().isoformat())
        finally:
            with self.guard:self.running=False
    def start(self,mode='manual',schedule_day=None):
        with self.guard:
            if self.running:raise ValueError('已有邮件任务运行中，请稍候。')
            c=self.config();self.ready(c);s=self.state()
            if schedule_day and any(x.get('schedule_day')==schedule_day for x in s['history']):return None
            identifier=uuid.uuid4().hex;entry={'id':identifier,'mode':mode,'recipient':c['recipient'],'status':'preparing','message':'正在整理阅读记录与检索论文','started':self.clock().isoformat(),'schedule_day':schedule_day}
            s['history'].insert(0,entry);self.write_state(s);self.running=True
            threading.Thread(target=self.run,args=(identifier,c,mode),daemon=True,name='mail-digest-send').start();return entry
    def tick(self):
        c=self.config();now=self.clock()
        if not c['enabled'] or self.running:return
        due=now.replace(hour=int(c['send_time'][:2]),minute=int(c['send_time'][3:]),second=0,microsecond=0)
        if now>=due and due.timestamp()>=c.get('enabled_at',0):self.start('scheduled',now.date().isoformat())
    def recover(self):
        with self.guard:
            s=self.state();changed=False
            for x in s['history']:
                if x['status'] in ('preparing','sending'):x.update(status='uncertain',message='上次任务因服务停止而中断，请检查收件箱后手动重试。');changed=True
            if changed:self.write_state(s)
    def worker(self):
        self.recover()
        while True:
            try:self.tick()
            except Exception:pass
            time.sleep(20)

def install(app,m):
    service=MailDigest(m);app.extensions['mail_digest']=service;bp=Blueprint('mail_digest',__name__)
    @bp.route('/api/mail/settings',methods=['GET','POST'])
    def settings():return jsonify(service.save(request.get_json()) if request.method=='POST' else service.public())
    @bp.post('/api/mail/preview')
    def preview():return jsonify(service.build())
    @bp.post('/api/mail/send')
    def send():
        mode=(request.get_json() or {}).get('mode','test')
        if mode not in ('test','manual'):raise ValueError('发送模式无效。')
        return jsonify(service.start(mode)),202
    app.register_blueprint(bp)
    app.extensions.setdefault('background_workers',[]).append(('mail-digest-scheduler',service.worker))
    if m.__name__=='__main__':threading.Thread(target=service.worker,daemon=True,name='mail-digest-scheduler').start()
