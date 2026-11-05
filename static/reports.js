import {translated} from '/plugins/research-plus/i18n.js';
import {briefView} from '/static/paper-brief.js';
import '/plugins/research-plus/plus.js';
const $=s=>document.querySelector(s),emit=(name,detail)=>document.dispatchEvent(new CustomEvent(name,{detail}));
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const labels={day:'日报',week:'周报',month:'月报'};
const css=el('link');css.rel='stylesheet';css.href='/static/reports.css';document.head.append(css);
const home=el('section',undefined,'reportHome');home.id='reportHome';
home.innerHTML='<div class="reportHomeHead"><div><span class="eyebrow">RESEARCH JOURNAL</span><h2>把研究进展，整理成可交付的汇报。</h2><p>论文归档、逐篇小结、阅读记录。每天有积累，每周有方向。</p></div><span class="reportHomeTag">可编辑 · 可下载 PDF</span></div><div class="reportShortcuts"></div>';
$('#library .hero').after(home);
for(const kind of ['day','week','month']){const b=el('button',undefined,'reportShortcut');b.dataset.reportKind=kind;b.innerHTML=`<span>${{day:'01 / DAILY',week:'02 / WEEKLY',month:'03 / MONTHLY'}[kind]}</span><strong>${{day:'今日研究日报',week:'本周研究周报',month:'本月研究月报'}[kind]} ↗</strong><small>正在读取记录…</small>`;b.onclick=()=>open(kind,today());home.querySelector('.reportShortcuts').append(b)}
const nav=el('button','▤  研究汇报');nav.dataset.view='reports';nav.onclick=()=>open(kind,date);document.querySelector('.sidebar nav').append(nav);
const page=el('section',undefined,'view');page.id='reports';page.hidden=true;
page.innerHTML=`<div class="reportPageHead"><div><span class="eyebrow">RESEARCH JOURNAL</span><h1>研究汇报</h1><p>把读过的论文、做过的工作和接下来的问题放在一起。</p></div><button id="reportBack">← 返回书架</button></div>
<div class="reportControls"><div class="reportTabs" role="group" aria-label="汇报周期"><button data-period="day">日报</button><button data-period="week">周报</button><button data-period="month">月报</button></div><label>选择日期 <input id="reportDate" type="date" min="1970-01-01" max="9998-12-31"></label><button id="reportToday">回到本期</button><select id="reportHistory" aria-label="已保存的汇报"><option value="">打开已保存汇报</option></select></div>
<div id="reportMessage" role="status"></div><div id="reportBody" hidden><div class="reportRange"></div><div id="reportStats" class="reportStats"></div>
<div class="reportActionBar"><span id="reportSaveState" role="status"></span><div><button id="reportSave">保存汇报</button><button data-report-download="md">下载 Markdown</button><button data-report-download="json">下载数据</button><button class="primary" data-report-download="pdf">下载精美 PDF</button></div></div>
<div class="reportEditor"><div class="reportMain"><label>汇报标题<input id="reportTitle" maxlength="200"></label><label>本期概览<textarea id="reportOverview" rows="3" maxlength="12000"></textarea></label><div class="reportFieldGrid"><label>主要收获与完成事项<textarea id="reportAchievements" rows="4" maxlength="12000" placeholder="记录自己真正完成的阅读、实验、复现和思考…"></textarea></label><label>问题与待验证事项<textarea id="reportBlockers" rows="4" maxlength="12000" placeholder="有哪些结论还需验证？哪些地方尚未读懂？"></textarea></label></div><label>下一步计划<textarea id="reportNextSteps" rows="3" maxlength="12000" placeholder="下一阶段具体要做什么？"></textarea></label></div><aside class="reportGuide"><h3>这份汇报包含什么？</h3><p>本期导入的论文单独归类；本期阅读过的旧论文也会收录。</p><p>有效阅读按累计至少 30 秒或标记读完统计。导入数量不等于阅读数量。</p><p>小结说明论文内容；“我的工作与收获”记录你实际做过的事。</p><p>按本机日期统计。周一至周日为一周，自然月为一个月。</p><p>编辑后自动保存，也可手动保存。PDF 导出前会保存当前修改。</p></aside></div>
<div class="reportPaperHead"><div><h2>逐篇论文小结</h2><p>摘录可直接修改；AI 小结使用当前模型并产生 API 用量。</p></div><button id="reportSummarize">AI 补全待整理小结</button></div><div id="reportEntries"></div><section class="reportTimeline"><h2>这段时间，我做了什么？</h2><div id="reportTimeline"></div></section></div>`;
document.querySelector('main').append(page);
let kind='day',date=today(),report=null,dirty=false,editVersion=0,timer,savePromise=null,operation=false,loadVersion=0;
const fieldMap={title:'#reportTitle',overview:'#reportOverview',achievements:'#reportAchievements',blockers:'#reportBlockers',next_steps:'#reportNextSteps'};
const status=text=>$('#reportSaveState').textContent=text;
async function api(url,body){const r=await fetch(url,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'请求失败');return data}
const url=()=>'/api/reports?kind='+kind+'&date='+date;
function changed(){dirty=true;editVersion++;status('有未保存修改…');clearTimeout(timer);timer=setTimeout(()=>save().catch(showError),900)}
function showError(e){$('#reportMessage').textContent=e.message;$('#reportMessage').className='reportError';status('保存或操作未完成，请重试');emit('pawsec:toast',{text:e.message})}
async function save(force=false){
  clearTimeout(timer);if(savePromise){await savePromise;if(dirty||force)return save(force);return}
  if(!report||(!dirty&&!force))return;
  const version=editVersion,payload=JSON.parse(JSON.stringify(report)),target=url();status('正在保存…');
  savePromise=api(target,payload).then(r=>{report.revision=r.revision;report.saved_at=r.saved_at;if(editVersion===version)dirty=false;status(dirty?'仍有修改待保存':'已保存 · '+new Date(r.saved_at*1000).toLocaleTimeString());$('#reportMessage').textContent=''}).finally(()=>savePromise=null);
  await savePromise;
}
function controls(lock){operation=lock;page.querySelectorAll('button,select,input,textarea').forEach(b=>b.disabled=lock||b.dataset.missing==='true');home.querySelectorAll('button').forEach(b=>b.disabled=lock)}
async function task(fn){if(operation)return;controls(true);try{await fn()}catch(e){showError(e)}finally{controls(false)}}
async function open(nextKind,nextDate){return task(async()=>{
  await save();const serial=++loadVersion;
  const next=await api('/api/reports?kind='+nextKind+'&date='+nextDate);if(serial!==loadVersion)return;
  kind=nextKind;date=nextDate;report=next;dirty=false;$('#reportDate').value=date;
  emit('pawsec:navigate',{name:'reports'});$('#breadcrumb').textContent='研究空间 / 研究'+labels[kind];render();await history();
})}
function render(){
  $('#reportBody').hidden=false;$('#reportMessage').textContent='';
  page.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===kind)));
  $('.reportRange').textContent=labels[kind]+' / '+report.start+' — '+report.end+' · '+report.timezone;
  const s=report.stats;$('#reportStats').replaceChildren();for(const [value,label] of [[s.imported,'本期导入'],[s.read,'有效阅读'],[s.completed,'标记读完'],[(s.seconds/60).toFixed(1),'阅读分钟']]){const card=el('div');card.append(el('strong',value),el('span',label));$('#reportStats').append(card)}
  for(const [key,id] of Object.entries(fieldMap))$(id).value=report[key];
  status(report.saved_at?'已保存 · '+new Date(report.saved_at*1000).toLocaleString():'自动整理完成 · 编辑后保存');renderEntries();
  const timeline=$('#reportTimeline');timeline.replaceChildren();
  for(const d of report.timeline){const row=el('article');row.append(el('strong',d.day),el('p',`导入 ${d.imports} 篇 · 阅读 ${(d.seconds/60).toFixed(1)} 分钟 · 读完 ${d.completed} 篇`));if(d.titles.length){const titles=el('small',d.titles.join(' / '));titles.dataset.noI18n='';row.append(titles)}timeline.append(row)}
  if(!report.timeline.length)timeline.append(el('p','本期暂无记录。你仍可填写计划和手动汇报。','muted'));
}
function renderEntries(){
  const box=$('#reportEntries');box.replaceChildren();
  for(const imported of [true,false]){
    const entries=report.entries.filter(e=>Boolean(e.imported)===imported);if(!entries.length)continue;
    box.append(el('h3',(imported?'本期导入':'本期阅读的旧论文 / 已收录')+' · '+entries.length,'reportGroupTitle'));
    for(const e of entries){
      const card=el('article',undefined,'reportPaper');card.dataset.reportPaper=e.id;
      const head=el('div',undefined,'reportPaperTitle'),title=el('h3',e.title),actions=el('div');title.dataset.noI18n='';
      const source=el('button','打开原文 ↗');source.disabled=e.missing;source.dataset.missing=String(e.missing);source.onclick=()=>task(async()=>{await save();emit('pawsec:jump',{id:e.id,page:1})});
      const ai=el('button','AI 生成小结');ai.disabled=e.missing;ai.dataset.missing=String(e.missing);ai.onclick=()=>task(async()=>{if(e.summary&&/^(AI|手动)/.test(e.summary_source)&&!confirm(translated('这会替换此篇现有小结，是否继续？')))return;await generate(e);renderEntries();await save(true)});actions.append(source,ai);head.append(title,actions);
      const meta=el('p',`${e.pages||0} 页 · 阅读 ${((e.seconds||0)/60).toFixed(1)} 分钟 · ${e.completed?'本期已标记读完':'未标记读完'}`,'reportPaperMeta');
      const label=el('label','论文小结'),summary=el('textarea');summary.rows=6;summary.maxLength=12000;summary.value=e.summary;summary.setAttribute('aria-label',e.title+'：论文小结');label.append(summary);
      const provenance=el('small','来源：'+e.summary_source,'reportProvenance');
      summary.oninput=()=>{e.summary=summary.value;e.summary_source='手动编辑';provenance.textContent='来源：手动编辑';changed()};
      const reflectionLabel=el('label','我的工作与收获'),reflection=el('textarea');reflection.rows=3;reflection.maxLength=12000;reflection.value=e.reflection;reflection.placeholder='今天 / 本周 / 本月，我围绕这篇论文实际完成了什么？';reflection.setAttribute('aria-label',e.title+'：我的工作与收获');reflection.oninput=()=>{e.reflection=reflection.value;changed()};reflectionLabel.append(reflection);
      card.append(head,meta,briefView({title:e.title,brief:e.brief}),label,provenance,reflectionLabel);
      if(e.evidence){const details=el('details'),caption=el('summary','参考当前笔记与提问（不代表本期新增）');const notes=el('p',e.evidence.notes||'暂无阅读笔记');if(e.evidence.notes)notes.dataset.noI18n='';details.append(caption,notes);for(const q of e.evidence.questions){const question=el('p',q);question.dataset.noI18n='';details.append(question)}card.append(details)}
      box.append(card);
    }
  }
  if(!report.entries.length){const empty=el('div',undefined,'reportEmpty');empty.append(el('h3','本期还没有论文记录'),el('p','导入论文或开始阅读后，这里会按日期自动归集。也可切换日期查看历史。'));const b=el('button','导入 PDF','primary');b.onclick=()=>$('#file').click();empty.append(b);box.append(empty)}
}
async function generate(e){status('正在生成：'+e.title);const result=await api('/api/reports/summary/'+e.id,{});e.summary=result.summary;e.summary_source=result.summary_source;changed()}
for(const [key,id] of Object.entries(fieldMap))$(id).oninput=()=>{if(report){report[key]=$(id).value;changed()}};
page.querySelectorAll('[data-period]').forEach(b=>b.onclick=()=>open(b.dataset.period,date));
$('#reportDate').value=date;$('#reportDate').onchange=async()=>{const selected=$('#reportDate').value;if(selected)await open(kind,selected);$('#reportDate').value=date};
$('#reportToday').onclick=()=>open(kind,today());$('#reportBack').onclick=()=>task(async()=>{await save();emit('pawsec:navigate',{name:'library'})});
$('#reportSave').onclick=()=>task(async()=>{await save(true);await history()});
$('#reportSummarize').onclick=()=>task(async()=>{
  const pending=report.entries.filter(e=>!e.missing&&!/^(AI|手动)/.test(e.summary_source));if(!pending.length){status('所有小结均已整理，可逐篇继续编辑');return}
  for(const e of pending){await generate(e);await save(true)}renderEntries();status('小结已生成并保存');
});
page.querySelectorAll('[data-report-download]').forEach(b=>b.onclick=()=>task(async()=>{
  await save(true);const fmt=b.dataset.reportDownload;status('正在生成下载文件…');const r=await fetch('/api/reports/download/'+fmt+'?kind='+kind+'&date='+date);if(!r.ok){const e=await r.json();throw Error(e.error||'导出失败')}
  const href=URL.createObjectURL(await r.blob()),a=el('a');a.href=href;a.download=`PawSec-${labels[kind]}-${report.start}.${fmt}`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),60000);status('已保存，文件已生成');await history();
}));
async function history(){const list=await api('/api/reports/history'),select=$('#reportHistory');select.replaceChildren(new Option('打开已保存汇报',''));for(const r of list)select.add(new Option(r.start+' · '+labels[r.kind]+' · '+r.title,r.kind+'|'+r.start))}
$('#reportHistory').onchange=()=>{const value=$('#reportHistory').value;if(value){const [k,d]=value.split('|');open(k,d)}};
async function homeStats(){await Promise.all(Object.keys(labels).map(async k=>{try{const r=await api('/api/reports?kind='+k+'&date='+today());home.querySelector(`[data-report-kind="${k}"] small`).textContent=`导入 ${r.stats.imported} 篇 · 阅读 ${r.stats.read} 篇 · ${(r.stats.seconds/60).toFixed(1)} 分钟`}catch{home.querySelector(`[data-report-kind="${k}"] small`).textContent='打开汇报查看记录'}}))}
document.addEventListener('pawsec:view',e=>{if(e.detail.name==='library')homeStats();if(e.detail.name!=='reports'&&dirty)save().catch(e=>emit('pawsec:toast',{text:e.message}))});
window.addEventListener('beforeunload',e=>{if(dirty||savePromise){e.preventDefault();e.returnValue=''}});
homeStats();
