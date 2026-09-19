#!/usr/bin/env python3
"""Repeatable preflight for the reconstructed standalone figure.
Run from this directory's parent: python qa/validate.py
Dependencies: PyMuPDF, Pillow, numpy. No OCR is used.
"""
from pathlib import Path
import itertools
import json
import re
import fitz
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
doc = fitz.open(ROOT/'figure.pdf')
assert len(doc) == 1, 'Expected a one-page standalone figure.'
page = doc[0]
spans = [s for b in page.get_text('dict')['blocks'] if b['type'] == 0
         for line in b['lines'] for s in line['spans'] if s['text'].strip()]
text = page.get_text()
normal = re.sub(r'\s+', ' ', text)
required = ['The game', 'Four designs', '6 players', '10 rounds', '40 each',
            'pay 0 / 2 / 4', 'target 120', 'Outcomes', 'Target reached',
            'Miss + catastrophe', 'Miss + no catastrophe', 'keep remainder',
            'lose all', 'keep money', 'Models we study', 'Claude', 'Haiku 4.5',
            'GPT-5.6', 'Luna', 'Gemini 3.5', 'Flash-Lite', 'Qwen3-235B',
            'Grok 4.20', 'Self-play', 'same model', 'Prompt tests',
            'prompt variants', 'Scripted partners', 'fixed partners',
            'Mixed tables', 'two models']
missing = [word for word in required if word not in normal]
assert not missing, f'Missing selectable labels: {missing}'
assert len(re.findall(r'\bFixed\b', text)) == 5, 'Five selectable Fixed labels required.'
assert '\ufffd' not in text and '\u25a0' not in text, 'Broken or replacement glyph detected.'
for glyph in ['→', '≥', '×', '−']:
    assert glyph in text, f'Missing extractable mathematical symbol: {glyph}'

out_of_page = []
for s in spans:
    rect = fitz.Rect(s['bbox'])
    if not page.rect.contains(rect):
        out_of_page.append(s['text'])
assert not out_of_page, f'Text outside the canvas: {out_of_page}'

text_overlaps = []
for a, b in itertools.combinations(spans, 2):
    inter = fitz.Rect(a['bbox']) & fitz.Rect(b['bbox'])
    # Tiny rounding intersections between contiguous font runs are harmless.
    if not inter.is_empty and inter.width > .05 and inter.get_area() > .2:
        text_overlaps.append([a['text'], b['text'], list(inter)])
assert not text_overlaps, f'Intersecting text bounding boxes: {text_overlaps}'

images = page.get_images(full=True)
assert len(images) == 19, f'Expected 19 extracted illustrations, got {len(images)}.'
text_image_overlaps = []
dpi = []
for entry in images:
    xref, smask, w, h = entry[:4]
    assert smask, f'Image {xref} is missing its transparency mask.'
    mask = fitz.Pixmap(doc, smask)
    alpha = np.frombuffer(mask.samples, dtype=np.uint8).reshape(mask.height, mask.width, mask.n)[:, :, 0]
    for rect in page.get_image_rects(xref):
        dpi.extend([w/rect.width*72, h/rect.height*72])
        for s in spans:
            inter = rect & fitz.Rect(s['bbox'])
            if inter.is_empty:
                continue
            xa = max(0, int(np.floor((inter.x0-rect.x0)/rect.width*w)))
            xb = min(w, int(np.ceil((inter.x1-rect.x0)/rect.width*w)))
            ya = max(0, int(np.floor((inter.y0-rect.y0)/rect.height*h)))
            yb = min(h, int(np.ceil((inter.y1-rect.y0)/rect.height*h)))
            piece = alpha[ya:yb, xa:xb]
            if piece.size and np.any(piece > 64):
                text_image_overlaps.append({'text': s['text'], 'image': xref})
assert not text_image_overlaps, f'Text intersects opaque icon pixels: {text_image_overlaps}'

pngs = sorted((ROOT/'assets').glob('*.png'))
assert len(pngs) == 19
for png in pngs:
    im = Image.open(png)
    assert im.mode == 'RGBA', f'{png.name} is not RGBA.'
    alpha = np.asarray(im)[:, :, 3]
    assert np.any(alpha == 0) and np.any(alpha == 255), f'Invalid alpha: {png.name}'
    border = np.concatenate([alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]])
    assert np.all(border == 0), f'Clipped transparent guard band: {png.name}'

fonts = page.get_fonts(full=True)
for font in fonts:
    assert doc.xref_get_key(font[0], 'ToUnicode')[0] != 'null', f'No Unicode map: {font}'

report = {
    'status': 'PASS',
    'pdf_pages': len(doc),
    'page_size_mm': [round(page.rect.width/72*25.4, 3), round(page.rect.height/72*25.4, 3)],
    'text_spans': len(spans),
    'selectable_fixed_labels': 5,
    'missing_expected_labels': missing,
    'out_of_page_text': out_of_page,
    'text_text_bbox_intersections': text_overlaps,
    'text_opaque_image_intersections': text_image_overlaps,
    'transparent_png_assets': len(pngs),
    'embedded_raster_images': len(images),
    'font_resources_with_Unicode_maps': len(fonts),
    'effective_native_icon_dpi_at_output_size': [round(min(dpi), 1), round(max(dpi), 1)],
    'notes': [
        'Text extraction and font-map checks are performed on actual text objects, without OCR.',
        'Image intersections use the embedded alpha masks, not just rectangular image boxes.',
        'Full layouts and extracted-asset edges also received visual inspection.',
        'Icons remain raster extracts; vector paths, backgrounds, and labels are supplied by TikZ.',
    ],
}
(ROOT/'qa'/'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))
