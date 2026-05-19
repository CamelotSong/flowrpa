import json
import os
from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config(path: str | None = None) -> dict:
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(data: dict, path: str | None = None) -> None:
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
