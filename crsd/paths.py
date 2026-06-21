"""Đường dẫn chuẩn của project (resolve tương đối với package ``crsd``)."""
from __future__ import annotations

from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = PKG_DIR / "configs"
PROMPTS_DIR = PKG_DIR / "prompts"

REPO_ROOT = PKG_DIR.parent
RESULTS_DIR = REPO_ROOT / "results"
DOCS_DIR = REPO_ROOT / "docs"
