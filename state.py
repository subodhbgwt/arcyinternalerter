"""Tiny JSON-on-disk store of job IDs we've already alerted on."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("arcy-alerter.state")


class SeenStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("seen"), list):
                self.seen = set(data["seen"])
            elif isinstance(data, list):
                self.seen = set(data)
        except Exception as exc:
            log.warning("Couldn't read %s (%s); starting fresh", self.path, exc)
            self.seen = set()

    def contains(self, job_id: str) -> bool:
        return job_id in self.seen

    def add(self, job_id: str) -> None:
        self.seen.add(job_id)

    def save(self) -> None:
        # Atomic write so a crash mid-write doesn't trash the file.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"seen": sorted(self.seen)}, f, ensure_ascii=False, indent=0)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def __len__(self) -> int:
        return len(self.seen)
