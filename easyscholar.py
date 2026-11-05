"""EasyScholar documented publication-rank API integration."""
import json,time,threading,hashlib
from datetime import datetime,timezone
import requests
from flask import request,jsonify
ENDPOINT='https://www.easyscholar.cc/open/getPublicationRank'
LABELS={'ccf':'CCF','sci':'JCR SCI 分区','ssci':'JCR SSCI 分区','sciif':'影响因子 IF','sciif5':'五年影响因子','sciUp':'中科院升级版分区','sciBase':'中科院基础版分区','sciUpSmall':'中科院小类分区','sciUpTop':'中科院 Top','jci':'JCI','sciwarn':'中科院预警','eii':'EI','cscd':'CSCD','pku':'北大核心','cssci':'CSSCI'}
def normalize(data):
    if not isinstance(data,dict) or not isinstance(data.get('officialRank'),dict):raise ValueError('EasyScholar 返回格式异常。')
    ranks=data['officialRank'].get('all',{})
    if not isinstance(ranks,dict):raise ValueError('EasyScholar 返回格式异常。')
    out=[{'field':k,'label':LABELS.get(k,k),'value':str(v),'kind':'official'} for k,v in ranks.items() if v is not None and v!='']
    custom=data.get('customRank') or {};infos={str(x.get('uuid')):x for x in custom.get('rankInfo',[]) if isinstance(x,dict)}
    for raw in custom.get('rank',[]):
        parts=str(raw).split('&&&')
        if len(parts)!=2 or parts[1] not in ['1','2','3','4','5']:continue
        row=infos.get(parts[0],{});v=row.get(['oneRankText','twoRankText','threeRankText','fourRankText','fiveRankText'][int(parts[1])-1])
        if v:out.append({'field':parts[0],'label':str(row.get('abbName',parts[0])),'value':str(v),'kind':'custom'})
    return out

def install(app,m):
    gate=threading.Lock();last=[0.0]
    def settings():
        p=m.DATA/'easyscholar.enc'
        return json.loads(m.cipher.decrypt(p.read_bytes())) if p.exists() else {}
    @app.route('/api/easyscholar/config',methods=['GET','POST'])
    def config():
        with m.lock:
            c=settings()
            if request.method=='POST':
                v=request.get_json() or {};key=v.get('key','')
                if not isinstance(key,str) or len(key)>512:raise ValueError('SecretKey 格式不正确。')
                if v.get('clear'):c={}
                elif key.strip():c['key']=key.strip()
                p=m.DATA/'easyscholar.enc';tmp=p.with_suffix('.tmp');tmp.write_bytes(m.cipher.encrypt(json.dumps(c).encode()));tmp.replace(p)
        return jsonify(configured=bool(c.get('key')),key_url='https://www.easyscholar.cc/console/user/open')
    def lookup(name,refresh=False):
        key=settings().get('key')
        if not key:raise ValueError('请先在 EasyScholar 设置中保存 SecretKey。')
        if not isinstance(name,str) or not name.strip() or len(name)>300:raise ValueError('请填写准确的期刊或会议名称（不是论文标题）。')
        name=name.strip();digest=hashlib.sha256((key+'\0'+name.casefold()).encode()).hexdigest();cache=m.DATA/'easyscholar-cache';cache.mkdir(exist_ok=True);path=cache/(digest+'.json')
        with gate:
            if not refresh and path.exists():
                saved=json.loads(path.read_text(encoding='utf-8'))
                if time.time()-saved['timestamp']<86400:return saved|{'cached':True}
            time.sleep(max(0,.55-(time.monotonic()-last[0])));last[0]=time.monotonic()
            try:
                r=requests.get(ENDPOINT,params={'secretKey':key,'publicationName':name},timeout=(10,25),allow_redirects=False)
                if r.status_code!=200:raise ValueError('EasyScholar 服务返回 HTTP '+str(r.status_code)+'。')
                result=r.json()
            except requests.RequestException:raise ValueError('EasyScholar 连接失败，请稍后重试。') from None
            except (json.JSONDecodeError,TypeError):raise ValueError('EasyScholar 返回格式异常。') from None
            if not isinstance(result,dict):raise ValueError('EasyScholar 返回格式异常。')
            if result.get('code')!=200:raise ValueError('EasyScholar 查询未成功（代码 '+str(result.get('code'))+'），请检查 SecretKey 或接口额度。')
            saved={'venue':name,'entries':normalize(result.get('data')),'source':'https://www.easyscholar.cc/console/user/open','queried_at':datetime.now(timezone.utc).isoformat(),'timestamp':time.time(),'data_year':None,'cached':False}
            m.save(path,saved);return saved
    @app.post('/api/easyscholar/query')
    def query():
        v=request.get_json() or {};return jsonify(lookup(v.get('venue'),v.get('refresh') is True))
    @app.route('/api/papers/<pid>/easyscholar',methods=['GET','POST'])
    def paper_ranks(pid):
        p=m.paper(pid)
        if request.method=='GET':return jsonify(venue=p.get('publication',{}).get('venue') or p.get('easyscholar',{}).get('venue',''),result=p.get('easyscholar'))
        v=request.get_json() or {};name=v.get('venue') or p.get('publication',{}).get('venue');result=lookup(name,v.get('refresh') is True)
        with m.lock:p=m.paper(pid);p['easyscholar']=result;m.put(p)
        return jsonify(result)