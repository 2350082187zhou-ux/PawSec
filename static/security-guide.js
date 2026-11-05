import {lang} from '/plugins/research-plus/i18n.js';
const $=s=>document.querySelector(s);
const groups=[
['01 · 问题与研究定位',[['研究问题与动机','本文解决什么安全问题？现实场景、保护资产、现有工作的不足分别是什么？'],['研究方向','判断本文属于网络与协议安全、系统与软件安全、密码与隐私、Web与应用安全、AI安全、数据与云安全、物联网与工控安全、攻防检测与数字取证中的哪些方向。允许交叉归类，说明依据。'],['贡献与基线','区分新问题、新方法、新系统、新数据或新评估；分别列出作者贡献主张和已有工作的差异。']]],
['02 · 威胁模型与安全目标',[['保护资产与目标','识别保护资产和机密性、完整性、可用性、认证、隐私等目标，说明成功条件。'],['攻击者能力','攻击者能观察、修改、注入或控制什么？区分白盒黑盒、主动被动、内部外部权限。'],['攻击面与信任边界','列出入口、组件、通信路径及跨越的信任边界。哪些组件被默认可信？'],['假设与范围外威胁','逐条列出关键假设、范围外攻击和成立条件，并说明假设失效的后果。'],['攻击与防御成功标准','如何判定攻击成功和防御有效？指标是否覆盖安全目标？']]],
['03 · 方法与机制',[['流程与模块','按输入、模块、数据流、输出解释方法，给出小例子。'],['核心公式与算法','解释核心公式的符号、优化目标和算法步骤，不补造未提供的公式。'],['安全保证与证明','区分形式化证明、经验有效性与作者推测。列出证明条件和保证边界。'],['部署与性能代价','分析部署位置、权限、依赖、延迟、吞吐和资源开销。']]],
['04 · 实验与证据',[['数据与划分','检查数据来源、样本规模、标签质量、时间划分、训练测试重叠及泄漏。'],['基线与公平性','检查基线是否强且相关，调参、算力和输入条件是否公平。'],['指标与误报漏报','解释准确率、精确率、召回、FPR/FNR、攻击成功率等实际采用指标；讨论基准发生率。'],['消融与因果证据','哪些消融支持各模块贡献？相关性是否被误当因果？'],['统计与稳健性','检查随机种子、重复次数、置信区间、显著性和参数敏感性。'],['泛化与自适应攻击','检查跨数据集、跨时间、跨环境泛化，以及知道防御后重新优化的攻击。']]],
['05 · 复现与工程落地',[['代码数据与环境','列出代码、数据、版本、依赖、硬件、随机种子；明确未公开项。'],['最小复现实验','制定验证核心主张的最小实验：输入、步骤、指标、预期现象及失败判据。'],['部署可行性','评估真实流量、扩展性、运维、误报处理和与现有系统兼容性。']]],
['06 · 失效边界与批判阅读',[['适用边界与反例','什么条件下方法失效？区分作者承认的局限与基于原文的推断。'],['绕过与对抗风险','从防御评估角度讨论是否考虑自适应对手、分布漂移和组合攻击。'],['证据缺口','哪些结论超过了实验能支持的范围？还需什么证据？'],['下一步研究','提出可检验的后续研究问题及验证方法，说明其与本文局限的联系。']]],
['07 · 整理与自测',[['结构化阅读笔记','按问题、威胁模型、方法、证据、贡献、局限、复现和待解决问题生成阅读笔记。'],['理解自测','给出五个覆盖威胁模型、方法、证据与边界的理解问题，先不展示答案。']]]
];
const root=document.createElement('section');root.id='securityReadingGuide';root.dataset.noI18n='';const title=document.createElement('h3');title.textContent='网安论文 · 分步精读';const intro=document.createElement('p');intro.textContent='按问题定位 → 威胁模型 → 方法 → 实验证据 → 复现 → 边界阅读。展开一个步骤，选择你要核对的问题。';root.append(title,intro);
for(const [heading,items]of groups){const d=document.createElement('details'),s=document.createElement('summary');s.textContent=heading;d.append(s);for(const [label,prompt]of items){const b=document.createElement('button');b.textContent=label;b.title=prompt;b.onclick=()=>{if($('#ask').disabled)return;document.dispatchEvent(new CustomEvent('pawsec:quick-question',{detail:{scope:'page',prompt:prompt+' 请结合本文可检索的原文回答，引用 [p.N] 页码；不把未报告当作不存在，不编造数据。若当前材料不足以覆盖全文，请明确指出缺失章节。回答语言：'+({zh:'中文',en:'English',ja:'日本語',ko:'한국어'}[lang()]||'中文')}}))};d.append(b)}root.append(d)}
$('#overview .promptGrid').replaceWith(root);
// The reading workspace keeps the original companion card hidden.
const card=$('.companionCard');if(card)card.hidden=true;
