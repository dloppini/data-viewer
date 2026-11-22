"""Build the dashboard's reading view and its printable manual from the same Markdown."""
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph,
                                Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "documentation"
SOURCE = DOCS / "manual.md"
PDF = DOCS / "Data Viewer Manual.pdf"
CHAPTERS = {
    "Quick start":"start", "System map":"map", "Workbook and controls":"workbook-guide",
    "Open a recording":"logs", "Configure scatter":"scatter", "Component catalogue and exports":"catalogue",
    "Embed a plug-in":"embed", "Parameter and event reference":"parameters",
    "Local service and analysis":"service", "Performance and evidence":"performance",
    "Repository and maintenance":"project", "Troubleshooting and references":"resources",
}
md = MarkdownIt("commonmark", {"html":False}).enable("table")
ink, muted, accent = "#192E42", "#425A6C", "#175CA1"
pale, rule = "#EDF3F7", "#CDD8E2"
PAGE_W, PAGE_H = A4
WIDTH = PAGE_W - 104

def chapters(source):
    intro, *parts = source.split("\n## ")
    found = []
    for part in parts:
        title, body = part.split("\n", 1)
        found.append((title, CHAPTERS[title], body.strip()))
    if {key for _,key,_ in found} != set(CHAPTERS.values()):
        raise ValueError("The chapter index does not match the manual.")
    return intro.strip().split("\n\n"), found

def dashboard(parts):
    nav = "\n".join(f'<a href="#{key}">{escape(title)}</a>' for title,key,_ in parts)
    articles = "\n".join(f'<article id="{key}"><h1>{escape(title)}</h1>{md.render(body)}</article>'
                         for title,key,body in parts)
    template = (ROOT/"web/dashboard-template.html").read_text(encoding="utf-8")
    return template.replace("{{CHAPTERS}}",nav).replace("{{ARTICLES}}",articles)

def fonts():
    folder=Path("C:/Windows/Fonts")
    if (folder/"segoeui.ttf").exists():
        pdfmetrics.registerFont(TTFont("ViewerSans",folder/"segoeui.ttf"))
        pdfmetrics.registerFont(TTFont("ViewerBold",folder/"segoeuib.ttf"))
        pdfmetrics.registerFontFamily("ViewerSans",normal="ViewerSans",bold="ViewerBold")
        return "ViewerSans","ViewerBold"
    return "Helvetica","Helvetica-Bold"

REG,BOLD=fonts()
def style(name,size,leading,**kwargs):
    return ParagraphStyle(name,fontName=kwargs.pop("fontName",REG),fontSize=size,leading=leading,
                          textColor=colors.HexColor(ink),**kwargs)

body_style=style("body",10.4,15.6,spaceAfter=9)
cell_style=style("table cell",9.3,13.5)
head_style=style("table heading",9.1,13,fontName=BOLD)
chapter_style=style("chapter",27,32,fontName=BOLD,spaceAfter=16)
sub_style=style("subheading",14,18,fontName=BOLD,spaceBefore=8,spaceAfter=6,keepWithNext=True)
code_style=style("code",8.1,12,fontName="Courier",leftIndent=9,spaceBefore=4,spaceAfter=12)

def rich(node):
    if node.type=="text":return escape(node.content)
    if node.type=="code_inline":return '<font name="Courier" size="8.5">'+escape(node.content)+'</font>'
    if node.type in ("softbreak","hardbreak"):return " " if node.type=="softbreak" else "<br/>"
    data="".join(rich(c) for c in node.children)
    if node.type=="strong":return "<b>"+data+"</b>"
    if node.type=="em":return "<i>"+data+"</i>"
    if node.type=="link":
        return '<a href="'+escape(node.attrs["href"],quote=True)+'" color="'+accent+'">'+data+'</a>'
    return data

def plain(node):
    if node.type in ("text","code_inline"):return node.content
    return "".join(plain(c) for c in node.children)

def rows(node):
    return [row.children for section in node.children for row in section.children]

class RouteDiagram(Flowable):
    def __init__(self,stages):
        super().__init__()
        self.stages=stages
        self.height=37
    def wrap(self,availWidth,availHeight):
        self.width=availWidth
        return self.width,self.height
    def draw(self):
        c=self.canv; gap=18; width=(self.width-gap*(len(self.stages)-1))/len(self.stages)
        for i,label in enumerate(self.stages):
            x=i*(width+gap)
            c.setFillColor(colors.HexColor(pale));c.setStrokeColor(colors.HexColor(rule))
            c.roundRect(x,6,width,27,4,fill=1,stroke=1)
            c.setFillColor(colors.HexColor(ink));c.setFont(BOLD,9.3)
            c.drawCentredString(x+width/2,16,label)
            if i<len(self.stages)-1:
                end=x+width+gap-3
                c.setStrokeColor(colors.HexColor(accent));c.line(x+width+3,19,end,19)
                c.line(end-3,22,end,19);c.line(end-3,16,end,19)

def table(node):
    grid=rows(node); count=len(grid[0])
    widths=([.29,.71] if count==2 else [.25,.29,.46])
    if plain(grid[0][1]).startswith(("Scatter data","5 million")):widths=[.55,.225,.225]
    data=[[Paragraph(rich(cell), head_style if not i else cell_style) for cell in row] for i,row in enumerate(grid)]
    obj=Table(data,colWidths=[w*WIDTH for w in widths],repeatRows=1,hAlign="LEFT")
    obj.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(pale)),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),.4,colors.HexColor(rule)),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    return [obj,Spacer(1,9)]

class Manual(SimpleDocTemplate):
    def afterFlowable(self,flow):
        if hasattr(flow,"chapter_id"):
            self.canv.bookmarkPage(flow.chapter_id)
            self.canv.addOutlineEntry(flow.getPlainText(),flow.chapter_id,level=0)
            self.notify("TOCEntry",(0,flow.getPlainText(),self.page,flow.chapter_id))

def page_frame(c,doc):
    c.saveState()
    c.setStrokeColor(colors.HexColor(rule));c.line(46,PAGE_H-36,PAGE_W-46,PAGE_H-36)
    c.setFont(BOLD,9);c.setFillColor(colors.HexColor(ink));c.drawString(46,PAGE_H-26,"Data Viewer")
    c.setFont(REG,8);c.setFillColor(colors.HexColor(muted))
    c.drawRightString(PAGE_W-46,PAGE_H-26,"User manual and technical reference")
    c.line(46,35,PAGE_W-46,35);c.drawRightString(PAGE_W-46,22,str(doc.page))
    c.restoreState()

def build_pdf(target,intro,parts):
    doc=Manual(str(target),pagesize=A4,leftMargin=46,rightMargin=46,topMargin=49,bottomMargin=47,
               title=intro[0].lstrip("# ")+" | "+intro[1],author="Data Viewer")
    toc=TableOfContents()
    toc.levelStyles=[style("contents",11,17,spaceBefore=4)]
    story=[Spacer(1,28),Paragraph(escape(intro[0].lstrip("# ")),style("title",40,48,fontName=BOLD)),
           Paragraph(escape(intro[1]),style("subtitle",19,27)),Spacer(1,8),
           Paragraph(escape(intro[2]),body_style),Spacer(1,25),Paragraph("Contents",sub_style),toc]
    for title,key,content in parts:
        heading=Paragraph(escape(title),chapter_style);heading.chapter_id=key
        story.extend([PageBreak(),heading])
        for node in SyntaxTreeNode(md.parse(content)).children:
            if node.type=="paragraph":story.append(Paragraph(rich(node),body_style))
            elif node.type=="heading":
                if key=="map" and plain(node)=="Workflows":story.append(PageBreak())
                story.append(Paragraph(rich(node),sub_style))
            elif node.type in ("ordered_list","bullet_list"):
                for i,item in enumerate(node.children,1):
                    story.append(Paragraph(rich(item),style("item",10.4,15.6,leftIndent=18,firstLineIndent=0,
                        bulletIndent=0,spaceAfter=6),bulletText=f"{i}." if node.type=="ordered_list" else "•"))
            elif node.type=="fence":story.append(Preformatted(node.content.rstrip(),code_style,maxLineLength=92))
            elif node.type=="table":
                grid=rows(node)
                if key=="map" and plain(grid[0][0])=="Workflow":
                    for name,route,outcome in grid[1:]:
                        story.append(KeepTogether([Paragraph(rich(name),sub_style),RouteDiagram(plain(route).split(" → ")),Paragraph(rich(outcome),body_style)]))
                else:story.extend(table(node))
    doc.multiBuild(story,onFirstPage=page_frame,onLaterPages=page_frame)

def main():
    intro,parts=chapters(SOURCE.read_text(encoding="utf-8"))
    with TemporaryDirectory(dir=DOCS) as work:
        folder=Path(work)
        build_pdf(folder/PDF.name,intro,parts)
        (folder/"dashboard.html").write_text(dashboard(parts),encoding="utf-8")
        (folder/PDF.name).replace(PDF)
        (folder/"dashboard.html").replace(DOCS/"dashboard.html")
    print(f"Built {PDF.name} and dashboard.html from {SOURCE.name}.")

if __name__=="__main__":
    main()
