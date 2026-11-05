import io, json, subprocess, tempfile, html
from pathlib import Path
import pymupdf as fitz
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfgen.canvas import Canvas
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
INK='#263E3A'; GREEN='#267565'; MUTED='#667C75'; BG='#F8F7F1'
def style(size=11,leading=18,color=INK): return ParagraphStyle('text',fontName='STSong-Light',fontSize=size,leading=leading,textColor=color,wordWrap='CJK',spaceAfter=8)
def para(text,sty): return Paragraph(html.escape(text).replace('\n','<br/>'),sty)
def make_notes(text):
    out=io.BytesIO(); story=[]
    for line in text.splitlines():
        if not line.strip(): story.append(Spacer(1,6)); continue
        level=len(line)-len(line.lstrip('#'))
        story.append(para(line.lstrip('# ').strip() if level else line,style(19 if level==1 else 14 if level else 10.5,25 if level==1 else 20 if level else 17)))
    def footer(c,d):
        c.setFont('STSong-Light',9); c.setFillColor(MUTED); c.drawString(44,25,'PawSec 汪安 · 阅读笔记'); c.drawRightString(A4[0]-44,25,str(d.page))
    SimpleDocTemplate(out,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=44).build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
def fit_paragraph(c,text,x,y,w,h,size):
    minimum=min(10,size)
    while size>=minimum:
        p=para(text,style(size,size*1.55)); _,height=p.wrap(w,h)
        if height<=h: p.drawOn(c,x,y+h-height); return
        size-=.5
    raise ValueError('重点内容超出版面，请缩短对应模块。')
def make_poster(s,paper):
    out=io.BytesIO(); w,h=A3; c=Canvas(out,pagesize=A3); c.setFillColor(BG); c.rect(0,0,w,h,fill=1,stroke=0)
    c.setFillColor(GREEN); c.setFont('STSong-Light',12); c.drawString(42,h-42,'PAWSEC / 网络安全论文研究笔记')
    fit_paragraph(c,s['title'],42,h-208,w-84,140,29)
    fit_paragraph(c,s.get('subtitle',''),42,h-242,w-84,25,12)
    col=(w-104)/2; top=h-278; boxh=245
    for i,section in enumerate(s['sections']):
        x=42+(i%2)*(col+20); y=top-(i//2)*(boxh+20)-boxh
        c.setStrokeColor('#CCD9D1'); c.line(x,y+boxh,x+col,y+boxh)
        fit_paragraph(c,f"0{i+1}  {section['title']}",x,y+boxh-46,col,34,17)
        fit_paragraph(c,section['body'] or '待补充',x,y+7,col,boxh-58,13)
    fit_paragraph(c,'来源：'+paper['title']+'\n[p.N] 为 PDF 物理页码。AI 整理与评价需对照原文核验。',42,23,w-84,58,9)
    c.showPage(); c.save(); return out.getvalue()
def make_slides(s,paper,root):
    with tempfile.TemporaryDirectory(prefix='pawsec-export-') as d:
        dest=Path(d)/'slides.pptx'
        result=subprocess.run(['node',str(root/'export-slides.cjs'),str(dest)],input=json.dumps({'story':s,'source':paper['title']},ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode!=0 or not dest.exists(): raise ValueError('PPT 导出失败，请检查 Node.js 及本地依赖。')
        return dest.read_bytes()

