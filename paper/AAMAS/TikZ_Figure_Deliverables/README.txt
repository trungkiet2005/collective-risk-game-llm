TikZ rebuild of the supplied 3-panel figure
===========================================

Contents
--------
- figure_rebuilt.pdf   : final PDF compiled from TikZ/LaTeX
- figure_rebuilt.tex   : editable TikZ source
- icons/*.png          : icons used by the figure, cropped tight to their visible content
                         and downscaled to 400 px on the long side
- icons/_original/     : the uncropped 1254x1254 icons the crops were made from

Build
-----
Run from this folder:
    pdflatex figure_rebuilt.tex

Requirements
------------
A standard TeX Live or MiKTeX installation with:
- tikz/pgf (libraries arrows.meta, calc, shapes.geometric)
- graphicx
- xcolor
- newtxtext/newtxmath

Notes
-----
- Coordinates in the .tex are in 0.1 mm with y growing downward. Because each icon is
  cropped to its content, the width given to \ico is the width of the drawing itself.
  If an icon is replaced, crop it the same way or it will appear smaller than intended.
- Every table in the figure has six seats, as in the game: self-play and prompt tests
  (six copies of one model), scripted partners (one model beside five scripts), two
  models (three plus three), and the finding-3 table (five fair-share seats paying 20
  and one late dropout paying 18, pool 118 < 120).
- The design cards carry no game counts or finding badges; the badges 1-4 number the
  findings in panel c only. The 47% / 100% target rates at p = 0.9 come from
  tables/num_selection.tex (SelWithinReachHigh, SelAcrossReachHigh).
- The scripted-partner icon has gears above and below its body, so it is drawn at
  5.6 mm to give it the same body height as a 3.9 mm LLM robot.
- All labels, headings, axes, cards, separators, badges, arrows/lines, plots and
  background shapes are native TikZ/LaTeX and remain selectable text in the PDF.
  Raster content is limited to the icons and model logos.
