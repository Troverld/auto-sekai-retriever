from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Phase1Config:
    image_root: Path
    image_output_root: Path
    search_root: Path
    discovery_probe_limit: int = 64
    miss_streak_limit: int = 5
    discovery_max_workers: int = 12
    request_timeout_seconds: float = 5.0
    request_retries: int = 3
    user_agent: str = "auto-sekai-retriever/0.1"


def load_phase1_config(project_root: Path | None = None) -> Phase1Config:
    root = project_root or Path.cwd()
    return Phase1Config(
        image_root=root / "public" / "img",
        image_output_root=root / "public" / "img_new",
        search_root=root / "public" / "search",
        discovery_probe_limit=int(os.getenv("ASR_DISCOVERY_PROBE_LIMIT", "64")),
        miss_streak_limit=int(os.getenv("ASR_DISCOVERY_MISS_STREAK", "5")),
        discovery_max_workers=int(os.getenv("ASR_DISCOVERY_MAX_WORKERS", "12")),
        request_timeout_seconds=float(os.getenv("ASR_REQUEST_TIMEOUT_SECONDS", "5")),
        request_retries=int(os.getenv("ASR_REQUEST_RETRIES", "3")),
        user_agent=os.getenv("ASR_USER_AGENT", "auto-sekai-retriever/0.1"),
    )
