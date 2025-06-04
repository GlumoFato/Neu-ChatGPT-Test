"""Simple configuration manager using JSON files."""

import json
from pathlib import Path
from typing import Any, Dict


def load(path: str) -> Dict[str, Any]:
    if Path(path).is_file():
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save(path: str, data: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
