"""Regression tests: typesetting must not alter the registered plot evidence."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import re
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / 'paper/AAMAS/analysis'
SPEC = importlib.util.spec_from_file_location('publication_figures', ANALYSIS / 'publication_figures.py')
sys.path.insert(0, str(ANALYSIS))
pub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pub)


@pytest.mark.parametrize('name,digest', [
    # 19-09-2026: Figure 3 became an arrow plot of the p = 0.1 and 0.9 levels.
    ('fig_knowdo', 'c31c113f549a2e677e3dfb00b0e2e49cb56d94bd5559cc0c36b4e0e412cbf841'),
    ('fig_mixed', '203620af5b59dd7927e2286e7195c661992149f925e638246331cf7f3d524ff3'),
])
def test_registered_estimates_unchanged(name, digest):
    raw = (pub.FIG / f'{name}.csv').read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(raw).hexdigest() == digest


@pytest.mark.parametrize('name,render', [('fig_knowdo', pub.knowdo), ('fig_mixed', pub.mixed)])
def test_sources_are_deterministic_and_order_invariant(name, render, tmp_path, monkeypatch):
    with (pub.FIG / f'{name}.csv').open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    monkeypatch.setattr(pub, 'FIG', tmp_path)
    first = render(rows).read_bytes().replace(b'\r\n', b'\n')
    second = render(list(reversed(rows))).read_bytes().replace(b'\r\n', b'\n')
    assert second == first
    assert b'\\documentclass[border=0pt]{standalone}' in first
    assert b'\\usepackage[T1]{fontenc}' in first


def test_knowdo_levels_match_supplement_table():
    """Figure 3 plots the p = 0.1 and 0.9 rows of the supplement's know-do table with
    the same intervals; a rerun of only one of the two scripts must fail here."""
    import crsd_data as cd
    table = (pub.FIG.parent / 'supplement/tables/s_knowdo.tex').read_text(encoding='utf-8')
    printed, model = {}, None
    for line in table.splitlines():
        cells = [c.strip() for c in line.rstrip('\\ ').split('&')]
        if len(cells) != 6 or not cells[1].startswith('$p='):
            continue
        model = next((k for k, v in cd.DISPLAY.items() if v == cells[0]), model)
        nums = [float(x) for x in re.findall(r'-?\d+\.\d+', ' '.join(cells[2:]).replace('$-$', '-'))]
        printed[(model, float(cells[1][3:-1]))] = nums
    with (pub.FIG / 'fig_knowdo.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 10
    for r in rows:
        keep, keep_lo, keep_hi, paid, paid_lo, paid_hi = printed[(r['model'], float(r['p']))]
        assert [round(float(r[c]) + 1e-9, 2) for c in ('keep', 'keep_lo', 'keep_hi')] == [keep, keep_lo, keep_hi]
        assert [round(float(r[c]) + 1e-9, 1) for c in ('paid', 'paid_lo', 'paid_hi')] == [paid, paid_lo, paid_hi]


def test_rejects_incomplete_model_panel():
    with (pub.FIG / 'fig_knowdo.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    with pytest.raises(ValueError):
        pub.knowdo(rows[:-1])


def test_rejects_bad_intervals_and_outside_markers():
    d = pub.Drawing('fig_knowdo')
    with pytest.raises(ValueError):
        d.ci(10, 50, 20, 5, 'Haiku')
    with pytest.raises(ValueError):
        d.ci(10, 50, 20, 30, 'Haiku')
    with pytest.raises(ValueError):
        d.mark(-1, 50, 'Haiku')
