import io, html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
INK='#243C36';GREEN='#287B66';MUTED='#65776E'
def minutes(seconds):return f'{seconds/60:.1f}'
def markdown(r):
    s=r['stats'];lines=[f"# {r['title']}",'',f"{r['start']} 至 {r['end']} · 本机日期（{r['timezone']}）",'',
      f"导入 {s['imported']} 篇 | 有效阅读 {s['read']} 篇 | 读完 {s['completed']} 篇 | 阅读 {minutes(s['seconds'])} 分钟",'']
    for key,label in [('overview','本期概览'),('achievements','主要收获与完成事项'),('blockers','问题与待验证事项'),('next_steps','下一步计划')]:lines+=['## '+label,'',r[key] or '尚未填写','']
    lines+=['## 每篇论文小结','']
    for i,e in enumerate(r['entries'],1):
        lines += [f"### {i:02d}. {e['title']}",'',('本期导入' if e.get('imported') else '本期阅读 / 已收录')+f" | 阅读 {minutes(e.get('seconds',0))} 分钟 | "+('本期标记读完' if e.get('completed') else '未标记读完'),'',e.get('summary','') or '尚未填写小结','',f"小结来源：{e.get('summary_source','手动编辑')}",'','我的工作与收获：'+(e.get('reflection') or '尚未填写'),'']
    if not r['entries']:lines+=['本期暂无导入或阅读记录。','']
    lines+=['## 每日活动','']
    for d in r['timeline']:lines+=[f"- {d['day']}：导入 {d['imports']} 篇；阅读 {minutes(d['seconds'])} 分钟；读完 {d['completed']} 篇。"+(' 涉及：'+'；'.join(d['titles']) if d['titles'] else '')]
    lines+=['','统计口径：按本机自然日归集；周一为每周起点。有效阅读按累计至少 30 秒或标记读完计算；导入不等于阅读。论文笔记与问答仅作为当前参考，不计作本期新增工作。']
    return '\n'.join(lines)

def make_pdf(r):
    out=io.BytesIO();story=[];width=A4[0]-88
    def style(size=10.5,color=INK,after=8):return ParagraphStyle('report',fontName='STSong-Light',fontSize=size,leading=size*1.65,textColor=colors.HexColor(color),spaceAfter=after,wordWrap='CJK')
    def p(text,size=10.5,color=INK):return Paragraph(html.escape(str(text)).replace('\n','<br/>'),style(size,color))
    story+=[p('PAWSEC / RESEARCH JOURNAL',10,GREEN),Spacer(1,12),p(r['title'],25),p(f"{r['start']} 至 {r['end']}  ·  {r['timezone']}",10,MUTED),Spacer(1,14)]
    s=r['stats'];stats=Table([[p(str(s['imported'])+' 篇',18,GREEN),p(str(s['read'])+' 篇',18,GREEN),p(str(s['completed'])+' 篇',18,GREEN),p(minutes(s['seconds'])+' 分钟',18,GREEN)],
        [p('本期导入',9,MUTED),p('有效阅读',9,MUTED),p('标记读完',9,MUTED),p('记录时长',9,MUTED)]],colWidths=[width/4]*4)
    stats.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EEF4ED')),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),12),('BOTTOMPADDING',(0,-1),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story += [stats,Spacer(1,20)]
    def section(label,text):
        h=p(label,15,GREEN);h.keepWithNext=True;story.extend([h,p(text or '尚未填写'),Spacer(1,8)])
    for key,label in [('overview','01  本期概览'),('achievements','02  主要收获与完成事项'),('blockers','03  问题与待验证事项'),('next_steps','04  下一步计划')]:section(label,r[key])
    h=p('05  每篇论文小结',17,GREEN);h.keepWithNext=True;story.append(h)
    if not r['entries']:story.append(p('本期暂无导入或阅读记录。',11,MUTED))
    for i,e in enumerate(r['entries'],1):
        title=p(f"{i:02d}  {e['title']}",13);title.keepWithNext=True
        meta=p(('本期导入' if e.get('imported') else '本期阅读 / 已收录')+f"  ·  {e.get('pages',0)} 页  ·  阅读 {minutes(e.get('seconds',0))} 分钟  ·  "+('本期读完' if e.get('completed') else '未标记读完'),9,MUTED)
        meta.keepWithNext=True
        story.extend([title,meta,p(e.get('summary') or '尚未填写小结'),p('来源：'+e.get('summary_source','手动编辑'),9,MUTED)])
        reflection_title=p('我的工作与收获',10,GREEN);reflection_title.keepWithNext=True
        story.extend([reflection_title,p(e.get('reflection') or '尚未填写',10),Spacer(1,13)])
    if r['timeline']:
        h=p('06  每日活动',17,GREEN);h.keepWithNext=True;story.append(h)
        for d in r['timeline']:section(d['day'],f"导入 {d['imports']} 篇；阅读 {minutes(d['seconds'])} 分钟；读完 {d['completed']} 篇。"+ ('\n'+'；'.join(d['titles']) if d['titles'] else ''))
    story.extend([Spacer(1,16),p('统计口径：本机自然日；周一为每周起点。有效阅读为累计至少 30 秒或标记读完。导入不等于阅读。论文小结不代表本人已完成该论文的全部研究。',9,MUTED)])
    def footer(c,d):
        c.setFillColor(colors.HexColor(MUTED));c.setFont('STSong-Light',9);c.drawString(44,25,'PawSec  /  研究汇报');c.drawRightString(A4[0]-44,25,str(d.page))
    SimpleDocTemplate(out,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=48,title=r['title'],author='PawSec').build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
