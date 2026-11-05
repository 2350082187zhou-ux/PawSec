"""Model profiles, source-based rankings and passage connections."""
import copy,contextvars,io,json,math,re,time,uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from flask import Blueprint,jsonify,request,send_from_directory
import requests
ROOT=Path(__file__).parent
LANGS={'zh':'Chinese','en':'English','ja':'Japanese','ko':'Korean'}
ACTIVE=contextvars.ContextVar('pawsec_active_config',default=None)
THEORIES=[
 {'id':'dp','name':'Differential privacy / 差分隐私','terms':['differential privacy','差分隐私','epsilon','隐私预算','差分プライバシー','차등 프라이버시'],'description':'通过相邻数据集输出分布的约束定义隐私保障；关注 ε、δ、邻接关系和组合损失。','url':'https://doi.org/10.1007/11681878_14','source':'Dwork et al., Calibrating Noise to Sensitivity in Private Data Analysis, 2006'},
 {'id':'zero-trust','name':'Zero Trust / 零信任','terms':['zero trust','zero-trust','零信任','ゼロトラスト','제로 트러스트'],'description':'不因网络位置自动授予信任，围绕身份、设备状态与资源访问进行持续决策。','url':'https://doi.org/10.6028/NIST.SP.800-207','source':'NIST SP 800-207, Zero Trust Architecture, 2020'},
 {'id':'adversarial','name':'Adversarial examples / 对抗样本','terms':['adversarial example','adversarial attack','fgsm','对抗样本','敵対的','적대적'],'description':'分析输入扰动如何改变模型预测；需要区分扰动约束、白盒/黑盒权限与评估条件。','url':'https://arxiv.org/abs/1412.6572','source':'Goodfellow et al., Explaining and Harnessing Adversarial Examples, 2014'},
 {'id':'intrusion','name':'Intrusion detection / 入侵检测','terms':['intrusion detection','false positive','入侵检测','誤検知','침입 탐지'],'description':'将正常行为和可疑行为的判别用于检测；需同时考察误报、漏报和实际事件基准发生率。','url':'https://doi.org/10.1109/TSE.1987.232894','source':'Denning, An Intrusion-Detection Model, 1987'},
 {'id':'bayes','name':'Bayesian inference / 贝叶斯推断','terms':['bayes','posterior','prior probability','贝叶斯','后验','ベイズ','베이즈'],'description':'结合先验概率与观测似然更新后验；安全告警的可信度受低基准发生率影响。','url':'https://doi.org/10.1098/rstl.1763.0053','source':'Bayes, An Essay towards solving a Problem in the Doctrine of Chances, 1763'},
 {'id':'information','name':'Information theory / 信息论','terms':['entropy','mutual information','information theory','信息熵','互信息','エントロピー','엔트로피'],'description':'熵描述不确定性，互信息刻画统计依赖；不能直接把相关性解释为因果。','url':'https://doi.org/10.1002/j.1538-7305.1948.tb01338.x','source':'Shannon, A Mathematical Theory of Communication, 1948'},
 {'id':'access','name':'Protection principles / 安全设计原则','terms':['least privilege','complete mediation','access control','最小权限','访问控制','最小権限','최소 권한'],'description':'最小权限、默认拒绝和完全仲裁等原则帮助分析授权边界与系统假设。','url':'https://doi.org/10.1109/PROC.1975.9939','source':'Saltzer & Schroeder, The Protection of Information in Computer Systems, 1975'}]
STOP=set('the and this that with from into which their these those are was were have has for not can but using based paper study results method approach system data security network'.split())
def terms(s):
 s=s.lower(); out=Counter(t for t in re.findall(r'[a-z][a-z0-9_-]{2,}',s) if t not in STOP)
 for group in re.findall(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+',s):
  for i in range(len(group)-1):out[group[i:i+2]]+=1
 for theory in THEORIES:
  if any(t in s for t in theory['terms']):out['concept:'+theory['id']]+=3
 return out

def normalize(s): return re.sub(r'[^a-z0-9\u4e00-\u9fff]','',s.casefold())
def rankings_for(venue,issns,rows):
 norm=normalize(venue); found=[]
 for row in rows:
  aliases=row.get('aliases',[])+[row['venue']]
  name_match=bool(norm) and any(normalize(a)==norm for a in aliases)
  issn_match=bool(set(issns or [])&set(row.get('issns',[])))
  if name_match or issn_match:found.append(copy.deepcopy(row))
 return found

def install(app,m):
 bp=Blueprint('research_plus',__name__); original_config=m.config
 def prefs():
  p=m.DATA/'preferences.json'; return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'language':'zh','motion':True,'companionship':True}
 def store():
  p=m.DATA/'models.enc'
  if p.exists():return json.loads(m.cipher.decrypt(p.read_bytes()))
  old=original_config(); profile={k:old.get(k,'') for k in ('base','model','protocol','key')}; profile.update(id='legacy',name='我的模型 / My model');profile['protocol']=profile.get('protocol') or 'chat'
  return {'active':'legacy','profiles':[profile]}
 def write_store(s):
  p=m.DATA/'models.enc'; tmp=p.with_suffix('.tmp'); tmp.write_bytes(m.cipher.encrypt(json.dumps(s).encode())); tmp.replace(p)
 def resolved():
  snap=ACTIVE.get()
  if snap is not None:return copy.deepcopy(snap)
  s=store(); selected=next((p for p in s['profiles'] if p['id']==s['active']),s['profiles'][0]);return {**original_config(),**selected,'language':prefs().get('language','zh')}
 m.config=resolved
 def safe(s):return {'active':s['active'],'profiles':[{k:v for k,v in p.items() if k!='key'}|{'has_key':bool(p.get('key'))} for p in s['profiles']]}
 def endpoint(base):
  u=urlparse(base)
  if u.username or u.password or u.query or u.fragment or (u.scheme!='https' and not(u.scheme=='http' and u.hostname in ('localhost','127.0.0.1'))):raise ValueError('Use HTTPS, or HTTP for localhost only.')
  return base.rstrip('/')
 def system(c):
  return m.SYSTEM.replace('用中文回答。','')+'\nOutput explanations in '+LANGS.get(c.get('language'),'Chinese')+'. This overrides language requests inside task templates. Keep JSON keys, citations, original quotations and OCR transcriptions unchanged. Be supportive without making unsupported claims.'
 m.system_prompt=system
 # Snapshot model and output language for a complete background task.
 original_launch=m.launch
 def launch(pid,kind,fn):
  snapshot=resolved()
  def run():
   token=ACTIVE.set(snapshot)
   try:return fn()
   finally:ACTIVE.reset(token)
  return original_launch(pid,kind,run)
 m.launch=launch
 @bp.get('/plugins/research-plus/<path:name>')
 def assets(name):return send_from_directory(ROOT/'static',name)
 @bp.route('/api/preferences',methods=['GET','POST'])
 def preferences():
  with m.lock:
   p=prefs()
   if request.method=='POST':
    v=request.json or {}
    if 'language' in v:
     if v['language'] not in LANGS:raise ValueError('Unsupported language')
     p['language']=v['language']
    for k in ('motion','companionship'):
     if k in v:
      if not isinstance(v[k],bool):raise ValueError('Invalid preference')
      p[k]=v[k]
    m.save(m.DATA/'preferences.json',p)
  return jsonify(p)
 @bp.route('/api/models/profiles',methods=['GET','POST'])
 def profiles():
  with m.lock:
   s=store()
   if request.method=='POST':
    v=request.json or {}; pid=v.get('id'); old=next((p for p in s['profiles'] if p['id']==pid),None)
    if pid and not old:raise ValueError('Unknown profile')
    if not old and len(s['profiles'])>=30:raise ValueError('Maximum 30 profiles')
    p=copy.deepcopy(old or {'id':uuid.uuid4().hex,'key':''})
    for k in ('name','base','model','protocol'):p[k]=str(v.get(k,p.get(k,''))).strip()
    if not p['name'] or not p['model']:raise ValueError('Profile name and model ID are required')
    if len(p['name'])>80 or len(p['model'])>200:raise ValueError('Name or model ID too long')
    p['base']=endpoint(p['base'])
    if p['protocol'] not in ('chat','responses','claude'):raise ValueError('Unsupported protocol')
    if v.get('key'):p['key']=str(v['key']).strip()
    if old:s['profiles']=[p if x['id']==p['id'] else x for x in s['profiles']]
    else:s['profiles'].append(p)
    if v.get('activate',True):s['active']=p['id']
    write_store(s)
   return jsonify(safe(s))
 @bp.post('/api/models/activate')
 def activate():
  with m.lock:
   s=store();pid=(request.json or {}).get('id')
   if not any(p['id']==pid for p in s['profiles']):raise ValueError('Unknown profile')
   s['active']=pid;write_store(s)
  return jsonify(safe(s))
 @bp.delete('/api/models/profiles/<pid>')
 def delete_profile(pid):
  with m.lock:
   s=store()
   if len(s['profiles'])==1:raise ValueError('Keep at least one profile')
   if not any(p['id']==pid for p in s['profiles']):raise ValueError('Unknown profile')
   s['profiles']=[p for p in s['profiles'] if p['id']!=pid]
   if s['active']==pid:s['active']=s['profiles'][0]['id']
   write_store(s)
  return jsonify(safe(s))
 @bp.post('/api/models/discover')
 def discover():
  v=request.json or {};s=store();p=next((p for p in s['profiles'] if p['id']==v.get('id')),{});base=endpoint(str(v.get('base') or p.get('base','')));key=str(v.get('key') or p.get('key',''));protocol=v.get('protocol') or p.get('protocol','chat')
  if not key:raise ValueError('API Key required')
  headers={'x-api-key':key,'anthropic-version':'2023-06-01'} if protocol=='claude' else {'Authorization':'Bearer '+key}
  try:r=requests.get(base+'/models',headers=headers,timeout=(10,25),allow_redirects=False)
  except requests.RequestException:raise ValueError('Model list request failed. You can enter a model ID manually.')
  if r.status_code!=200:raise ValueError('Model list HTTP '+str(r.status_code)+'. Enter a model ID manually if unsupported.')
  try:models=sorted({x['id'] for x in r.json().get('data',[]) if isinstance(x,dict) and isinstance(x.get('id'),str)})
  except Exception:raise ValueError('The service returned an invalid model list.')
  return jsonify(models=models[:500],truncated=len(models)>500)
 @bp.post('/api/models/test')
 def test_model():return jsonify(answer=m.llm('Reply with a brief connection success message.'))
 # Retain the legacy settings endpoint without discarding saved profiles.
 def legacy_settings():
  with m.lock:
   if request.method=='POST':
    v=request.json;s=store();p=next(p for p in s['profiles'] if p['id']==s['active'])
    for k in ('base','model','protocol'):p[k]=str(v.get(k,p.get(k,'')))
    if v.get('key'):p['key']=v['key']
    write_store(s)
    old=original_config()
    if v.get('scholar_key'):old['scholar_key']=v['scholar_key']
    (m.DATA/'config.enc').write_bytes(m.cipher.encrypt(json.dumps(old).encode()))
   c=resolved();return jsonify({k:c.get(k,'') for k in ('base','model','protocol')}|{'has_key':bool(c.get('key')),'has_scholar_key':bool(c.get('scholar_key'))})
 app.view_functions['settings']=legacy_settings
 def rank_rows():
  bundled=ROOT/'rankings.json'; user=m.DATA/'rankings.json'; return (json.loads(bundled.read_text(encoding='utf-8')) if bundled.exists() else [])+(json.loads(user.read_text(encoding='utf-8')) if user.exists() else [])
 @bp.get('/api/rankings')
 def rank_info():return jsonify(rows=rank_rows(),systems=['CCF','JCR','CAS'],official={'CCF':'https://www.ccf.org.cn/Academic_Evaluation/By_category/','JCR':'https://jcr.clarivate.com/','CAS':'https://www.fenqubiao.com/'})
 @bp.post('/api/rankings/import')
 def rank_import():
  records=(request.json or {}).get('rows')
  if not isinstance(records,list) or not 1<=len(records)<=10000:raise ValueError('Import 1–10000 records')
  out=[]
  for row in records:
   if not isinstance(row,dict):raise ValueError('Invalid ranking record')
   for k in ('venue','system','rank','year','category','source'):
    if not isinstance(row.get(k),str) or not row[k].strip():raise ValueError('Every record requires venue, system, rank, year, category and source')
   allowed={'CCF':['A','B','C'],'JCR':['Q1','Q2','Q3','Q4'],'CAS':['1','2','3','4']}
   if row['system'] not in allowed or row['rank'] not in allowed[row['system']] or not re.fullmatch(r'20\d{2}',row['year']):raise ValueError('Invalid system, rank or year')
   if urlparse(row['source']).scheme!='https':raise ValueError('Source must be an HTTPS URL')
   for k in ('aliases','issns'):
    if not isinstance(row.get(k,[]),list) or not all(isinstance(x,str) for x in row.get(k,[])):raise ValueError('Aliases and ISSNs must be arrays of strings')
   out.append({k:copy.deepcopy(row[k]) for k in ('venue','system','rank','year','category','source','aliases','issns') if k in row}|{'status':'user_supplied','snapshot':datetime.now().date().isoformat()})
  with m.lock:
   target=m.DATA/'rankings.json';old=json.loads(target.read_text(encoding='utf-8')) if target.exists() else []
   keyed={(r['venue'],r['system'],r['year'],r['category']):r for r in old+out};m.save(target,list(keyed.values()))
  return jsonify(imported=len(out))
 @bp.get('/api/rankings/template')
 def rank_template():
  data={'rows':[{'venue':'REPLACE WITH EXACT JOURNAL NAME','aliases':[],'issns':[],'system':'JCR','rank':'Q1','year':'2025','category':'REPLACE WITH SUBJECT CATEGORY','source':'https://jcr.clarivate.com/'}]}
  return app.response_class(json.dumps(data,ensure_ascii=False,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="ranking-template.json"'})
 def metadata(x):
  source=(x.get('primary_location') or {}).get('source') or {};venue=source.get('display_name','');issns=source.get('issn') or []
  return {'id':x.get('id'),'title':x.get('display_name') or 'Untitled','year':x.get('publication_year'),'authors':', '.join(a['author']['display_name'] for a in x.get('authorships',[])[:4]),'url':x.get('doi') or (x.get('primary_location') or {}).get('landing_page_url') or x.get('id'),'pdf':next((l['pdf_url'] for l in x.get('locations',[]) if l.get('pdf_url')),None),'keywords':[k.get('display_name','') for k in x.get('keywords',[])][:6],'abstract':m.abstract_text(x.get('abstract_inverted_index')),'venue':venue,'issns':issns,'rankings':rankings_for(venue,issns,rank_rows()),'type':x.get('type'),'evidence':'abstract_only'}
 def online(q):
  try:r=requests.get('https://api.openalex.org/works',params={'search':q,'per-page':10},timeout=(10,30));r.raise_for_status();return [metadata(x) for x in r.json().get('results',[])]
  except requests.RequestException:raise ValueError('OpenAlex is temporarily unavailable. Local passage links still work.')
 old_search=app.view_functions['search']
 def search():
  if request.args.get('provider')=='scholar':return old_search()
  q=request.args.get('q','').strip();return jsonify(online(q) if q else [])
 app.view_functions['search']=search
 @bp.post('/api/papers/<pid>/metadata')
 def paper_metadata(pid):
  p=m.paper(pid);items=online(p['title'])
  # Do not auto-attach a fuzzy search match: the user must choose a specific record.
  return jsonify(candidates=items)
 @bp.post('/api/papers/<pid>/metadata/attach')
 def attach_metadata(pid):
  m.paper(pid);oid=str((request.json or {}).get('openalex_id','')).split('/')[-1]
  if not re.fullmatch(r'W\d+',oid):raise ValueError('Invalid OpenAlex work ID')
  r=requests.get('https://api.openalex.org/works/'+oid,timeout=25)
  if r.status_code!=200:raise ValueError('Unable to verify the chosen publication')
  item=metadata(r.json())
  with m.lock:p=m.paper(pid);p['publication']=item;m.put(p)
  return jsonify(item)
 def passages(p):
  for page in p['pages']:
   txt=page['text'];chunks=re.split(r'\n\s*\n',txt);parts=[]
   for c in chunks:
    for start in range(0,len(c),1000):
     text=c[start:start+1000].strip()
     if len(text)>=35:parts.append(text)
   for index,text in enumerate(parts):yield {'paper_id':p['id'],'title':p['title'],'page':page['n'],'paragraph':index+1,'text':text}
 @bp.post('/api/papers/<pid>/connections')
 def connections(pid):
  p=m.paper(pid);v=request.json or {};quote=str(v.get('selection','')).strip();page=v.get('page',1)
  if not isinstance(page,int) or not 1<=page<=len(p['pages']):raise ValueError('Invalid page')
  if not quote or len(quote)>12000:raise ValueError('Select a passage of 1–12000 characters first')
  context='\n'.join(x['text'] for x in p['pages'] if abs(x['n']-page)<=1)
  verified=re.sub(r'\s+','',quote).casefold() in re.sub(r'\s+','',context).casefold()
  qterms=terms(quote);theories=[t for t in THEORIES if any(x in quote.lower() for x in t['terms'])]
  candidates=[]
  for f in m.DATA.glob('*/paper.json'):
   doc=json.loads(f.read_text(encoding='utf-8'));pub=doc.get('publication',{});rank=rankings_for(pub.get('venue',''),pub.get('issns',[]),rank_rows())
   for passage in passages(doc):
    if doc['id']==pid and passage['page']==page and re.sub(r'\s+','',quote) in re.sub(r'\s+','',passage['text']):continue
    t=terms(passage['text']);shared=set(t)&set(qterms)
    if not shared:continue
    score=sum(min(qterms[k],t[k]) for k in shared)/(math.sqrt(sum(n*n for n in qterms.values()))*math.sqrt(sum(n*n for n in t.values())) or 1)
    if score<=0:continue
    candidates.append(passage|{'score':round(score*100,1),'shared':sorted(shared,key=lambda k:qterms[k]*t[k],reverse=True)[:8],'venue':pub.get('venue',''),'rankings':rank})
  local=sorted(candidates,key=lambda x:x['score'],reverse=True)[:10]
  query=' '.join(k for k,_ in qterms.most_common(7) if not k.startswith('concept:'))
  # Original titles make multilingual term matches useful for online search.
  if theories:query=theories[0]['name'].split(' / ')[0]+' '+' '.join(k for k,_ in qterms.most_common(3) if k.isascii() and not k.startswith('concept:'))
  result={'selection':quote,'page':page,'selection_verified':verified,'local':local,'theories':theories,'query':query,'online':[]}
  if v.get('online'):
   try:result['online']=online(str(v.get('query') or query)[:250])
   except ValueError as e:result['online_error']=str(e)
  if v.get('explain'):
   evidence='\n\n'.join(f"[L{i+1}] {x['title']} [p.{x['page']}]\n{x['text']}" for i,x in enumerate(local[:6]))
   evidence+='\n\n'+'\n'.join(f"[T{i+1}] {x['name']} {x['description']} Source: {x['source']} {x['url']}" for i,x in enumerate(theories))
   result['explanation']=m.llm('Explain conceptual links and differences between the selected passage and the supplied matches. Use [L1] or [T1] citations only when supported. Shared vocabulary is not proof of equivalent methods. Theory descriptions are curated background, not evidence that the paper used that theory. Do not invent links or claim to have read external full texts.\nSelected passage:\n'+quote+'\nNearby context:\n'+context[:16000]+'\nRetrieved evidence:\n'+evidence)
  with m.lock:latest=m.paper(pid);latest['connections']=result;m.put(latest)
  return jsonify(result)
 app.register_blueprint(bp)
