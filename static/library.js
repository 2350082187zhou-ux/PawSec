import {briefView} from '/static/paper-brief.js';
import {lang} from '/plugins/research-plus/i18n.js';

const copy = {
  ai:['AI 阅读重点','AI reading insights','AI読書の要点','AI 읽기 핵심'],
  all:['全部文献','All papers','すべて','전체 논문'],
  started:['有阅读记录','Previously opened','閲覧履歴あり','열람 기록'],
  report:['已有精读','With reports','レポートあり','보고서 있음'],
  scanned:['待识读页面','Needs OCR','OCR が必要','OCR 필요'],
  newest:['最近导入','Newest first','新しい順','최근 추가순'],
  recent:['最近阅读','Recently read','最近の閲覧','최근 열람순'],
  title:['标题 A–Z','Title A–Z','タイトル A–Z','제목 A–Z'],
  sort:['排序方式','Sort papers','並び替え','정렬'],
  filters:['筛选书架','Filter library','本棚を絞り込む','서재 필터'],
  resume:['继续上次阅读','Continue reading','続きを読む','이어서 읽기'],
  open:['打开论文','Open paper','論文を開く','논문 열기'],
  start:['开始阅读','Start reading','読み始める','읽기 시작'],
  position:['上次停在','Last opened at','前回の位置','마지막 위치'],
  page:['页','pages','ページ','페이지'],
  emptyTitle:['书架还空着，先放进一篇论文吧','Your library starts with one paper','最初の論文を追加しましょう','첫 논문을 추가해 보세요'],
  emptyBody:['导入 PDF 后，就可以高亮、做笔记和生成精读报告。','Import a PDF to highlight, take notes, and create a report.','PDF を追加して、ハイライトやノートを始めましょう。','PDF를 가져와 강조 표시와 메모를 시작하세요.'],
  noMatch:['没有符合条件的论文','No matching papers','一致する論文がありません','조건에 맞는 논문이 없습니다'],
  noMatchBody:['试试其他标题关键词，或清除筛选查看全部文献。','Try another title or clear the filters to see all papers.','別のキーワードを試すか、絞り込みを解除してください。','다른 제목을 검색하거나 필터를 초기화하세요.'],
  clear:['清除筛选','Clear filters','絞り込みを解除','필터 초기화'],
  upload:['＋ 导入 PDF','＋ Import PDF','＋ PDF を追加','＋ PDF 가져오기'],
  shown:['显示','Showing','表示','표시'],
};
const t = key => copy[key][Math.max(0,['zh','en','ja','ko'].indexOf(lang()))];
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
const read=key=>{try{return localStorage.getItem(key)}catch{return null}};
const position=p=>Math.min(p.pages,Math.max(0,Math.trunc(Number(read('pawsec:last:'+p.id)))||0));
const lastRead=p=>Number(read('pawsec:read-at:'+p.id))||0;

export function createLibrary(getPapers,openPaper){
  const css=el('link');css.rel='stylesheet';css.href='/static/library.css';document.head.append(css);
  const search=document.querySelector('#filter'),cards=document.querySelector('#cards');
  let filter='all',order='newest';
  const bar=el('div',undefined,'libraryToolbar');bar.dataset.noI18n='';
  const filters=el('div',undefined,'libraryFilters');filters.setAttribute('role','group');
  const sort=el('select');sort.id='librarySort';
  for(const value of ['newest','recent','title']){const option=el('option');option.value=value;sort.append(option)}
  const buttons=new Map();
  for(const key of ['all','started','report','scanned']){
    const button=el('button');button.type='button';button.dataset.libraryFilter=key;
    button.onclick=()=>{filter=key;render()};buttons.set(key,button);filters.append(button);
  }
  bar.append(filters,sort);document.querySelector('#library .topicFilters').replaceWith(bar);
  const summary=el('p',undefined,'librarySummary');summary.id='libraryResultCount';summary.dataset.noI18n='';summary.setAttribute('role','status');bar.after(summary);
  const resume=el('section',undefined,'libraryResume');resume.id='libraryResume';resume.dataset.noI18n='';resume.hidden=true;
  document.querySelector('#library .sectionhead').before(resume);
  const matches=(p,key)=>key==='all'||(key==='started'?position(p)>0:key==='report'?Boolean(p.report):Boolean(p.scanned));
  const clear=()=>{search.value='';filter='all';render();search.focus()};
  search.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();clear()}});
  sort.onchange=()=>{order=sort.value;render()};
  function render(){
    const papers=getPapers(),query=search.value.trim().toLocaleLowerCase();
    document.querySelector('#count').textContent=document.querySelector('#statPapers').textContent=papers.length;
    document.querySelector('#statReports').textContent=papers.filter(p=>p.report).length;
    filters.setAttribute('aria-label',t('filters'));sort.setAttribute('aria-label',t('sort'));
    for(const option of sort.options)option.textContent=t(option.value);
    for(const [key,button] of buttons){button.textContent=t(key)+' · '+papers.filter(p=>matches(p,key)).length;button.setAttribute('aria-pressed',String(key===filter))}
    const visible=papers.filter(p=>matches(p,filter)&&[p.title,p.brief?.summary,...(p.brief?.keywords||[])].join(' ').toLocaleLowerCase().includes(query));
    if(order==='title')visible.sort((a,b)=>a.title.localeCompare(b.title));
    // Explicit comparisons keep unread papers behind papers with saved positions.
    if(order==='recent')visible.sort((a,b)=>lastRead(b)-lastRead(a)||Number(position(b)>0)-Number(position(a)>0)||(b.created-a.created));
    if(order==='newest')visible.sort((a,b)=>b.created-a.created);
    summary.textContent=t('shown')+' '+visible.length+' / '+papers.length;
    cards.replaceChildren();
    for(const p of visible){
      const page=position(p),card=el('article',undefined,'card'),top=el('div',undefined,'cardTop'),bottom=el('div',undefined,'cardFoot');
      card.tabIndex=0;card.setAttribute('role','button');card.dataset.paperId=p.id;card.dataset.noI18n='';card.title=p.title;
      card.setAttribute('aria-label',t(page?'resume':'open')+': '+p.title);
      top.append(el('span','▤','icon'),el('small',p.pages+' '+t('page')));
      const date=el('small',new Date(p.created*1000).toLocaleDateString({zh:'zh-CN',en:'en-US',ja:'ja-JP',ko:'ko-KR'}[lang()]));
      bottom.append(el('span',t(p.report?'report':p.scanned?'scanned':'start'),'pill'),date);
      const progress=el('div',undefined,'libraryProgress');
      if(page){const caption=el('span',t('position')+' '+page+' / '+p.pages);const track=el('div',undefined,'libraryProgressTrack'),fill=el('span');fill.style.width=(page/p.pages*100)+'%';track.append(fill);progress.append(caption,track)}
      const ai=el('button',t('ai'),'libraryAiRead');ai.type='button';ai.onclick=e=>{e.stopPropagation();document.dispatchEvent(new CustomEvent('pawsec:auto-read-open',{detail:{id:p.id}}))};card.append(top,el('h3',p.title),briefView(p),ai,progress,bottom);card.onclick=()=>openPaper(p.id);card.onkeydown=e=>{if(e.target===card&&['Enter',' '].includes(e.key)){e.preventDefault();openPaper(p.id)}};cards.append(card);
    }
    if(!visible.length){
      const empty=el('div',undefined,'empty libraryEmpty');empty.dataset.noI18n='';
      empty.append(el('span',papers.length?'⌕':'▤','libraryEmptyIcon'),el('h3',t(papers.length?'noMatch':'emptyTitle')),el('p',t(papers.length?'noMatchBody':'emptyBody')));
      const action=el('button',t(papers.length?'clear':'upload'),'primary');action.type='button';action.onclick=papers.length?clear:()=>document.querySelector('#file').click();empty.append(action);cards.append(empty);
    }
    const recent=papers.filter(p=>position(p)>0).sort((a,b)=>lastRead(b)-lastRead(a)||b.created-a.created)[0];
    resume.replaceChildren();resume.hidden=!recent;
    if(recent){const content=el('div');content.append(el('span',t('resume'),'libraryResumeLabel'),el('h3',recent.title),el('p',t('position')+' '+position(recent)+' / '+recent.pages));const button=el('button',t('resume')+' →','primary');button.type='button';button.onclick=()=>openPaper(recent.id);resume.append(content,button)}
  }
  document.addEventListener('pawsec:language',render);
  document.addEventListener('pawsec:view',e=>{if(e.detail.name==='library')render()});
  document.addEventListener('pawsec:page',e=>{try{localStorage.setItem('pawsec:read-at:'+e.detail.id,String(Date.now()))}catch{}});
  return {render};
}
