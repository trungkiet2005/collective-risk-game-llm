#!/usr/bin/env python3
"""Extract the supplied figure's actual pixels; no image synthesis or OCR.
Usage: python extract_assets.py path/to/source.png --output assets
Requires: Pillow, numpy, scipy, opencv-python-headless.
Source coordinates refer to the original 1672 x 941 image.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

# Keep each complete robot/table composition together, rather than recutting robots.
SPECS = {
    'group_game': ((48, 166, 487, 600), 'group', 'Main game: six robots, table, and coins'),
    'group_self_play': ((904, 371, 1186, 588), 'group', 'Self-play: six blue robots and table'),
    'group_prompt_tests': ((1307, 372, 1590, 590), 'group', 'Prompt tests: six multicolour robots and table'),
    'group_scripted_partners': ((917, 666, 1170, 870), 'group', 'Scripted partners: one blue robot, five grey robots, and table; no Fixed labels'),
    'group_mixed_tables': ((1305, 673, 1593, 897), 'group', 'Mixed tables: original six-robot composition and table'),
    'logo_claude': ((907, 158, 973, 219), 'logo', 'Claude symbol only'),
    'logo_gpt': ((1057, 157, 1126, 220), 'logo', 'GPT symbol only'),
    'logo_gemini': ((1211, 157, 1277, 222), 'logo', 'Gemini symbol only'),
    'logo_qwen': ((1374, 158, 1446, 231), 'logo', 'Qwen symbol only'),
    'logo_grok': ((1528, 162, 1584, 222), 'logo', 'Grok symbol only'),
    'icon_players': ((538, 123, 626, 187), 'open', 'Players / people icon'),
    'icon_rounds': ((542, 197, 620, 271), 'icon', 'Calendar / rounds icon'),
    'icon_endowment': ((545, 283, 619, 355), 'icon', 'Coin stack / endowment icon'),
    'icon_contribution': ((542, 362, 619, 442), 'icon', 'Lightning coin / contribution icon'),
    'icon_target': ((538, 449, 620, 525), 'icon', 'Target and arrow icon'),
    'icon_risk': ((539, 535, 619, 619), 'icon', 'Blue risk die'),
    'icon_success': ((115, 715, 192, 791), 'icon', 'Green success check'),
    'icon_catastrophe': ((370, 715, 450, 793), 'icon', 'Red catastrophe / lightning icon'),
    'icon_no_catastrophe': ((638, 712, 710, 790), 'icon', 'Brown no-catastrophe die'),
}


def background_model(rgb: np.ndarray) -> np.ndarray:
    """Robust quadratic fit to the crop border, rejecting foreground outliers."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[-1:1:complex(h), -1:1:complex(w)]
    design = np.stack([np.ones_like(xx), xx, yy, xx*xx, xx*yy, yy*yy], axis=-1)
    ring = np.zeros((h, w), bool)
    b = max(3, min(6, min(h, w)//12))
    ring[:b, :] = ring[-b:, :] = True
    ring[:, :b] = ring[:, -b:] = True
    x, c = design[ring], rgb[ring].astype(float)
    valid = np.ones(c.shape[0], bool)
    for _ in range(12):
        coeff, *_ = np.linalg.lstsq(x[valid], c[valid], rcond=None)
        residual = np.linalg.norm(c-x@coeff, axis=1)
        cutoff = max(3.5, float(np.quantile(residual, 0.65)))
        valid = residual < cutoff
        if valid.sum() < 20:
            raise RuntimeError('Insufficient background samples')
    return np.clip(design@coeff, 0, 255)


def clear_regions(mask: np.ndarray, name: str, box: tuple) -> None:
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1]
    if name == 'group_scripted_partners':
        # Remove the existing typographic badges, not the robot silhouettes.
        # Polygonal cuts follow the rounded badge edges, leaving the adjacent
        # diagonal head outlines intact. The two lower badges meet torso edges
        # in the source; retain the visible silhouette without inventing pixels.
        polygons = [
            [(850, 690), (940, 690), (940, 718), (937, 722), (932, 726), (850, 727)],
            [(1150, 690), (1230, 690), (1230, 727), (1159, 727), (1155, 724), (1152, 721), (1150, 718)],
            [(850, 806), (926, 809), (930, 813), (933, 819), (933, 840), (930, 843), (924, 846), (850, 848)],
            [(1230, 806), (1168, 808), (1164, 811), (1161, 814), (1159, 819), (1159, 840), (1162, 844), (1166, 846), (1230, 848)],
        ]
        cuts = np.zeros(mask.shape, dtype=np.uint8)
        for polygon in polygons:
            pts = np.asarray(polygon, dtype=np.int32) - np.array([x0, y0], dtype=np.int32)
            cv2.fillPoly(cuts, [pts], 1)
        mask[cuts.astype(bool)] = False
        mask[yy >= 870] = False
    # The self-play torso stops above the cyan card border in the source.
    if name == 'group_self_play':
        mask[yy >= 586] = False
    # Parts of numbered badges occasionally enter the raw crop's upper-left corner.
    if name in ('group_self_play', 'group_prompt_tests', 'group_mixed_tables', 'group_scripted_partners'):
        mask[:14, :24] = False


def extract(rgb: np.ndarray, name: str, box: tuple, kind: str) -> tuple[Image.Image, dict]:
    crop = rgb[box[1]:box[3], box[0]:box[2]].copy()
    bg = background_model(crop)
    score = np.max(bg-crop, axis=2)
    mask = score > (22 if kind == 'group' else 18)
    clear_regions(mask, name, box)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n < 2:
        raise RuntimeError(f'No foreground found: {name}')
    if kind == 'group':
        idx = 1+np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = labels == idx
    else:
        keep = np.where(stats[:, cv2.CC_STAT_AREA] >= 6)[0]
        keep = keep[keep != 0]
        mask = np.isin(labels, keep)
    if kind in ('group', 'icon'):
        mask = ndi.binary_fill_holes(mask)
    clear_regions(mask, name, box)

    core = ndi.binary_erosion(mask, iterations=1)
    if not core.any():
        core = mask.copy()
    region = ndi.binary_dilation(mask, iterations=2)
    _, nearest = ndi.distance_transform_edt(~core, return_indices=True)
    fg = crop[nearest[0], nearest[1]].astype(float)
    delta = fg-bg
    alpha = np.sum((crop-bg)*delta, axis=2)/(np.sum(delta*delta, axis=2)+1e-6)
    alpha = np.clip(alpha, 0, 1)
    alpha[core] = 1
    alpha[~region] = 0
    allowed = np.ones_like(mask)
    clear_regions(allowed, name, box)
    alpha[~allowed] = 0
    alpha[alpha < 0.045] = 0
    alpha[alpha > 0.985] = 1
    # Unmatte edges against the fitted original backdrop, avoiding pastel fringes.
    out = (crop.astype(float) - (1-alpha[..., None])*bg) / np.maximum(alpha[..., None], 1e-6)
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    out[alpha == 0] = 0
    rgba = Image.fromarray(np.dstack([out, np.rint(alpha*255).astype(np.uint8)]), 'RGBA')
    bounds = rgba.getbbox()
    if not bounds:
        raise RuntimeError(f'Empty asset: {name}')
    rgba = rgba.crop(bounds)
    # Transparent guard band avoids clipping antialiased silhouettes in TeX.
    padded = Image.new('RGBA', (rgba.width+8, rgba.height+8), (0, 0, 0, 0))
    padded.alpha_composite(rgba, (4, 4))
    global_bounds = [box[0]+bounds[0], box[1]+bounds[1], box[0]+bounds[2], box[1]+bounds[3]]
    return padded, {'source_crop_xyxy': list(box), 'foreground_source_bounds_xyxy': global_bounds,
                    'transparent_padding_px': 4, 'width_px': padded.width, 'height_px': padded.height}


def contact_sheet(assets: Path, output: Path) -> None:
    names = list(SPECS)
    width, height = 330, 260
    sheet = Image.new('RGB', (4*width, 5*height), 'white')
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 15) if Path(font_path).exists() else ImageFont.load_default()
    for i, name in enumerate(names):
        tile = Image.new('RGB', (width, height), '#f8f8f8')
        d = ImageDraw.Draw(tile)
        for y in range(28, height-6, 12):
            for x in range(6, width-6, 12):
                shade = 221 if (x//12+y//12)%2 else 241
                d.rectangle([x, y, min(x+11,width-7), min(y+11,height-7)], fill=(shade, shade, shade))
        d.text((9, 5), name, font=font, fill='#17212b')
        im = Image.open(assets/f'{name}.png').convert('RGBA')
        im.thumbnail((width-22, height-45), Image.Resampling.LANCZOS)
        tile.paste(im, ((width-im.width)//2, 31+(height-37-im.height)//2), im)
        sheet.paste(tile, ((i%4)*width, (i//4)*height))
    sheet.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('assets'))
    args = parser.parse_args()
    im = Image.open(args.source).convert('RGB')
    if im.size != (1672, 941):
        raise SystemExit(f'Expected 1672x941 source pixels; found {im.size}. Do not resize the source first.')
    args.output.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(im)
    manifest = {'source_image_size_px': list(im.size), 'method': 'pixel extraction; fitted-background alpha matting; no generated image content', 'assets': []}
    for name, (box, kind, description) in SPECS.items():
        asset, info = extract(rgb, name, box, kind)
        asset.save(args.output/f'{name}.png', optimize=True)
        manifest['assets'].append({'file': f'{name}.png', 'kind': kind, 'description': description, **info})
        print(f'{name:28s} {asset.width:4d} x {asset.height:<4d}')
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    contact_sheet(args.output, args.output.parent/'assets_contact_sheet.png')

if __name__ == '__main__':
    main()
