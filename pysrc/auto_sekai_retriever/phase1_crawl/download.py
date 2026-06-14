from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from auto_sekai_retriever.config import Phase1Config, load_phase1_config
from auto_sekai_retriever.phase1_crawl.discover import UrlCandidate, discover_urls
from auto_sekai_retriever.utils.hashing import sha256_bytes, sha256_file
from auto_sekai_retriever.utils.io import ensure_parent
from auto_sekai_retriever.utils.paths import output_relative_path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class DownloadResult:
    candidate: UrlCandidate
    relative_path: str
    sha256: str
    status: str


def fetch_bytes(url: str, timeout_seconds: float, user_agent: str) -> bytes:
    request = Request(url, method="GET", headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise HTTPError(url, response.status, "unexpected status", response.headers, None)
        return response.read()


def validate_png_bytes(data: bytes) -> None:
    if len(data) < 24:
        raise ValueError("png too small")
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid png signature")
    if data[12:16] != b"IHDR":
        raise ValueError("missing IHDR chunk")


def download_candidate(
    candidate: UrlCandidate,
    config: Phase1Config,
    force: bool = False,
) -> DownloadResult:
    relative_path = output_relative_path(candidate.character, candidate.index)
    output_path = config.image_output_root / candidate.character / Path(relative_path).name
    if output_path.exists() and not force:
        return DownloadResult(
            candidate=candidate,
            relative_path=relative_path,
            sha256=sha256_file(output_path),
            status="skipped",
        )

    last_error: Exception | None = None
    for attempt in range(1, config.request_retries + 1):
        try:
            payload = fetch_bytes(candidate.source_url, config.request_timeout_seconds, config.user_agent)
            validate_png_bytes(payload)
            ensure_parent(output_path)
            output_path.write_bytes(payload)
            return DownloadResult(
                candidate=candidate,
                relative_path=relative_path,
                sha256=sha256_bytes(payload),
                status="downloaded",
            )
        except (HTTPError, URLError, ValueError) as exc:
            last_error = exc
            if attempt < config.request_retries:
                time.sleep(0.25 * attempt)
    raise RuntimeError(f"failed to download {candidate.source_url}: {last_error}") from last_error


def download_all(
    candidates: Iterable[UrlCandidate],
    config: Phase1Config,
    force: bool = False,
) -> tuple[list[DownloadResult], list[dict[str, str]]]:
    results: list[DownloadResult] = []
    failures: list[dict[str, str]] = []
    for candidate in candidates:
        try:
            results.append(download_candidate(candidate, config, force=force))
        except RuntimeError as exc:
            failures.append(
                {
                    "character": candidate.character,
                    "index": str(candidate.index),
                    "source_url": candidate.source_url,
                    "error": str(exc),
                }
            )
    return results, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download discovered sticker URLs.")
    parser.add_argument("--force", action="store_true", help="Re-download existing images.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_phase1_config()
    candidates = discover_urls(config)
    results, failures = download_all(candidates, config, force=args.force)
    print(
        json.dumps(
            {
                "downloaded": sum(1 for item in results if item.status == "downloaded"),
                "skipped": sum(1 for item in results if item.status == "skipped"),
                "failed": len(failures),
            },
            ensure_ascii=False,
        )
    )
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

