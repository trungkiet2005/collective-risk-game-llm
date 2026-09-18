"""Publication builds must not duplicate documentation on repeated execution."""
import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[2] / 'paper/AAMAS/build_publication.py'
SPEC = importlib.util.spec_from_file_location('publication_build', PATH)
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def test_replacement_containing_old_heading_is_idempotent(tmp_path):
    path = tmp_path / 'README.md'
    path.write_text('## Build\n\nExisting text.\n')
    old, new = '## Build\n', '## Build\n\nAdded instructions.\n'
    build.replace_once(path, old, new)
    first = path.read_bytes()
    build.replace_once(path, old, new)
    assert path.read_bytes() == first


@pytest.mark.parametrize('text', ['unexpected', 'old old'])
def test_changed_or_ambiguous_source_fails_without_writing(tmp_path, text):
    path = tmp_path / 'source.txt'
    path.write_text(text)
    with pytest.raises(ValueError):
        build.replace_once(path, 'old', 'replacement')
    assert path.read_text() == text
