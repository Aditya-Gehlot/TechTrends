from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


class JsonFileStore(Generic[T]):
    """Small JSON file adapter with atomic replace writes.

    It centralizes file parsing and write behavior so orchestration code does
    not need to know the details of JSON persistence.
    """

    def __init__(self, path: Path | str, default_factory: Callable[[], T]) -> None:
        self.path = Path(path)
        self.default_factory = default_factory

    def read(self) -> T:
        if not self.path.exists():
            return self.default_factory()
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self.default_factory()

    def write(self, value: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f"{self.path.name}.tmp")
        temp_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        temp_path.replace(self.path)
