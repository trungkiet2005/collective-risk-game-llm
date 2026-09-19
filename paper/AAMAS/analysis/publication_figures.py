"""Typeset Figures 3 and 5 as editable TikZ, without changing any estimate.

Run probes.py and mixed.py first, then this script (requires pdflatex and PyMuPDF).
--source-only writes the two standalone .tex files and a provenance manifest.
Colours, model order and page width come from the existing shared paper style.
The CSVs, not rounded manuscript macros, are the sole source of plotted values.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
import crsd_style as cs
import crsd_data as cd

FIG = cd.FIGURES
TEXT_PT = 8.25
HEIGHTS = {'fig_knowdo': 158.0, 'fig_mixed': 146.0}
RISK_LOW, RISK_HIGH = 0.1, 0.9
ARROW_MIN_BP = 14.0   # a shorter change is drawn as a plain segment: no room for a head
LABELS = {'Haiku': r'Haiku 4.5', 'Flash-Lite': r'Gemini 3.5\\Flash-Lite',
          'Luna': r'GPT-5.6\\Luna', 'Qwen': r'Qwen3-235B', 'Grok': r'Grok 4.20'}


def coord(x: float, y: float) -> str:
    return f'({x:.5f},{y:.5f})'


class Drawing:
    def __init__(self, name: str):
        self.name, self.height = name, HEIGHTS[name]
        self.lines = [r'\documentclass[border=0pt]{standalone}',
                      r'\usepackage[T1]{fontenc}',
                      r'\usepackage[tt=false,type1=true]{libertine}',
                      r'\usepackage{tikz}', r'\usetikzlibrary{arrows.meta}',
                      r'\pdfinfoomitdate=1', r'\pdftrailerid{}', r'\pdfsuppressptexinfo=15']
        palette = dict(ink=cs.INK, muted=cs.MUTED, grid=cs.LINE, band=cs.GREY_LIGHT, white=cs.WHITE)
        for i, m in enumerate(cs.MODEL_ORDER):
            palette[f'm{i}'] = cs.model(m).colour
            palette[f't{i}'] = cs.model(m).text
        self.lines += [rf'\definecolor{{{k}}}{{HTML}}{{{v.lstrip("#")}}}' for k, v in palette.items()]
        self.lines += [r'\begin{document}',
                       rf'\begin{{tikzpicture}}[x=1bp,y=-1bp,text=ink,every node/.style={{inner sep=0pt,outer sep=0pt,font=\fontsize{{{TEXT_PT}}}{{9.5}}\selectfont}}]',
                       rf'\path[use as bounding box] (0,0) rectangle ({cs.COL_W_PT},{self.height});']

    def text(self, x, y, text, *, anchor='center', colour='ink', bold=False, italic=False,
             align='center'):
        font = r',font=\fontsize{9.2}{10}\selectfont\bfseries' if bold else ''
        font += r',font=\fontsize{8.25}{9.2}\selectfont\itshape' if italic else ''
        self.lines.append(rf'\node[anchor={anchor},align={align},text={colour}{font}] at {coord(x,y)} {{{text}}};')

    def line(self, x1, y1, x2, y2, *, colour='grid', width=0.6, dash='', opacity=1):
        self.lines.append(rf'\draw[draw={colour},line width={width}bp,opacity={opacity}{","+dash if dash else ""}] {coord(x1,y1)} -- {coord(x2,y2)};')

    def band(self, x1, y1, x2, y2):
        self.lines.append(rf'\fill[band] {coord(x1,y1)} rectangle {coord(x2,y2)};')

    def mark(self, x, y, m, filled=True, size=2.2):
        if not (size <= x <= cs.COL_W_PT-size and size <= y <= self.height-size):
            raise ValueError(f'marker outside page: {self.name} {m} {x},{y}')
        colour = f'm{cs.MODEL_ORDER.index(m)}'
        fill = colour if filled else 'white'
        style = rf'draw={colour},fill={fill},line width=0.8bp'
        shape = cs.model(m).marker
        if shape == 'o':
            path = rf'{coord(x,y)} circle[radius={size}bp]'
        elif shape == 's':
            r = size*0.89
            path = rf'{coord(x-r,y-r)} rectangle {coord(x+r,y+r)}'
        elif shape == 'D':
            r = size*1.12
            path = ' -- '.join(coord(a,b) for a,b in [(x,y-r),(x+r,y),(x,y+r),(x-r,y)])+' -- cycle'
        else:
            r = size*1.12
            sign = 1 if shape == '^' else -1
            path = ' -- '.join(coord(a,b) for a,b in [(x,y-sign*r),(x+r,y+sign*r*.75),(x-r,y+sign*r*.75)])+' -- cycle'
        self.lines.append(rf'\path[{style}] {path};')

    def circle(self, x, y, colour, filled=True, size=2.1):
        fill = colour if filled else 'white'
        self.lines.append(rf'\path[draw={colour},fill={fill},line width=.8bp] {coord(x,y)} circle[radius={size}bp];')

    @staticmethod
    def check(value, lo, hi):
        if lo > hi:
            raise ValueError('reversed confidence interval')
        if not lo-1e-7 <= value <= hi+1e-7:
            raise ValueError('estimate outside interval')

    def bar(self, lo, hi, y, m):
        """A 95% interval as a translucent round-ended bar; zero width draws nothing."""
        if hi-lo > 1e-7:
            colour = f'm{cs.MODEL_ORDER.index(m)}'
            self.lines.append(rf'\draw[draw={colour},line width=4.6bp,line cap=round,opacity=.28] {coord(lo,y)} -- {coord(hi,y)};')

    def arrow(self, x0, x1, y, colour, *, dashed=False):
        """The change between two measured values; too short for a head, a segment."""
        if abs(x1-x0) < 1e-7:
            return
        if abs(x1-x0) < ARROW_MIN_BP:
            self.line(x0, y, x1, y, colour=colour, width=1.1)
            return
        dash = ',dash pattern=on 2.6bp off 1.6bp' if dashed else ''
        self.lines.append(rf'\draw[draw={colour},line width=1.1bp,-{{Stealth[length=3.6bp,width=3.4bp]}},shorten <=3.2bp,shorten >=3.4bp{dash}] {coord(x0,y)} -- {coord(x1,y)};')

    def ribbon(self, points, m):
        """Interval band through (x, lo, hi) points, in the model colour."""
        colour = f'm{cs.MODEL_ORDER.index(m)}'
        path = [coord(x, lo) for x, lo, _ in points] + [coord(x, hi) for x, _, hi in reversed(points)]
        self.lines.append(rf'\fill[fill={colour},opacity=.18] ' + ' -- '.join(path) + ' -- cycle;')

    def polyline(self, points, colour, width=1.1):
        self.lines.append(rf'\draw[draw={colour},line width={width}bp,line join=round] ' + ' -- '.join(coord(x, y) for x, y in points) + ';')

    def ci(self, x, y, lo, hi, m, *, horizontal=True, filled=True):
        self.check(x if horizontal else y, lo, hi)
        if horizontal:
            self.bar(lo, hi, y, m)
        else:
            self.lines.append(rf'\draw[draw=m{cs.MODEL_ORDER.index(m)},line width=4.6bp,line cap=round,opacity=.28] {coord(x,lo)} -- {coord(x,hi)};' if hi-lo > 1e-7 else '')
        self.mark(x,y,m,filled=filled)

    def write(self):
        p=FIG/f'{self.name}.tex'
        p.write_text('\n'.join(self.lines+[r'\end{tikzpicture}',r'\end{document}'])+'\n',encoding='utf-8')
        return p


def knowdo(rows):
    """One arrow per model from p = 0.1 (open) to p = 0.9 (filled). Bars are the level
    intervals of the supplement's knowdo table, which also gives the shift intervals."""
    d=Drawing('fig_knowdo')
    data={(r['model'],float(r['p'])):r for r in rows}
    want={(m,p) for m in cs.MODEL_ORDER for p in (RISK_LOW,RISK_HIGH)}
    if set(data)!=want or len(rows)!=len(want): raise ValueError('Figure 3 requires every model once at p = 0.1 and p = 0.9')
    xa=lambda v: 60+68*v            # share of answers saying B, 0..1
    xb=lambda v: 150+84*(v-10)/30   # units the questioned seat pays, 10..40
    ys=[25+19.5*i for i in range(6)]
    d.text(56,8,'a  Answers',anchor='west',bold=True)
    d.text(146,8,'b  Play',anchor='west',bold=True)
    # Reference row: a fully correct answerer says B at p = 0.1 and A at p = 0.9.
    # It applies only to the stated question, not to best responses in self-play.
    d.text(50,ys[0],'Correct',anchor='east',colour='muted',italic=True)
    d.arrow(xa(1),xa(0),ys[0],'muted',dashed=True)
    d.circle(xa(1),ys[0],'muted',filled=False); d.circle(xa(0),ys[0],'muted')
    # The risk legend sits in panel b's reference row; fill encodes risk, not a model.
    for x,p,filled in ((160,RISK_LOW,False),(197,RISK_HIGH,True)):
        d.circle(x,ys[0],'ink',filled=filled); d.text(x+4.5,ys[0],rf'\textit{{p}}\,=\,{p:g}',anchor='west')
    d.line(xb(20),ys[0]+9,xb(20),131,colour='muted',dash='densely dotted',width=.8)
    for i,m in enumerate(cs.MODEL_ORDER):
        y=ys[i+1]
        d.text(50,y,LABELS[m],anchor='east',colour=f't{i}',align='right')
        lo,hi=data[(m,RISK_LOW)],data[(m,RISK_HIGH)]
        for x,col,low,high in ((xa,'keep',0,1),(xb,'paid',10,40)):
            for r in (lo,hi):
                v,v_lo,v_hi=(float(r[c]) for c in (col,col+'_lo',col+'_hi'))
                d.check(v,v_lo,v_hi)
                if not low<=v_lo and v_hi<=high: raise ValueError(f'{m} {col} outside the axis')
                d.bar(x(v_lo),x(v_hi),y,m)
            x0,x1=x(float(lo[col])),x(float(hi[col]))
            d.arrow(x0,x1,y,f'm{i}')
            d.mark(x0,y,m,filled=False); d.mark(x1,y,m)
    for x0,x1 in ((56,132),(146,238)): d.line(x0,134,x1,134,colour='ink',width=.7)
    for v in (0,.5,1):
        x=xa(v); d.line(x,134,x,137,colour='ink'); d.text(x,142.5,str(round(100*v)))
    for v in (10,20,30,40):
        x=xb(v); d.line(x,134,x,137,colour='ink'); d.text(x,142.5,str(v))
    d.text(xa(.5),152.5,r'Answers favouring B (\%)')
    d.text(xb(25),152.5,'Units paid (of 40)')
    return d.write()


def mixed(rows):
    d=Drawing('fig_mixed')
    short={cd.show(m):m for m in cs.MODEL_ORDER}
    a=[r for r in rows if r['panel']=='a'];b=[r for r in rows if r['panel']=='b']
    if len(a)!=8 or len(b)!=20: raise ValueError('Figure 5 requires 8 + 20 estimates')
    k=cs.MODEL_ORDER.index
    # One shared model legend on top frees both panels from per-row and line-end labels.
    for m,(x,y) in {'Haiku':(4,7),'Flash-Lite':(70,7),'Luna':(168,7),'Qwen':(4,19),'Grok':(70,19)}.items():
        d.line(x,y,x+10,y,colour=f'm{k(m)}',width=1.1)
        d.mark(x+5,y,m,size=1.9)
        d.text(x+14,y,LABELS[m].replace(r'\\',' '),anchor='west')
    d.line(0,27.5,cs.COL_W_PT,27.5,width=.4,opacity=.5)
    top,ax=38,122
    xa=lambda v: 10+v
    xb=lambda n: 142+22.5*(n-1)
    yb=lambda v: ax-4-3.75*(v-8)
    d.text(1,top,'a  One replacement',anchor='west',bold=True)
    d.text(126,top,'b  Units per seat',anchor='west',bold=True)
    # The condition key is neutral: fill encodes condition, not another model.
    for x,label,filled in ((4,'Self-play',True),(46,'+1 Qwen',False)):
        d.circle(x,top+12,'ink',filled=filled); d.text(x+4.5,top+12,label,anchor='west')
    # a: an arrow from self-play to one Qwen seat; both keep their own interval.
    for i,m in enumerate(('Haiku','Flash-Lite','Luna','Grok')):
        y=top+26+15*i
        s,q=(next(r for r in a if short[r['model']]==m and r['condition']==c) for c in ('self_play','one_Qwen_seat'))
        for r in (s,q):
            d.check(float(r['estimate']),float(r['ci_low']),float(r['ci_high']))
            d.bar(xa(float(r['ci_low'])),xa(float(r['ci_high'])),y,m)
        xs,xq=xa(float(s['estimate'])),xa(float(q['estimate']))
        if abs(xs-xq)<1e-7: d.text(xq-6,y,'no change',anchor='east',colour='muted',italic=True)
        d.arrow(xs,xq,y,f'm{k(m)}')
        d.mark(xq,y,m,filled=False); d.mark(xs,y,m)
    d.line(6,ax,114,ax,colour='ink',width=.7)
    for v in (0,25,50,75,100):
        x=xa(v); d.line(x,ax,x,ax+3,colour='ink'); d.text(x,ax+8,str(v))
    d.text(xa(50),ax+18,r'Target reached (\%)')
    # b: every composition is its own measured mean; lines only join them, bands are
    # their intervals. No fit, and no interpolation of data.
    for v in (10,15,20,25):
        d.line(136,yb(v),238,yb(v),opacity=.28,width=.5)
        d.text(133,yb(v),str(v),anchor='east')
    d.line(136,yb(20),238,yb(20),colour='muted',dash='densely dotted',width=.8)
    groups={}
    for m in ('Haiku','Flash-Lite','Luna','Qwen'):
        group=sorted((r for r in b if short[r['model']]==m),key=lambda r:int(r['grok_seats']))
        if [int(r['grok_seats']) for r in group]!=[1,2,3,4,5]: raise ValueError(f'incomplete composition: {m}')
        for r in group: d.check(float(r['estimate']),float(r['ci_low']),float(r['ci_high']))
        d.ribbon([(xb(int(r['grok_seats'])),yb(float(r['ci_low'])),yb(float(r['ci_high']))) for r in group],m)
        groups[m]=[(xb(int(r['grok_seats'])),yb(float(r['estimate']))) for r in group]
    for m,pts in groups.items():
        d.polyline(pts,f'm{k(m)}')
        for x,y in pts: d.mark(x,y,m,size=1.9)
    d.line(136,ax,238,ax,colour='ink',width=.7)
    for n in range(1,6):
        x=xb(n); d.line(x,ax,x,ax+3,colour='ink'); d.text(x,ax+8,str(n))
    d.text(xb(3),ax+18,'Grok 4.20 seats')
    return d.write()


def build_and_check(path):
    import pymupdf
    subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',path.name],cwd=FIG,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    doc=pymupdf.open(path.with_suffix('.pdf'))
    page=doc[0]
    if len(doc)!=1 or abs(page.rect.width-cs.COL_W_PT)>.05: raise RuntimeError('wrong figure page size')
    spans=[s for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans or min(s['size'] for s in spans)<8.0: raise RuntimeError('text below 8 PDF points')
    if any(f[2]=='Type3' for f in page.get_fonts()): raise RuntimeError('Type 3 font')
    for s in spans:
        box=pymupdf.Rect(s['bbox'])
        if not page.rect.contains(box): raise RuntimeError(f'text outside page: {s["text"]}')
    page.get_pixmap(matrix=pymupdf.Matrix(300/72,300/72),alpha=False).save(path.with_suffix('.png'))
    cs.proof_sheet(path.with_suffix('.png'))
    return {'width_bp':page.rect.width,'height_bp':page.rect.height,'minimum_font_bp':min(s['size'] for s in spans),'text_spans':len(spans),'type3_fonts':0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-only',action='store_true')
    args=ap.parse_args()
    report={'renderer':'standalone TikZ / pdflatex','estimates_changed':False,'figures':{}}
    for name,draw in (('fig_knowdo',knowdo),('fig_mixed',mixed)):
        source=FIG/f'{name}.csv'
        rows=list(csv.DictReader(source.open(encoding='utf-8')))
        path=draw(rows)
        entry={'csv_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tex_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'estimates':len(rows)}
        if not args.source_only: entry.update(build_and_check(path))
        report['figures'][name]=entry
        print('wrote',path)
    (FIG/'publication_figures_manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
