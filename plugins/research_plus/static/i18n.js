import {workspaceRows,dynamicText} from './workspace-translations.js';
import {rows,copy} from './translations.js';
import {extraRows} from './extra-translations.js';
const languages=['zh','en','ja','ko'];let language=localStorage.getItem('pawsec-language')||'zh';if(!languages.includes(language))language='zh';let busy=false,scheduled=false;const memories=new WeakMap(),attrs=new WeakMap();const table=new Map((rows+'\n'+extraRows+'\n'+workspaceRows).trim().split('\n').map(line=>{const cols=line.split('|');return [cols[0],cols]}));
export function lang(){return language}export function t(key){return copy[key]?.[languages.indexOf(language)]||key}
const skip='script,style,textarea,input,canvas,.textLayer,#text,#sections,#messages .answer,#analysis .answer,#analysis .evidence,#comparison,#marks blockquote,.posterSection p,.posterTitle,.card h3,#paperTitle,.relatedTitle,.dayPaper strong,.dayCompleted,[data-no-i18n]';
export function translated(original){const trimmed=original.trim();const known=table.get(trimmed);if(known)return original.replace(trimmed,known[languages.indexOf(language)]||trimmed);if(language==='zh')return original;const dynamic=dynamicText(trimmed,language,translated);if(dynamic!==trimmed)return original.replace(trimmed,dynamic);const idx=languages.indexOf(language)-1;const patterns=[
 [/^当前模型：(.*)$/,[x=>'Model: '+x,x=>'モデル：'+x,x=>'모델: '+x]],
 [/^(\d+) 处标记$/,[x=>x+' highlights',x=>x+' 件のマーカー',x=>x+'개 강조']],
 [/^第 (\d+) 页 ↗$/,[x=>'Page '+x+' ↗',x=>x+'ページ ↗',x=>x+'페이지 ↗']],
 [/^当前连续 (\d+) 天 · 最长连续 (\d+) 天$/,[ (a,b)=>'Current '+a+' days · Best '+b+' days',(a,b)=>'現在 '+a+'日・最長 '+b+'日',(a,b)=>'현재 '+a+'일 · 최장 '+b+'일']],
 [/^(\d{4}) 年 (\d{2}) 月$/,[ (y,m)=>y+' / '+m,(y,m)=>y+'年'+m+'月',(y,m)=>y+'년 '+m+'월']],
 [/^(\d{2})月(\d{2})日的足迹$/,[ (m,d)=>'Journal · '+m+'/'+d,(m,d)=>m+'月'+d+'日の記録',(m,d)=>m+'월 '+d+'일 기록']],
 [/^还差 (\d+) 篇，一篇一篇来。$/,[n=>n+' papers to go, one at a time.',n=>'あと'+n+'本。一つずつ。',n=>n+'편 남았어요. 한 편씩 천천히.']],
 [/^(\d+) 分钟活动$/,[n=>n+' minutes active',n=>n+'分の活動',n=>n+'분 활동']],
 [/^(\d+) 秒活动$/,[n=>n+' seconds active',n=>n+'秒の活動',n=>n+'초 활동']],
 [/^电脑日期 · (UTC.*)$/,[x=>'Computer time · '+x,x=>'PCの日付 · '+x,x=>'컴퓨터 시간 · '+x]],
 [/^(\d{4}\.\d{2}\.\d{2}) · 今天也有汪陪你$/,[x=>x+' · Your buddy is here',x=>x+' · 今日も一緒に',x=>x+' · 오늘도 함께해요']],
 [/^研究空间 \/ (.*)$/,[x=>'Workspace / '+translated(x),x=>'ワークスペース / '+translated(x),x=>'작업 공간 / '+translated(x)]],
 [/^贡献 (\d+)$/,[x=>'Contribution '+x,x=>'貢献 '+x,x=>'기여 '+x]],
 [/^正在解析 (.*)$/,[x=>'Parsing '+x,x=>x+' を解析中',x=>x+' 분석 중']]
 ];for(const [regex,functions]of patterns){const m=trimmed.match(regex);if(m)return original.replace(trimmed,functions[idx](...m.slice(1)))}return original}
export function translate(){if(busy)return;busy=true;observer.disconnect();try{document.documentElement.lang={zh:'zh-CN',en:'en',ja:'ja',ko:'ko'}[language];document.querySelectorAll('[data-i18n]').forEach(e=>{const value=t(e.dataset.i18n);if(e.textContent!==value)e.textContent=value});document.querySelectorAll('[data-i18n-placeholder]').forEach(e=>e.placeholder=t(e.dataset.i18nPlaceholder));const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=walker.nextNode()){if(!n.parentElement||n.parentElement.closest(skip)||n.parentElement.closest('[data-i18n]'))continue;let rec=memories.get(n);if(!rec||n.nodeValue!==rec.last)rec={original:n.nodeValue,last:n.nodeValue};const value=translated(rec.original);if(n.nodeValue!==value)n.nodeValue=value;rec.last=value;memories.set(n,rec)}document.querySelectorAll('[placeholder],[title],[aria-label]').forEach(e=>{if(e.closest('[data-no-i18n]')||e.dataset.i18nPlaceholder)return;let rec=attrs.get(e)||{};for(const key of ['placeholder','title','aria-label']){if(!e.hasAttribute(key))continue;const v=e.getAttribute(key);if(!rec[key]||v!==rec[key].last)rec[key]={original:v};const value=translated(rec[key].original);if(v!==value)e.setAttribute(key,value);rec[key].last=value}attrs.set(e,rec)})}finally{busy=false;observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label']})}}
const observer=new MutationObserver(()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;translate()})});
export function setLanguage(value){if(!languages.includes(value))return;language=value;localStorage.setItem('pawsec-language',value);translate();document.dispatchEvent(new CustomEvent('pawsec:language',{detail:{language}}))}translate();
