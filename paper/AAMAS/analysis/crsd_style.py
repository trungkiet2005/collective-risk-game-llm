"""crsd_style -- the one figure style for the collective-risk paper (AAMAS, ACM sigconf).

Import it in every figure script, call ``use()`` once, and save through ``save()``.
Nothing else in the paper may declare a colour, a font size or a figure width.

    import crsd_style as cs
    cs.use()
    fig, ax = cs.subplots("col", aspect=0.62)
    cs.plot_model(ax, risks, means, "Haiku", yerr=ci)
    cs.theory_line(ax, risks, ev_optimum, label="EV optimum")
    cs.save(fig, "figures/risk_response", width="col")

PAGE GEOMETRY (read from the typeset log, not guessed)
    \\textwidth   = 506.295 pt  (7.032 in)   -> width="full"  (figure*)
    \\columnwidth = 241.1475 pt (3.349 in)   -> width="col"   (figure)
    columnsep 24 pt; body type 9 pt Linux Libertine.
    Figures are exported at exactly these widths and placed with
    \\includegraphics[width=\\columnwidth] / [width=\\textwidth], so a point size set
    here is the printed point size.

TYPE: three sizes, nothing below 7 pt (enforced in save()).
    9 pt bold  panel titles ("a  Risk response")
    8 pt       axis labels, direct line labels, colour-bar label
    7 pt       tick labels, legend entries, heatmap cell values
    Face: Linux Libertine G (TrueType build of the paper's own face), embedded as
    Type 42. Fallbacks, in order: Times New Roman, DejaVu Serif. A fallback prints a
    warning, because a Times figure beside Libertine body text is visible.

MEANING TABLE. ONE MEANING PER COLOUR. This is the whole table; if a hue is not in
it, no figure may use it.

  Neutrals (all lettering, rules and references)
    INK        #17212B  lettering, spines, ticks; THEORY benchmark line (dashed)
    MUTED      #4B5865  secondary lettering; human reference series (open markers)
    LINE       #778492  hairline rules, grid (value axis only), scripted opponents
    REGION     #E6EAEE  shaded parameter region with a theoretical meaning
    GREY_LIGHT #F4F6F8  inert surface (card with no meaning)
    WHITE      #FFFFFF  page

  Models (categorical; ordered dark to light, the order IS the greyscale code)
    model       colour   L*    luma601  on white  marker  text variant  tint
    Qwen        #543859  27.9    68     10.06:1    D      (same)        #F8F0F9
    Haiku       #84442E  36.4    85      7.37:1    o      (same)        #FDEFEB
    Flash-Lite  #3E6D9F  44.9   101      5.39:1    s      (same)        #EDF2FD
    Grok        #977C38  53.3   124      4.00:1    v      #8C722E       #F7F1E8
    Luna        #64A184  61.5   139      3.01:1    ^      #448065       #E9F5EE
  Hue families are the house plum, rust, blue, ochre and sage; lightness was
  re-spaced in 8.4 L* steps so the five survive greyscale and colour-blind
  simulation (numbers below). Grok and Luna are under 4.5:1, so model lettering
  uses the "text variant" column: same hue, 12 to 4 L* darker.

  Maps
    crsd_div  rust #76321C .. #F6F6F6 .. blue #024B72, symmetric L* 30..97..30.
              Negative = rust, positive = blue. For signed matrices only.
    crsd_seq  slate #F4F9FC .. #1D3340, L* 97.6 -> 20.0 in 9.7 steps, chroma <= 14.
    crsd_pay  units one seat pays in one round: 0 #D3DEE6, 2 #7891A2, 4 #1D3340. Sampled
              from crsd_seq (anchors 1, 4, 8), so darker always means paying more. Used
              as three discrete swatches (which move) and as a continuous 0..4 map (mean).
    model ramp  WHITE -> a model's text colour, for a matrix whose rows are models and
              whose cells print their value; hue says which model, lightness says how much.

WHAT THIS PALETTE COSTS (stated, not hidden)
  1. The diverging map borrows the rust and blue hue families of Haiku and
     Flash-Lite. It may appear only in matrix panels whose axes name the models
     and which carry no model-coloured marks.
  2. Luna sits exactly on the 3:1 floor for graphical marks. Its lines are drawn at
     full weight with markers; never as a hairline, never as lettering.
  3. Greyscale identity rests on 8.4 L* steps (min CIEDE2000 6.8 under CIE grey,
     5.6 under Rec.601 luma). That separates solid marks side by side, not thin
     lines far apart. Marker shape is therefore mandatory on every model series.
  4. Grok (luma 124) and LINE (luma 130) are the same grey in mono; scripted
     opponents drawn in LINE therefore use open markers and no model marker shape.
  5. A diverging map cannot carry sign in greyscale (mirror pairs differ by
     dE00 0.0). Every cell of a signed matrix prints its signed value.

MEASURED (python crsd_style.py re-derives all of these; do not hand-edit)
  Model palette, minimum pairwise CIEDE2000:
    normal 25.9 | deuteranopia 15.7 | protanopia 16.8 | tritanopia 16.2
    CIE-Y greyscale 6.8 | Rec.601 luma greyscale 5.6 | min dE00 to INK 10.9
  For comparison, the Okabe-Ito set in the previous draft: greyscale 0.6
  (orange #E69F00 and sky blue #56B4E9 print as the same grey).
  Heatmap cell text: white below L* 53, INK above. Binding constraint 4.0:1 at
  L* 53 (both inks), the best any continuous map allows.
  CVD simulation: Machado, Oliveira & Fernandes (2009), severity 1.0, applied in
  linear RGB.
"""
from __future__ import annotations

import itertools
import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D

from crsd_data import show

# --------------------------------------------------------------------------- geometry
POINTS_PER_INCH = 72.0
COL_W_PT = 241.1475
TEXT_W_PT = 506.295
COL_W = COL_W_PT / POINTS_PER_INCH
TEXT_W = TEXT_W_PT / POINTS_PER_INCH
PDF_RASTER_DPI = 900
PNG_DPI = 300

# --------------------------------------------------------------------------- type
SIZE_TITLE = 9.0
SIZE_LABEL = 8.0
SIZE_SMALL = 7.0
MIN_TEXT_PT = 7.0

# --------------------------------------------------------------------------- neutrals
INK = "#17212B"
MUTED = "#4B5865"
LINE = "#778492"
REGION = "#E6EAEE"
GREY_LIGHT = "#F4F6F8"
WHITE = "#FFFFFF"


# --------------------------------------------------------------------------- models
@dataclass(frozen=True)
class ModelStyle:
    key: str          # display name used on every figure
    colour: str       # lines, markers, fills
    text: str         # lettering in the model's hue (>= 4.5:1 on white)
    tint: str         # fc for boxes/cards, always with ec=colour
    marker: str
    marker_scale: float   # optical size compensation per glyph
    dash: object      # fallback for marker-less panels only (see FIGURE_STYLE.md)
    match: tuple      # lower-case substrings that identify the model slug


MODELS = {
    "Qwen": ModelStyle("Qwen", "#543859", "#543859", "#F8F0F9", "D", 0.86,
                       (0, (5.0, 1.5, 1.0, 1.5)), ("qwen",)),
    "Haiku": ModelStyle("Haiku", "#84442E", "#84442E", "#FDEFEB", "o", 1.00,
                        "solid", ("haiku", "claude")),
    "Flash-Lite": ModelStyle("Flash-Lite", "#3E6D9F", "#3E6D9F", "#EDF2FD", "s", 0.90,
                             (0, (3.5, 1.5)), ("flash-lite", "flash_lite", "gemini")),
    "Grok": ModelStyle("Grok", "#977C38", "#8C722E", "#F7F1E8", "v", 1.10,
                       (0, (1.0, 1.3)), ("grok",)),
    "Luna": ModelStyle("Luna", "#64A184", "#448065", "#E9F5EE", "^", 1.10,
                       (0, (6.0, 1.5, 1.0, 1.5, 1.0, 1.5)), ("luna", "gpt")),
}
# Legend / panel order. Alphabetical by provider would scatter the greyscale code;
# this order follows the paper's model table. Change it only together with that table.
MODEL_ORDER = ("Haiku", "Flash-Lite", "Luna", "Qwen", "Grok")
LIGHTNESS_ORDER = ("Qwen", "Haiku", "Flash-Lite", "Grok", "Luna")   # dark -> light

BAND_ALPHA = 0.16        # confidence ribbons: model colour at this alpha, no edge
LW_DATA = 1.2
LW_THEORY = 1.0
LW_RULE = 0.8
MARKER_SIZE = 4.0        # points, before per-glyph scale
MARKER_EDGE = 0.5        # white keyline so overlapping markers stay separable

# --------------------------------------------------------------------------- references
THEORY = dict(color=INK, lw=LW_THEORY, ls=(0, (4.5, 2.0)), marker="None", zorder=2.5)
THEORY_SECONDARY = dict(color=LINE, lw=0.9, ls=(0, (1.0, 1.6)), marker="None", zorder=2.4)
HUMAN = dict(color=MUTED, lw=0.9, ls="solid", marker="o", ms=4.0, mfc=WHITE,
             mec=MUTED, mew=0.9, zorder=2.6)
SCRIPTED = dict(color=LINE, lw=0.9, ls="solid", marker="o", ms=3.4, mfc=WHITE,
                mec=LINE, mew=0.8, zorder=2.2)

# --------------------------------------------------------------------------- maps
DIV_ANCHORS = ("#76321C", "#955640", "#B37B68", "#CEA293", "#E7CAC1", "#F6F6F6",
               "#C3D2E4", "#94AECC", "#648CB2", "#2F6B98", "#024B72")
SEQ_ANCHORS = ("#F4F9FC", "#D3DEE6", "#B3C4D0", "#95AAB9", "#7891A2", "#5D788A",
               "#456071", "#304959", "#1D3340")
CMAP_DIV = LinearSegmentedColormap.from_list("crsd_div", DIV_ANCHORS, N=256)
CMAP_SEQ = LinearSegmentedColormap.from_list("crsd_seq", SEQ_ANCHORS, N=256)
CMAP_DIV.set_bad(WHITE)   # masked cell = hole in the matrix, never a value colour
CMAP_SEQ.set_bad(WHITE)
PAY_COLOURS = {0: SEQ_ANCHORS[1], 2: SEQ_ANCHORS[4], 4: SEQ_ANCHORS[8]}
CMAP_PAY = LinearSegmentedColormap.from_list(
    "crsd_pay", [(0.0, PAY_COLOURS[0]), (0.5, PAY_COLOURS[2]), (1.0, PAY_COLOURS[4])], N=256)
HEATMAP_TEXT_SWITCH_L = 53.0   # cell L* below this takes white text

# --------------------------------------------------------------------------- roles
TEXT_COLOURS = (INK, MUTED, *(m.text for m in MODELS.values()))
FILL_ONLY = (LINE, REGION, GREY_LIGHT, MODELS["Grok"].colour, MODELS["Luna"].colour,
             *(m.tint for m in MODELS.values()))


# =========================================================================== colour math
_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]])
_WHITE_XYZ = np.array([0.95047, 1.0, 1.08883])
MACHADO_2009 = {   # severity 1.0, linear RGB
    "protanopia": np.array([[0.152286, 1.052583, -0.204868],
                            [0.114503, 0.786281, 0.099216],
                            [-0.003882, -0.048116, 1.051998]]),
    "deuteranopia": np.array([[0.367322, 0.860646, -0.227968],
                              [0.280085, 0.672501, 0.047413],
                              [-0.011820, 0.042940, 0.968881]]),
    "tritanopia": np.array([[1.255528, -0.076749, -0.178779],
                            [-0.078411, 0.930809, 0.147602],
                            [0.004733, 0.691367, 0.303900]]),
}


def _hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0


def _to_linear(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def _lin2lab(lin):
    xyz = np.asarray(lin) @ _M_RGB2XYZ.T / _WHITE_XYZ
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


def luminance(colour: str) -> float:
    return float(_to_linear(_hex2rgb(colour)) @ _M_RGB2XYZ[1])


def contrast(fg: str, bg: str = WHITE) -> float:
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def lightness(colour: str) -> float:
    return float(_lin2lab(_to_linear(_hex2rgb(colour)))[0])


def luma601(colour: str) -> float:
    r, g, b = _hex2rgb(colour) * 255
    return 0.299 * r + 0.587 * g + 0.114 * b


def simulate_lab(colour: str, condition: str):
    """CIELAB of a colour as seen under a condition: normal, grey, luma601, or a CVD."""
    lin = _to_linear(_hex2rgb(colour))
    if condition == "normal":
        out = lin
    elif condition == "grey":
        out = np.repeat(lin @ _M_RGB2XYZ[1], 3)
    elif condition == "luma601":
        out = np.repeat(_to_linear(luma601(colour) / 255.0), 3)
    else:
        out = np.clip(MACHADO_2009[condition] @ lin, 0, 1)
    return _lin2lab(out)


def ciede2000(lab1, lab2) -> float:
    """CIEDE2000 (Sharma, Wu & Dalal 2005 formulation)."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    Cb = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0.0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hb = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hb = (h1p + h2p) / 2
    else:
        hb = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * np.cos(np.radians(hb - 30)) + 0.24 * np.cos(np.radians(2 * hb))
         + 0.32 * np.cos(np.radians(3 * hb + 6)) - 0.20 * np.cos(np.radians(4 * hb - 63)))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    RT = -np.sin(np.radians(60 * np.exp(-(((hb - 275) / 25) ** 2)))) * Rc
    SL = 1 + 0.015 * (Lb - 50) ** 2 / np.sqrt(20 + (Lb - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    dL, dC = L2 - L1, C2p - C1p
    return float(np.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2
                         + RT * (dC / SC) * (dH / SH)))


# =========================================================================== role gate
def _audit_roles():
    for c in TEXT_COLOURS:
        if contrast(c) < 4.5:
            raise RuntimeError(f"{c} is declared a text colour but measures "
                               f"{contrast(c):.2f}:1 on white")
    for c in FILL_ONLY:
        if contrast(c) >= 4.5:
            raise RuntimeError(f"{c} now clears {contrast(c):.2f}:1 on white; either promote "
                               "it into TEXT_COLOURS or stop calling it fill-only")
    for m in MODELS.values():
        if contrast(m.colour) < 2.995:
            raise RuntimeError(f"{m.key} colour {m.colour} is below 3:1 for graphical marks")
    Ls = [lightness(MODELS[k].colour) for k in LIGHTNESS_ORDER]
    if any(b - a < 8.0 for a, b in zip(Ls, Ls[1:])):
        raise RuntimeError(f"model lightness steps {np.diff(Ls).round(1)} fall under 8 L*; "
                           "the greyscale code no longer holds")
    if sorted(MODEL_ORDER) != sorted(MODELS):
        raise RuntimeError("MODEL_ORDER and MODELS disagree")
    if len({m.marker for m in MODELS.values()}) != len(MODELS):
        raise RuntimeError("two models share a marker")


_audit_roles()


def audit(verbose: bool = True) -> dict:
    """Re-derive every number quoted in the module header."""
    conds = ["normal", "deuteranopia", "protanopia", "tritanopia", "grey", "luma601"]
    cols = [MODELS[k].colour for k in LIGHTNESS_ORDER]
    out = {}
    for cond in conds:
        labs = [simulate_lab(c, cond) for c in cols]
        pairs = {(LIGHTNESS_ORDER[i], LIGHTNESS_ORDER[j]): ciede2000(labs[i], labs[j])
                 for i, j in itertools.combinations(range(len(cols)), 2)}
        worst = min(pairs, key=pairs.get)
        out[cond] = (pairs[worst], worst)
    out["to_ink"] = min(ciede2000(simulate_lab(c, k), simulate_lab(INK, k))
                        for c in cols for k in conds)
    n = len(DIV_ANCHORS)
    out["div_sign"] = {k: min(ciede2000(simulate_lab(DIV_ANCHORS[i], k),
                                        simulate_lab(DIV_ANCHORS[n - 1 - i], k))
                              for i in range(n // 2))
                       for k in ["deuteranopia", "protanopia", "tritanopia", "grey"]}
    out["div_L"] = [round(lightness(c), 1) for c in DIV_ANCHORS]
    out["seq_L"] = [round(lightness(c), 1) for c in SEQ_ANCHORS]
    out["seq_L_cvd"] = {k: [round(float(simulate_lab(c, k)[0]), 1) for c in SEQ_ANCHORS]
                        for k in ["deuteranopia", "protanopia", "tritanopia"]}
    if verbose:
        print("model   colour   L*    luma601  contrast  text     text-contrast")
        for k in LIGHTNESS_ORDER:
            m = MODELS[k]
            print(f"{k:10} {m.colour} {lightness(m.colour):5.1f} {luma601(m.colour):7.0f} "
                  f"{contrast(m.colour):7.2f}   {m.text} {contrast(m.text):6.2f}")
        for cond in conds:
            v, pair = out[cond]
            print(f"min dE00 {cond:13} {v:5.1f}   worst pair {pair[0]} / {pair[1]}")
        print(f"min dE00 to INK (any condition) {out['to_ink']:.1f}")
        print("diverging L*", out["div_L"])
        print("diverging sign separation (min mirror-pair dE00):",
              {k: round(v, 1) for k, v in out["div_sign"].items()})
        print("sequential L*", out["seq_L"])
        for k, v in out["seq_L_cvd"].items():
            print(f"sequential L* under {k}: {v}")
        for name, c in [("INK", INK), ("MUTED", MUTED), ("LINE", LINE), ("REGION", REGION),
                        ("GREY_LIGHT", GREY_LIGHT)]:
            print(f"{name:10} {c} L*={lightness(c):5.1f} luma={luma601(c):5.0f} "
                  f"on white {contrast(c):5.2f}")
    return out


# =========================================================================== fonts
_FONT_FILES = ("LinLibertine_R_G.ttf", "LinLibertine_RI_G.ttf", "LinLibertine_RB_G.ttf",
               "LinLibertine_RBI_G.ttf")
_FONT_DIRS = (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
              Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
              Path.home() / ".fonts", Path("/usr/share/fonts/truetype/linux-libertine"),
              Path("/Library/Fonts"), Path.home() / "Library/Fonts")
SERIF_STACK = ("Linux Libertine G", "Times New Roman", "DejaVu Serif")


def _register_libertine() -> str:
    """Register the TrueType Libertine files directly (matplotlib's cache may be stale).

    The OpenType builds shipped with TeX (Linux Libertine O, Libertinus) have CFF
    outlines; matplotlib writes Type 42 as FontFile2, which expects TrueType glyf
    outlines, so only the G (TrueType) build is used.
    """
    for d in _FONT_DIRS:
        for f in _FONT_FILES:
            p = d / f
            if p.is_file():
                try:
                    font_manager.fontManager.addfont(str(p))
                except Exception:   # pragma: no cover - unreadable file
                    pass
    names = {f.name for f in font_manager.fontManager.ttflist}
    for fam in SERIF_STACK:
        if fam in names:
            if fam != SERIF_STACK[0]:
                warnings.warn(f"Linux Libertine G not found; figures fall back to {fam}. "
                              "Install the TrueType Libertine (LinLibertine_*_G.ttf).")
            return fam
    return "DejaVu Serif"


FONT_FAMILY = None


def use() -> str:
    """Apply the paper style. Returns the font family actually in use."""
    global FONT_FAMILY
    FONT_FAMILY = _register_libertine()
    for cmap in (CMAP_DIV, CMAP_SEQ, CMAP_PAY):
        if cmap.name not in mpl.colormaps:
            mpl.colormaps.register(cmap)
    mpl.rcParams.update({
        # export
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.bbox": None, "savefig.pad_inches": 0.0,
        "figure.facecolor": WHITE, "savefig.facecolor": WHITE, "axes.facecolor": WHITE,
        "figure.dpi": 150,
        # one spacing strategy for the whole paper
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.w_pad": 2.0 / POINTS_PER_INCH,
        "figure.constrained_layout.h_pad": 2.0 / POINTS_PER_INCH,
        "figure.constrained_layout.wspace": 0.06,
        "figure.constrained_layout.hspace": 0.08,
        # type
        "font.family": "serif", "font.serif": [FONT_FAMILY, *SERIF_STACK[1:]],
        "mathtext.fontset": "custom", "mathtext.rm": FONT_FAMILY,
        "mathtext.it": f"{FONT_FAMILY}:italic", "mathtext.bf": f"{FONT_FAMILY}:bold",
        "mathtext.sf": FONT_FAMILY, "axes.unicode_minus": True,
        "font.size": SIZE_LABEL,
        "axes.titlesize": SIZE_TITLE, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlepad": 4.0,
        "axes.labelsize": SIZE_LABEL, "axes.labelpad": 2.5,
        "xtick.labelsize": SIZE_SMALL, "ytick.labelsize": SIZE_SMALL,
        "legend.fontsize": SIZE_SMALL, "legend.title_fontsize": SIZE_SMALL,
        "figure.titlesize": SIZE_TITLE, "figure.labelsize": SIZE_LABEL,
        "text.color": INK, "axes.labelcolor": INK, "axes.titlecolor": INK,
        # chrome
        "axes.edgecolor": INK, "axes.linewidth": LW_RULE,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": INK, "ytick.color": INK,
        "xtick.major.width": LW_RULE, "ytick.major.width": LW_RULE,
        "xtick.minor.width": 0.6, "ytick.minor.width": 0.6,
        "xtick.major.size": 2.8, "ytick.major.size": 2.8,
        "xtick.minor.size": 1.6, "ytick.minor.size": 1.6,
        "xtick.major.pad": 2.0, "ytick.major.pad": 2.0,
        "xtick.direction": "out", "ytick.direction": "out",
        "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
        "grid.color": LINE, "grid.linewidth": 0.5, "grid.alpha": 0.35,
        # marks
        "lines.linewidth": LW_DATA, "lines.markersize": MARKER_SIZE,
        "lines.markeredgewidth": MARKER_EDGE, "lines.solid_capstyle": "round",
        "lines.dash_capstyle": "butt", "lines.solid_joinstyle": "round",
        "patch.linewidth": 0.6, "hatch.linewidth": 0.5, "hatch.color": MUTED,
        "errorbar.capsize": 0.0,
        "axes.prop_cycle": mpl.cycler(color=[MODELS[k].colour for k in MODEL_ORDER]),
        "image.cmap": "crsd_seq", "image.interpolation": "nearest",
        # legends
        "legend.frameon": False, "legend.handlelength": 1.8, "legend.handleheight": 0.7,
        "legend.handletextpad": 0.45, "legend.columnspacing": 1.0,
        "legend.borderaxespad": 0.2, "legend.borderpad": 0.1, "legend.labelspacing": 0.25,
    })
    return FONT_FAMILY


# =========================================================================== sizing
def width_in(width) -> float:
    if width in ("col", "column"):
        return COL_W
    if width in ("full", "text", "wide"):
        return TEXT_W
    raise ValueError(f"width must be 'col' or 'full', not {width!r}")


def figsize(width="col", *, aspect=None, height_pt=None, nrows=1, ncols=1, square=False,
            colorbar=False, chrome_pt=None):
    """(w, h) in inches. Exactly one of aspect / height_pt / square fixes the height.

    aspect    = height / width of the whole figure
    square    = each panel square; the height is the panel width plus a chrome
                allowance per panel (title, tick labels, axis label), measured on the
                specimens so a heatmap pair leaves no dead band: 64 pt across
                (+42 pt with a colour bar), 52 pt down.
    chrome_pt = (across, down) to override that allowance.
    """
    w = width_in(width)
    if square:
        cw, ch = chrome_pt or (64.0 + (42.0 if colorbar else 0.0), 52.0)
        panel = (w * POINTS_PER_INCH - cw * ncols) / ncols
        return w, nrows * (panel + ch) / POINTS_PER_INCH
    if height_pt is not None:
        return w, height_pt / POINTS_PER_INCH
    return w, w * (0.62 if aspect is None else aspect)


def subplots(width="col", *, aspect=None, height_pt=None, nrows=1, ncols=1, square=False,
             colorbar=False, chrome_pt=None, **kw):
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize(
        width, aspect=aspect, height_pt=height_pt, nrows=nrows, ncols=ncols, square=square,
        colorbar=colorbar, chrome_pt=chrome_pt), **kw)
    fig._crsd_width = width
    return fig, axes


# =========================================================================== drawing helpers
def model_key(name: str) -> str:
    """Map a slug or display name to its MODELS key; fail loud on none or several."""
    if name in MODELS:
        return name
    low = name.lower()
    hits = [k for k, m in MODELS.items() if any(s in low for s in m.match)]
    if len(hits) != 1:
        raise KeyError(f"{name!r} matches {hits or 'no'} model(s)")
    return hits[0]


def model(name: str) -> ModelStyle:
    return MODELS[model_key(name)]


def plot_model(ax, x, y, name, *, yerr=None, band=None, markers=True, label=None, **kw):
    """One model series: solid line + marker (+ vertical CI bars or a ribbon).

    yerr : symmetric half-width, or (lower, upper) half-widths, drawn as bars.
    band : (lo, hi) arrays, drawn as a ribbon at BAND_ALPHA.
    markers=False switches to the dash fallback (only for >30-point series).
    """
    m = model(name)
    x, y = np.asarray(x, float), np.asarray(y, float)
    style = dict(color=m.colour, lw=LW_DATA, zorder=3, label=show(m.key) if label is None else label)
    if markers:
        style.update(ls="solid", marker=m.marker, ms=MARKER_SIZE * m.marker_scale,
                     mfc=m.colour, mec=WHITE, mew=MARKER_EDGE)
    else:
        style.update(ls=m.dash, marker="None")
    style.update(kw)
    if band is not None:
        ax.fill_between(x, band[0], band[1], color=m.colour, alpha=BAND_ALPHA, lw=0,
                        zorder=1.5)
    if yerr is not None:
        ax.errorbar(x, y, yerr=yerr, fmt="none", ecolor=m.colour, elinewidth=0.8,
                    capsize=0, zorder=2.8)
    (line,) = ax.plot(x, y, **style)
    return line


def theory_line(ax, x, y, *, label=None, secondary=False, drawstyle="default", **kw):
    style = dict(THEORY_SECONDARY if secondary else THEORY)
    style.update(kw)
    (line,) = ax.plot(x, y, drawstyle=drawstyle, label=label, **style)
    return line


def region(ax, x0, x1, *, label=None, **kw):
    """Shade a parameter interval that has a theoretical meaning (e.g. paying dominated)."""
    style = dict(color=REGION, lw=0, zorder=0.5)
    style.update(kw)
    return ax.axvspan(x0, x1, label=label, **style)


def label_end(ax, x, y, text, *, colour=INK, dx_pt=3.0, **kw):
    """Direct label to the right of a line end, in points so it does not scale with data."""
    if colour not in TEXT_COLOURS:
        raise ValueError(f"{colour} may not carry lettering; use a text variant")
    return ax.annotate(text, (x, y), xytext=(dx_pt, 0), textcoords="offset points",
                       ha="left", va="center", color=colour, fontsize=SIZE_LABEL,
                       annotation_clip=False, **kw)


def model_handles(names=MODEL_ORDER, markers=True):
    hs = []
    for n in names:
        m = model(n)
        if markers:
            hs.append(Line2D([], [], color=m.colour, lw=LW_DATA, marker=m.marker,
                             ms=MARKER_SIZE * m.marker_scale, mfc=m.colour, mec=WHITE,
                             mew=MARKER_EDGE, label=show(m.key)))
        else:
            hs.append(Line2D([], [], color=m.colour, lw=LW_DATA, ls=m.dash, label=show(m.key)))
    return hs


def legend_top(fig_or_ax, handles, ncols=None, **kw):
    """Frameless one-row legend outside the plot area, above it."""
    ncols = ncols or len(handles)
    if isinstance(fig_or_ax, plt.Figure):
        return fig_or_ax.legend(handles=handles, loc="outside upper center", ncols=ncols, **kw)
    return fig_or_ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0),
                            ncols=ncols, borderaxespad=0.3, **kw)


def panel_title(ax, letter, text=""):
    return ax.set_title(f"{letter}   {text}".rstrip(), loc="left", fontsize=SIZE_TITLE,
                        fontweight="bold", color=INK)


def ramp(colour: str, t: float):
    """The model ramp: WHITE at t = 0, `colour` at t = 1 (linear in sRGB)."""
    a, b = np.array(mpl.colors.to_rgb(WHITE)), np.array(mpl.colors.to_rgb(colour))
    return tuple(a + (b - a) * float(np.clip(t, 0.0, 1.0)))


def cell_ink(fc) -> str:
    """Lettering for a filled cell: white below HEATMAP_TEXT_SWITCH_L, INK above."""
    return WHITE if lightness(mpl.colors.to_hex(fc)) < HEATMAP_TEXT_SWITCH_L else INK


def row_labels(ax, rows, *, axis="y", wrap=False, colour=True):
    """Tick labels for rows that are models (display name, in the model's text colour
    unless colour=False) or references such as "Optimum" (italic INK). Pass colour=False
    beside crsd_div, which borrows the Haiku and Flash-Lite hues (palette cost 1)."""
    ticks = getattr(ax, f"set_{axis}ticks")
    ticks(range(len(rows)), [show(r, wrap=wrap) if r in MODELS else r for r in rows])
    labels = getattr(ax, f"get_{axis}ticklabels")()
    for t, r in zip(labels, rows):
        if r not in MODELS:
            t.set_fontstyle("italic")
        elif colour:
            t.set_color(MODELS[r].text)


def style_matrix_axes(ax):
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0, pad=2.5)


def heatmap(ax, data, *, row_labels, col_labels, cmap="div", vmax=None, vmin=None,
            fmt="{:+.1f}", mask_diagonal=False, text_size=SIZE_SMALL):
    """Annotated matrix. cmap='div' centres on 0 with a symmetric range."""
    data = np.asarray(data, float)
    shown = np.ma.masked_invalid(data.copy())
    if mask_diagonal:
        shown = np.ma.array(shown, mask=np.eye(*data.shape, dtype=bool) | np.ma.getmaskarray(shown))
    if cmap == "div":
        lim = vmax if vmax is not None else float(np.nanmax(np.abs(shown)))
        norm, cm_ = TwoSlopeNorm(0.0, -lim, lim), CMAP_DIV
    else:
        norm = mpl.colors.Normalize(np.nanmin(shown) if vmin is None else vmin,
                                    np.nanmax(shown) if vmax is None else vmax)
        cm_ = CMAP_SEQ
    im = ax.imshow(shown, cmap=cm_, norm=norm, aspect="equal")
    ax.set_xticks(range(data.shape[1]), col_labels)
    ax.set_yticks(range(data.shape[0]), row_labels)
    style_matrix_axes(ax)
    ax.set_xticks(np.arange(-0.5, data.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, data.shape[0]), minor=True)
    ax.tick_params(which="minor", length=0)
    ax.grid(which="minor", axis="both", color=WHITE, lw=1.2, alpha=1.0)   # cell keylines
    for (i, j), v in np.ndenumerate(data):
        if np.ma.getmaskarray(shown)[i, j]:
            if mask_diagonal and i == j:
                ax.text(j, i, "self", ha="center", va="center", fontsize=text_size, color=MUTED)
            continue
        rgba = cm_(norm(v))
        L = lightness(mpl.colors.to_hex(rgba))
        ax.text(j, i, fmt.format(v).replace("-", "−"), ha="center", va="center",
                fontsize=text_size,
                color=WHITE if L < HEATMAP_TEXT_SWITCH_L else INK)
    return im


def colorbar(fig, im, ax, label, **kw):
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03, aspect=22, **kw)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2.0, width=0.6, labelsize=SIZE_SMALL)
    cb.set_label(label, fontsize=SIZE_LABEL)
    return cb


# =========================================================================== gates
def _texts(fig):
    """Every text artist that will actually print: free texts, titles (left, centre,
    right), axis labels, offset texts, legend texts, colour-bar labels, and tick labels
    of ticks inside the view interval only."""
    fig.canvas.draw()
    tick_labels, drawn = set(), set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for t in axis.get_major_ticks() + axis.get_minor_ticks():
                tick_labels.update((id(t.label1), id(t.label2)))
            for t in axis._update_ticks():
                drawn.update(id(lb) for lb in (t.label1, t.label2) if lb.get_visible())
    out = []
    for t in fig.findobj(mpl.text.Text):
        if not t.get_visible() or not t.get_text().strip():
            continue
        if id(t) in tick_labels and id(t) not in drawn:
            continue
        out.append(t)
    return out


def check_text(fig, min_pt=MIN_TEXT_PT):
    bad = [(t.get_text()[:32], t.get_fontsize()) for t in _texts(fig)
           if t.get_fontsize() < min_pt - 1e-6]
    if bad:
        raise RuntimeError(f"text below the {min_pt} pt print floor: {bad}")


def check_overlap(fig, gap_x_pt=2.0, gap_y_pt=1.0, debug_path=None):
    r = fig.canvas.get_renderer()
    texts = _texts(fig)
    boxes = [t.get_window_extent(renderer=r) for t in texts]
    fb = fig.bbox
    sx, sy = gap_x_pt * fig.dpi / POINTS_PER_INCH, gap_y_pt * fig.dpi / POINTS_PER_INCH
    tol = 0.5 * fig.dpi / POINTS_PER_INCH
    problems = []
    for t, b in zip(texts, boxes):
        if b.x0 < fb.x0 - tol or b.x1 > fb.x1 + tol or b.y0 < fb.y0 - tol or b.y1 > fb.y1 + tol:
            problems.append(f"'{t.get_text()[:24]}' leaves the figure")
    for (t1, b1), (t2, b2) in itertools.combinations(zip(texts, boxes), 2):
        if (b1.x0 < b2.x1 + sx and b2.x0 < b1.x1 + sx
                and b1.y0 < b2.y1 + sy and b2.y0 < b1.y1 + sy):
            problems.append(f"'{t1.get_text()[:24]}' ~ '{t2.get_text()[:24]}'")
    if problems:
        if debug_path:
            fig.savefig(debug_path, dpi=300)
        raise RuntimeError("text collision: " + "; ".join(problems))


def check_marks_inside(fig):
    """Markers outside the axes are a defect, not a style choice."""
    for ax in fig.axes:
        x0, x1 = sorted(ax.get_xlim())
        y0, y1 = sorted(ax.get_ylim())
        for ln in ax.get_lines():
            if ln.get_marker() in (None, "None", "", " "):
                continue
            xd, yd = (np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float))
            ok = np.isfinite(xd) & np.isfinite(yd)
            if np.any((xd[ok] < x0) | (xd[ok] > x1) | (yd[ok] < y0) | (yd[ok] > y1)):
                raise RuntimeError(f"'{ln.get_label()}' has markers outside the axes")


def save(fig, path, *, width=None, png=True, proofs=False, title=None, checks=True):
    """Write <path>.pdf at the exact page width (Type 42 fonts), plus an optional PNG
    preview and a greyscale/CVD proof sheet. Returns the PDF path."""
    stem = Path(path).with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)
    width = width or getattr(fig, "_crsd_width", None)
    if width is None:
        raise ValueError("save() needs width='col' or 'full'")
    want = width_in(width) * POINTS_PER_INCH
    got = fig.get_figwidth() * POINTS_PER_INCH
    if abs(want - got) > 0.01:
        raise RuntimeError(f"figure is {got:.2f} pt wide, the page wants {want:.2f} pt")
    if checks:
        check_text(fig)
        check_marks_inside(fig)
        check_overlap(fig, debug_path=str(stem) + "_COLLISION.png")
    pdf = stem.with_suffix(".pdf")
    meta = {"Title": title or stem.name, "Author": None, "Creator": None,
            "CreationDate": None}     # no author: the paper is double-blind
    fig.savefig(pdf, dpi=PDF_RASTER_DPI, metadata=meta)
    raw = pdf.read_bytes()
    box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    if not box or abs(float(box.group(1)) - want) > 0.05:
        raise RuntimeError(f"{pdf.name}: MediaBox width {box and box.group(1)} != {want:.3f}")
    if b"/Type3" in raw:
        raise RuntimeError(f"{pdf.name} embeds a Type 3 font")
    if png:
        png_path = stem.with_suffix(".png")
        fig.savefig(png_path, dpi=PNG_DPI)
        if proofs:
            proof_sheet(png_path)
    return pdf


def proof_sheet(png_path):
    """2 x 2 sheet: CIE greyscale, deuteranopia, protanopia, tritanopia."""
    from PIL import Image, ImageDraw
    img = np.asarray(Image.open(png_path).convert("RGB"), float) / 255.0
    lin = _to_linear(img)
    views = [("greyscale", np.repeat((lin @ _M_RGB2XYZ[1])[..., None], 3, -1))]
    for k in ("deuteranopia", "protanopia", "tritanopia"):
        views.append((k, np.clip(lin @ MACHADO_2009[k].T, 0, 1)))
    h, w = img.shape[:2]
    sheet = Image.new("RGB", (2 * w + 30, 2 * h + 80), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=26)
    except Exception:   # Pillow < 10.1
        font = None
    for n, (name, v) in enumerate(views):
        tile = Image.fromarray((_to_srgb(v) * 255).round().astype(np.uint8))
        x, y = (n % 2) * (w + 30), (n // 2) * (h + 40) + 38
        sheet.paste(tile, (x, y))
        draw.text((x + 4, y - 30), name, fill=(23, 33, 43), font=font)
    out = Path(png_path).with_name(Path(png_path).stem + "_proof.png")
    sheet.save(out)
    return out


if __name__ == "__main__":
    audit()
