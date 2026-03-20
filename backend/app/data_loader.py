from __future__ import annotations

from pathlib import Path
import json
from typing import Any

BASE = Path(__file__).resolve().parents[1]
ART = BASE / "artifacts"


def load_json(name: str, default: Any = None) -> Any:
    path = ART / name
    if default is None:
        default = {}
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))
