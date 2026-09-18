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
HEIGHTS = {'fig_knowdo': 150.0, 'fig_mixed': 159.5}
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
                      r'\usepackage{tikz}',
                      r'\pdfinfoomitdate=1', r'\pdftrailerid{}', r'\pdfsuppressptexinfo=15']
        palette = dict(ink=cs.INK, muted=cs.MUTED, grid=cs.LINE, band=cs.GREY_LIGHT, white=cs.WHITE)
        for i, m in enumerate(cs.MODEL_ORDER):
            palette[f'm{i}'] = cs.model(m).colour
            palette[f't{i}'] = cs.model(m).text
        self.lines += [rf'\definecolor{{{k}}}{{HTML}}{{{v.lstrip("#")}}}' for k, v in palette.items()]
        self.lines += [r'\begin{document}',
                       rf'\begin{{tikzpicture}}[x=1bp,y=-1bp,text=ink,every node/.style={{inner sep=0pt,outer sep=0pt,font=\fontsize{{{TEXT_PT}}}{{9.5}}\selectfont}}]',
                       rf'\path[use as bounding box] (0,0) rectangle ({cs.COL_W_PT},{self.height});']

    def text(self, x, y, text, *, anchor='center', colour='ink', bold=False):
        font = r',font=\fontsize{9.2}{10}\selectfont\bfseries' if bold else ''
        self.lines.append(rf'\node[anchor={anchor},align=center,text={colour}{font}] at {coord(x,y)} {{{text}}};')

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

    def ci(self, x, y, lo, hi, m, *, horizontal=True, filled=True):
        if lo > hi:
            raise ValueError('reversed confidence interval')
        colour=f'm{cs.MODEL_ORDER.index(m)}'
        if horizontal:
            if not lo-1e-7 <= x <= hi+1e-7: raise ValueError('estimate outside interval')
            self.line(lo,y,hi,y,colour=colour,width=1.0)
            for v in (lo,hi): self.line(v,y-1.7,v,y+1.7,colour=colour,width=.8)
        else:
            if not lo-1e-7 <= y <= hi+1e-7: raise ValueError('estimate outside interval')
            self.line(x,lo,x,hi,colour=colour,width=1.0)
            for v in (lo,hi): self.line(x-1.6,v,x+1.6,v,colour=colour,width=.8)
        self.mark(x,y,m,filled=filled)

    def write(self):
        p=FIG/f'{self.name}.tex'
        p.write_text('\n'.join(self.lines+[r'\end{tikzpicture}',r'\end{document}'])+'\n',encoding='utf-8')
        return p


def knowdo(rows):
    d=Drawing('fig_knowdo')
    data={r['model']:r for r in rows}
    if set(data)!=set(cs.MODEL_ORDER) or len(rows)!=5: raise ValueError('Figure 3 requires five unique models')
    xa=lambda v: 68+70*(v+0.15)/1.3
    xb=lambda v: 162+71*(v+10)/20
    for i in (1,3): d.band(1,36+17.7*i,239,52+17.7*i)
    d.text(68,9,'a  Answers',anchor='west',bold=True)
    d.text(161,9,'b  Contributions',anchor='west',bold=True)
    d.text(103,25,r'Drop in Pr(B) (pp)')
    d.text(197.5,25,'Change (units)')
    for x in (xa(0),xb(0)): d.line(x,35,x,123,dash='densely dotted',width=.7)
    d.line(xa(1),35,xa(1),123,colour='ink',dash='dashed',width=.8)
    for i,m in enumerate(cs.MODEL_ORDER):
        y=44+17.7*i
        r=data[m]
        d.text(1,y,LABELS[m],anchor='west',colour=f't{i}')
        d.ci(xa(float(r['dx'])),y,xa(float(r['x_lo'])),xa(float(r['x_hi'])),m)
        d.ci(xb(float(r['dy'])),y,xb(float(r['y_lo'])),xb(float(r['y_hi'])),m)
    for x0,x1 in ((68,138),(162,233)): d.line(x0,125,x1,125,colour='ink',width=.7)
    for value in (0,.5,1):
        x=xa(value); d.line(x,125,x,128,colour='ink');d.text(x,134,str(round(100*value)))
    for value in (-10,0,10):
        x=xb(value); d.line(x,125,x,128,colour='ink');d.text(x,134,str(value) if value>=0 else r'\textminus10')
    d.text(120,145,'Risk 0.1 to 0.9; 10 games per model and risk',colour='muted')
    return d.write()


def mixed(rows):
    d=Drawing('fig_mixed')
    short={cd.show(m):m for m in cs.MODEL_ORDER}
    a=[r for r in rows if r['panel']=='a'];b=[r for r in rows if r['panel']=='b']
    if len(a)!=8 or len(b)!=20: raise ValueError('Figure 5 requires 8 + 20 estimates')
    xa=lambda v: 55+64*v/100
    xb=lambda v: 155+18.7*(v-1)
    yb=lambda v: 139-5.05*(v-8)
    d.text(1,9,'a  One replacement',anchor='west',bold=True)
    d.text(145,9,'b  Units per seat',anchor='west',bold=True)
    # The legend is neutral: fill encodes condition, not another model.
    for x,label,filled in ((4,'Self-play',True),(57,'+1 Qwen',False)):
        d.lines.append(rf'\path[draw=ink,fill={"ink" if filled else "white"},line width=.8bp] {coord(x,27)} circle[radius=2.1bp];')
        d.text(x+5,27,label,anchor='west')
    for x,y,m,label in ((147,25,'Haiku','Haiku'),(199,25,'Luna','Luna'),(147,38,'Flash-Lite','Flash-Lite'),(207,38,'Qwen','Qwen')):
        d.mark(x,y,m,size=1.9); d.text(x+5,y,label,anchor='west')
    models=('Haiku','Flash-Lite','Luna','Grok')
    for i,m in enumerate(models):
        y=57+23*i
        if i%2: d.band(1,y-10.5,124,y+10.5)
        d.text(1,y,LABELS[m],anchor='west',colour=f't{cs.MODEL_ORDER.index(m)}')
    for v in (0,50,100): d.line(xa(v),45,xa(v),138,opacity=.25,width=.5)
    for i,m in enumerate(models):
        for condition,offset in (('self_play',-3.6),('one_Qwen_seat',3.6)):
            r=next(r for r in a if short[r['model']]==m and r['condition']==condition)
            d.ci(xa(float(r['estimate'])),57+23*i+offset,xa(float(r['ci_low'])),xa(float(r['ci_high'])),m,filled=condition=='self_play')
    for v in (10,15,20,25):
        d.line(149,yb(v),235,yb(v),opacity=.28,width=.5)
        d.text(144,yb(v),str(v),anchor='east')
    d.line(149,yb(20),235,yb(20),dash='densely dotted',width=.8)
    for m in ('Haiku','Flash-Lite','Luna','Qwen'):
        group=sorted((r for r in b if short[r['model']]==m),key=lambda r:int(r['grok_seats']))
        if [int(r['grok_seats']) for r in group]!=[1,2,3,4,5]: raise ValueError(f'incomplete composition: {m}')
        pts=[(xb(int(r['grok_seats'])),yb(float(r['estimate']))) for r in group]
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]): d.line(x1,y1,x2,y2,colour=f'm{cs.MODEL_ORDER.index(m)}',width=1.1)
        for (x,y),r in zip(pts,group): d.ci(x,y,yb(float(r['ci_high'])),yb(float(r['ci_low'])),m,horizontal=False)
    for x0,x1 in ((52,123),(149,235)): d.line(x0,141,x1,141,colour='ink',width=.7)
    for v in (0,50,100):
        x=xa(v);d.line(x,141,x,144,colour='ink');d.text(x,146.5,str(v))
    for v in range(1,6):
        x=xb(v);d.line(x,141,x,144,colour='ink');d.text(x,146.5,str(v))
    d.text(86,154.5,r'Target reached (\%)')
    d.text(192,154.5,'Grok 4.20 seats')
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
