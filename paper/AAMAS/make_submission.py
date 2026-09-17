"""Build the AAMAS 2027 upload bundle and refuse it if a submission gate fails.

    python paper/AAMAS/make_submission.py

Writes paper/AAMAS/submission/main.pdf and supplementary_material.zip (supplement.pdf only;
the .tex sources carry repository paths in comments, so they are never shipped). Build both
PDFs first (latexmk -pdf main.tex, then in supplement/). Gates: body ends on page 8 and the
references start page 9; no Type 3 fonts; no author, dates or file paths in PDF metadata;
no identifying or internal strings in the extracted text; no en or em dash outside the
class running header and the bibliography; zip under the 25 MB limit.
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
OUT = HERE / "submission"
MAIN = HERE / "main.pdf"
SUPP = HERE / "supplement" / "supplement.pdf"
ZIP_LIMIT = 25 * 1024 * 1024
BODY_PAGES = 8

LEAKS = [r"\bDao\b", r"\bMinh\b", r"\bchis", r"trungkiet", r"kaggle", r"github", r"proxy",
         r"D:[/\\]", r"PhD_", r"\bTODO\b", r"\bexp_[a-z]", r"\bE[0-9]{1,2}[ab]?\b",
         r"Interface Focus", r"University of Science", r"VNU", r"@gmail"]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def text_of(doc):
    return [p.get_text() for p in doc]


def check_common(doc, name):
    meta = doc.metadata
    if meta.get("author"):
        fail(f"{name}: author in metadata: {meta['author']!r}")
    if meta.get("creationDate") or meta.get("modDate"):
        fail(f"{name}: dates in metadata (time zone leak)")
    for page in doc:
        for f in page.get_fonts():
            if f[2] == "Type3":
                fail(f"{name}: Type 3 font on page {page.number + 1}")
    raw = Path(doc.name).read_bytes()
    if re.search(rb"/PTEX\.FileName", raw):
        fail(f"{name}: included file paths recorded (PTEX.FileName)")
    pages = text_of(doc)
    for pat in LEAKS:
        for i, t in enumerate(pages):
            m = re.search(pat, t, flags=re.I if pat.islower() else 0)
            if m:
                fail(f"{name}: '{m.group(0)}' on page {i + 1} matches {pat}")
    return pages


def main():
    if not MAIN.exists() or not SUPP.exists():
        fail("build main.pdf and supplement/supplement.pdf first")
    main_doc = pymupdf.open(MAIN)
    pages = check_common(main_doc, "main.pdf")
    first_ref = next(i for i, t in enumerate(pages) if "\nReferences\n" in "\n" + t)
    body_before = pages[first_ref].index("References")
    header = "Research Paper Track\nAAMAS 2027, 3–7 May 2027, Hanoi, Vietnam\n"
    if first_ref != BODY_PAGES or not pages[first_ref].startswith(header) or body_before != len(header):
        fail(f"body is not exactly {BODY_PAGES} pages (references on page {first_ref + 1}, "
             f"{body_before - len(header)} characters of body before the heading)")
    for i, t in enumerate(pages[:BODY_PAGES]):
        body = t.replace(header, "").replace("3–7 May 2027", "")
        if "–" in body or "—" in body:
            fail(f"main.pdf: en or em dash in the body on page {i + 1}")
    supp_doc = pymupdf.open(SUPP)
    check_common(supp_doc, "supplement.pdf")

    OUT.mkdir(exist_ok=True)
    shutil.copyfile(MAIN, OUT / "main.pdf")
    zpath = OUT / "supplementary_material.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(SUPP, "supplementary_material.pdf")
    if zpath.stat().st_size > ZIP_LIMIT:
        fail(f"zip is {zpath.stat().st_size} bytes, over the 25 MB limit")
    print(f"OK main.pdf {len(main_doc)} pages (body {BODY_PAGES}), supplement {len(supp_doc)} pages, "
          f"zip {zpath.stat().st_size / 1e6:.2f} MB -> {OUT}")


if __name__ == "__main__":
    main()
