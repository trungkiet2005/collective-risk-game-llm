"""Regression tests: typesetting must not alter the registered plot evidence."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / 'paper/AAMAS/analysis'
SPEC = importlib.util.spec_from_file_location('publication_figures', ANALYSIS / 'publication_figures.py')
sys.path.insert(0, str(ANALYSIS))
pub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pub)


@pytest.mark.parametrize('name,digest', [
    ('fig_knowdo', '810dad1ae1de729f40ee4aed321de86fd95222331068e1c3647afb423f688b6e'),
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
