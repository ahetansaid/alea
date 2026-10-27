"""Traçabilité : chaque résultat est rattaché à ses données, ses décisions et sa version de code."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from . import __version__

RUNS = Path(__file__).resolve().parent.parent / "runs"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, timeout=5).stdout.strip() or None
    except Exception:
        return None


def save_run(manifest: dict, report_text: str, tables: dict) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    d = RUNS / stamp
    d.mkdir(parents=True, exist_ok=True)
    manifest = {**manifest, "horodatage": stamp, "version_alea": __version__, "commit": git_commit()}
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (d / "note_technique.md").write_text(report_text, encoding="utf-8")
    for name, df in tables.items():
        df.to_csv(d / f"{name}.csv", index=False)
    return d
