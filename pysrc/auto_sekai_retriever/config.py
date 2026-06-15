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


@dataclass(frozen=True)
class Phase3Config:
    data_root: Path
    search_root: Path
    cache_root: Path
    embedding_model: str
    embedding_batch_size: int
    embedding_pooling: str = "none"


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


def load_phase3_config(project_root: Path | None = None) -> Phase3Config:
    root = project_root or Path.cwd()
    data_root = Path(os.getenv("ASR_DATA_ROOT", root / "data"))
    search_root = Path(os.getenv("ASR_OUTPUT_ROOT", root / "public" / "search"))
    cache_root = Path(os.getenv("SENTENCE_TRANSFORMERS_HOME", data_root / "cache" / "huggingface"))
    return Phase3Config(
        data_root=data_root,
        search_root=search_root,
        cache_root=cache_root,
        embedding_model=os.getenv("ASR_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
        embedding_batch_size=int(os.getenv("ASR_EMBEDDING_BATCH_SIZE", "16")),
    )
