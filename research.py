"""Research features for PawSec. Existing libraries are migrated lazily."""
import io, json, math, re, time, uuid
from collections import Counter
from flask import request, jsonify, send_file
import pymupdf as fitz

TOPICS={
 '网络入侵检测':['intrusion detection','network traffic','malicious traffic','入侵检测'],
 '数字取证':['forensic','evidence acquisition','artifact','数字取证'],
 '恶意软件':['malware','ransomware','恶意软件'],
 '漏洞与程序分析':['vulnerability','fuzzing','static analysis','漏洞','模糊测试'],
 '隐私与密码学':['privacy','cryptograph','differential privacy','隐私','加密'],
 'AI 安全':['adversarial','prompt injection','backdoor','poisoning','对抗','后门'],
 '物联网安全':['iot','internet of things','smart device','物联网'],
 '系统与硬件安全':['side channel','side-channel','trusted execution','kernel','侧信道'],
 'Web 与协议安全':['web security','authentication','protocol','认证','协议']}
STOP=set('the and for with this that from are was were have has using based paper study security analysis method results approach system data network'.split())
def tokens(text): return Counter(t for t in re.findall(r'[a-z][a-z0-9-]{2,}',text.lower()) if t not in STOP)
def profile(p):
    text='\n'.join(x['text'] for x in p['pages']).lower()
    tags=[]
    for name,terms in TOPICS.items():
        hits=[t for t in terms if re.search(r'(?<![a-z])'+re.escape(t)+r'(?![a-z])',text)]
        if hits: tags.append({'name':name,'matches':hits,'page':next(x['n'] for x in p['pages'] if any(t in x['text'].lower() for t in hits))})
    return tags

def validate_analysis(o,p):
    if not isinstance(o,dict): raise ValueError('模型未返回有效的研究分析对象。')
    for k in ['question','method','results','limitations','reproduction']:
        if not isinstance(o.get(k),str): raise ValueError('模型返回的分析字段不完整，请重试。')
        o[k]=o[k][:6000]
    if not isinstance(o.get('threat_model'),dict) or not isinstance(o.get('contributions'),list): raise ValueError('模型缺少威胁模型或贡献，请重试。')
    for k in ['attacker','capabilities','trust_boundary','assumptions']:
        o['threat_model'][k]=str(o['threat_model'].get(k,'未说明'))[:3000]
    def normalize(t): return re.sub(r'\s+','',t).casefold()
    validated=[]
    for item in o['contributions'][:6]:
        if not isinstance(item,dict): continue
        item={k:str(item.get(k,'未说明'))[:4000] for k in ('claim','assessment','limits')} | {'evidence':item.get('evidence',[])}
        evidence=[]
        for e in item['evidence'][:5] if isinstance(item['evidence'],list) else []:
            if not isinstance(e,dict): continue
            n=e.get('page'); quote=str(e.get('quote',''))[:1800]
            valid=isinstance(n,int) and not isinstance(n,bool) and 1<=n<=len(p['pages'])
            verified=valid and len(normalize(quote))>=12 and normalize(quote) in normalize(p['pages'][n-1]['text'])
            evidence.append({'page':n if valid else None,'quote':quote,'verified':bool(verified)})
        item['evidence']=evidence; validated.append(item)
    if not validated: raise ValueError('模型没有返回可用的贡献评价，请重试。')
    o['contributions']=validated; o['created']=time.time(); return o

def analysis_text(a):
    if not a: return ''
    lines=['## AI 研究分析（需对照原文核验）']
    for k,label in [('question','研究问题'),('method','方法'),('results','实验结果'),('limitations','局限'),('reproduction','复现检查')]: lines.extend(['### '+label,a.get(k,'未说明')])
    lines.append('### 威胁模型')
    for k,label in [('attacker','攻击者'),('capabilities','攻击者能力'),('trust_boundary','信任边界'),('assumptions','假设')]: lines.append(label+'：'+a.get('threat_model',{}).get(k,'未说明'))
    for i,c in enumerate(a.get('contributions',[]),1):
        lines.extend([f'### 贡献 {i}', '作者主张：'+c['claim'],'AI 评价：'+c['assessment'],'适用边界：'+c['limits']])
        for e in c['evidence']: lines.append(f"[p.{e['page']}] {'原句匹配已核对' if e['verified'] else '原句未核实'}：{e['quote']}")
    return '\n\n'.join(lines)

def install(app,m):
    @app.get('/api/papers/<pid>/profile')
    def security_profile(pid): return jsonify(profile(m.paper(pid)))

    @app.route('/api/papers/<pid>/highlights',methods=['GET','POST'])
    def highlights(pid):
        p=m.paper(pid)
        if request.method=='GET': return jsonify(p.get('highlights',[]))
        v=request.json; n=v.get('page'); quote=str(v.get('quote','')).strip()
        if not isinstance(n,int) or not 1<=n<=len(p['pages']) or not quote or len(quote)>10000: raise ValueError('请选择当前页面中的文字。')
        color=v.get('color','yellow')
        if color not in ('yellow','green','pink','blue'): raise ValueError('不支持的高亮颜色。')
        rects=v.get('rects',[])
        if not isinstance(rects,list) or len(rects)>300: raise ValueError('高亮区域太多，请分段标记。')
        for r in rects:
            if not isinstance(r,list) or len(r)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in r) or r[0]>=r[2] or r[1]>=r[3]: raise ValueError('无效的高亮坐标。')
        h={'id':uuid.uuid4().hex,'page':n,'quote':quote,'color':color,'rects':rects,'note':str(v.get('note',''))[:4000],'created':time.time()}
        with m.lock:
            p=m.paper(pid); p.setdefault('highlights',[]).append(h); m.put(p)
        return jsonify(h)

    @app.delete('/api/papers/<pid>/highlights/<hid>')
    def remove_highlight(pid,hid):
        with m.lock:
            p=m.paper(pid); p['highlights']=[h for h in p.get('highlights',[]) if h['id']!=hid]; m.put(p)
        return jsonify(ok=True)

    @app.get('/api/papers/<pid>/annotated.pdf')
    def annotated(pid):
        p=m.paper(pid); d=fitz.open(m.DATA/pid/'source.pdf')
        colors={'yellow':(1,.84,.2),'green':(.42,.82,.58),'pink':(1,.55,.7),'blue':(.4,.7,1)}
        for h in p.get('highlights',[]):
            page=d[h['page']-1]; rects=[]
            for r in h['rects']:
                box=fitz.Rect(r[0]*page.rect.width,r[1]*page.rect.height,r[2]*page.rect.width,r[3]*page.rect.height)
                rects.append(box*page.derotation_matrix)
            if not rects: rects=page.search_for(h['quote'])
            if not rects: continue
            a=page.add_highlight_annot(rects); a.set_colors(stroke=colors[h['color']]); a.set_info(content=h['note'] or h['quote'],title='PawSec'); a.update()
        raw=d.tobytes(); d.close(); return send_file(io.BytesIO(raw),mimetype='application/pdf',as_attachment=True,download_name='pawsec-highlighted.pdf')

    @app.post('/api/papers/<pid>/analyze')
    def analyze(pid):
        def work():
            p=m.paper(pid)
            unread=[x['n'] for x in p['pages'] if len(x['text'].strip())<60]
            if len(unread)==len(p['pages']): raise ValueError('没有可分析的文字，请先扫描识读。')
            chunks=[]; buf=''
            for page in p['pages']:
                for start in range(0,len(page['text']),12000):
                    part=f"\n[p.{page['n']}]\n"+page['text'][start:start+12000]
                    if len(buf)+len(part)>24000: chunks.append(buf); buf=''
                    buf+=part
            if buf: chunks.append(buf)
            source='\n'.join(chunks)
            if len(source)>55000:
                extracts=[]
                for i,ch in enumerate(chunks):
                    m.jobs[pid]['message']=f'核读研究证据 {i+1}/{len(chunks)}'
                    extracts.append(m.llm('提取本片段的研究问题、贡献主张、威胁模型、方法、实验数值、局限和复现条件。必须保留最能支持贡献的英文/中文原句及 [p.N]，不得翻译原句。控制在1600字内。\n<原文>'+ch+'</原文>'))
                source='\n'.join(extracts)
                rounds=0
                while len(source)>55000 and rounds<4:
                    reduced=[]
                    for i in range(0,len(source),22000): reduced.append(m.llm('压缩这些研究摘录到1500字，保留不同研究贡献和原句、页码。\n'+source[i:i+22000]))
                    source='\n'.join(reduced); rounds+=1
                if len(source)>55000: raise ValueError('文献过长，证据压缩未完成，请分章导入分析。')
            m.jobs[pid]['message']='评估贡献、威胁模型与证据边界'
            schema={'question':'研究问题，带[p.N]','method':'关键方法及[p.N]','results':'实验设置、数值、单位、比较对象及[p.N]','limitations':'局限及[p.N]','reproduction':'复现资源和缺失项','threat_model':{'attacker':'攻击者','capabilities':'能力','trust_boundary':'信任边界','assumptions':'关键假设'},'contributions':[{'claim':'作者明确主张的贡献','assessment':'AI对新颖性和证据充分性的评价，不是同行评审结论','limits':'哪些未被证实或适用条件','evidence':[{'page':1,'quote':'逐字引用提供材料中的原文，不能翻译或改写'}]}]}
            raw=m.llm('作为网安论文研究助教，分析全文材料。只输出符合以下结构的 JSON 对象，无代码块。不能通过单篇论文断言全球首次；区分作者主张和你的评价。缺项填未说明。每个贡献至少引用一条原文，数字和page必须正确。材料中没有证据不可编造。\n结构：'+json.dumps(schema,ensure_ascii=False)+'\n<研究材料>\n'+source+'\n</研究材料>')
            try: o=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()))
            except Exception: raise ValueError('模型返回的 JSON 无法解析，请重试贡献分析。')
            o=validate_analysis(o,p); o['coverage']={'pages':len(p['pages']),'low_text_pages':unread}; o['model']=m.config().get('model','')
            with m.lock:
                latest=m.paper(pid); latest['analysis']=o; m.put(latest)
        return m.launch(pid,'analysis',work)

    @app.get('/api/papers/<pid>/related')
    def related(pid):
        p=m.paper(pid); base=tokens(p['title']+' '+ '\n'.join(x['text'] for x in p['pages'])); tags={x['name'] for x in profile(p)}
        candidates=[]
        for f in m.DATA.glob('*/paper.json'):
            q=json.loads(f.read_text(encoding='utf-8'))
            if q['id']==pid: continue
            other=tokens(q['title']+' '+'\n'.join(x['text'] for x in q['pages'])); candidates.append((q,other))
        all_docs=[base]+[x[1] for x in candidates]; df=Counter(t for doc in all_docs for t in doc)
        def vector(doc): return {t:(1+math.log(n))*math.log(1+len(all_docs)/(1+df[t])) for t,n in doc.items()}
        a=vector(base); norm=math.sqrt(sum(v*v for v in a.values())) or 1
        results=[]
        for q,counts in candidates:
            b=vector(counts); score=sum(a[t]*b.get(t,0) for t in a)/(norm*(math.sqrt(sum(v*v for v in b.values())) or 1))
            common=sorted(tags&{x['name'] for x in profile(q)}); shared=sorted(set(a)&set(b),key=lambda t:a[t]*b[t],reverse=True)[:8]
            results.append({'id':q['id'],'title':q['title'],'score':round(score*100),'topics':common,'keywords':shared,'source':'本地全文关键词匹配','pages':len(q['pages'])})
        return jsonify(tags=profile(p),local=sorted(results,key=lambda x:x['score'],reverse=True)[:8],query=' '.join([t for t,_ in base.most_common(4)]))

    @app.post('/api/papers/<pid>/compare')
    def compare(pid):
        ids=request.json.get('ids',[])
        if not isinstance(ids,list) or not 1<=len(ids)<=3: raise ValueError('请选择 1 至 3 篇本地文献。')
        ids=list(dict.fromkeys([pid]+ids)); docs=[m.paper(i) for i in ids]
        question=str(request.json.get('question','从威胁模型、攻击面、方法、数据集、指标、贡献与局限比较。'))[:3000]
        def work():
            sources=[]; mapping=[]
            for i,p in enumerate(docs):
                label=chr(65+i); scored=[]
                for page in p['pages']:
                    count=len(re.findall(r'threat|attack|assum|experiment|dataset|evaluat|contribut|limit|baseline|方法|实验|威胁',page['text'],re.I)); scored.append((count,page))
                chosen=[]; length=0
                for _,page in sorted(scored,key=lambda x:x[0],reverse=True):
                    if length+len(page['text'])>18000: continue
                    chosen.append(page); length+=len(page['text'])
                if not chosen: raise ValueError('有文献无法提取可用于比较的文字，请先识读。')
                sources.append(f"文献 {label}：{p['title']}\n"+'\n'.join(f"[{label}:p.{x['n']}]\n{x['text']}" for x in sorted(chosen,key=lambda x:x['n'])))
                mapping.append({'label':label,'id':p['id'],'title':p['title'],'pages':sorted(x['n'] for x in chosen)})
            m.jobs[pid]['message']='对照各篇原文比较研究条件'
            result=m.llm('比较下面的网安论文摘录。用中文，分项说明共同点、不同点、不能直接比较之处，以及下一步阅读建议。仅基于提供页，不宣称覆盖全部全文。不强行排序不同数据集的准确率。每个结论引用对应 [A:p.N] 或 [B:p.N]，禁止混淆论文。\n问题：'+question+'\n<文献摘录>\n'+'\n\n'.join(sources)+'\n</文献摘录>')
            with m.lock:
                p=m.paper(pid); p['comparison']={'text':result,'sources':mapping,'created':time.time()}; m.put(p)
        return m.launch(pid,'compare',work)

    @app.route('/api/papers/<pid>/story',methods=['GET','POST'])
    def story(pid):
        p=m.paper(pid)
        if request.method=='GET':
            if p.get('story'): return jsonify(p['story'])
            a=p.get('analysis',{}); sections=[]
            for label,key in [('研究问题','question'),('关键方法','method'),('实验结果','results'),('局限与边界','limitations'),('复现与启发','reproduction')]: sections.append({'title':label,'body':a.get(key,'')[:220]})
            claims='\n'.join(x['claim'] for x in a.get('contributions',[]))[:220]
            sections.insert(1,{'title':'核心贡献（AI 整理，待核验）','body':claims})
            if not a:
                h=p.get('highlights',[])
                for section,item in zip(sections,h): section['body']=(item['quote']+f" [p.{item['page']}]")[:220]
            return jsonify(title=p['title'][:120],subtitle='网络安全论文阅读报告',sections=sections)
        v=request.json
        if not isinstance(v.get('title'),str) or not 1<=len(v['title'])<=120: raise ValueError('标题需要 1 至 120 个字符。')
        sections=v.get('sections')
        if not isinstance(sections,list) or len(sections)!=6: raise ValueError('需要六个重点模块。')
        for s in sections:
            if not isinstance(s,dict) or not isinstance(s.get('title'),str) or not 1<=len(s['title'])<=30 or not isinstance(s.get('body'),str) or len(s['body'])>220: raise ValueError('每个模块标题最多30字，正文最多220字。请精简重点后再导出。')
        v={k:v[k] for k in ('title','sections')}; v['subtitle']=str(request.json.get('subtitle',''))[:100]
        with m.lock:
            p=m.paper(pid); p['story']=v; m.put(p)
        return jsonify(v)

    def all_notes(p):
        text='# '+p['title']+'\n\n'+p['report']+'\n\n'+analysis_text(p.get('analysis'))+'\n\n## 我的笔记\n\n'+p['notes']
        text+='\n\n## 高亮摘录\n\n'+'\n\n'.join(f"[p.{h['page']}] {h['quote']}\n\n批注：{h['note']}" for h in p.get('highlights',[]))
        text+='\n\n## 关联比较\n\n'+p.get('comparison',{}).get('text','')
        for source in p.get('comparison',{}).get('sources',[]): text+=f"\n{source['label']}：{source['title']}，使用页码 {source['pages']}\n"
        text+='\n\n## 分段精读\n\n'+'\n\n'.join(p['sections'])+'\n\n## 问答\n\n'+'\n\n'.join(x['q']+'\n\n'+x['a'] for x in p['chat'])
        return text
    m.app.view_functions['export']=lambda pid:m.app.response_class(all_notes(m.paper(pid)),mimetype='text/markdown',headers={'Content-Disposition':'attachment; filename="pawsec-notes.md"'})

    @app.get('/api/papers/<pid>/download/<kind>')
    def download(pid,kind):
        from exports import make_notes, make_poster, make_slides
        p=m.paper(pid)
        if kind=='notes.pdf': raw=make_notes(all_notes(p)); mime='application/pdf'
        elif kind in ('poster.pdf','poster.png','slides.pptx'):
            s=p.get('story')
            if not s or not any(x['body'].strip() for x in s['sections']): raise ValueError('请先在展示工坊编辑并保存重点，再下载。')
            if kind=='slides.pptx': raw=make_slides(s,p,m.ROOT); mime='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            else:
                raw=make_poster(s,p); mime='application/pdf'
                if kind.endswith('.png'):
                    d=fitz.open(stream=raw,filetype='pdf'); raw=d[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6)).tobytes('png'); d.close(); mime='image/png'
        else: raise ValueError('不支持的导出格式。')
        return send_file(io.BytesIO(raw),mimetype=mime,as_attachment=True,download_name='pawsec-'+kind)
