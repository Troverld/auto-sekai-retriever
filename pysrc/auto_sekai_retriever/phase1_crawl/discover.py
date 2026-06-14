from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from auto_sekai_retriever.config import Phase1Config, load_phase1_config
from auto_sekai_retriever.utils.io import write_json
from auto_sekai_retriever.utils.paths import normalize_character_name, parse_existing_png, source_filename


@dataclass(frozen=True)
class UrlCandidate:
    character: str
    index: int
    source_url: str
    source_filename: str


def iter_character_directories(image_root: Path) -> list[str]:
    characters = []
    for child in sorted(image_root.iterdir()):
        if child.is_dir():
            characters.append(normalize_character_name(child.name))
    return characters


def infer_existing_max_indices(image_root: Path) -> dict[str, int]:
    maxima: dict[str, int] = {}
    for path in image_root.rglob("*.png"):
        parsed = parse_existing_png(path)
        if parsed is None:
            continue
        character, index = parsed
        maxima[character] = max(index, maxima.get(character, 0))
    return maxima


def build_source_url(character: str, index: int) -> str:
    normalized = normalize_character_name(character)
    return f"https://pjsk.moe/sticker-maker/img/{normalized}/{source_filename(normalized, index)}"


def url_exists(url: str, timeout_seconds: float, user_agent: str) -> bool:
    request = Request(url, method="HEAD", headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    except URLError:
        return False


def discover_urls(
    config: Phase1Config,
    exists_func: Callable[[str, float, str], bool] = url_exists,
    characters: Iterable[str] | None = None,
) -> list[UrlCandidate]:
    candidates: list[UrlCandidate] = []
    max_indices = infer_existing_max_indices(config.image_root)
    character_list = (
        [normalize_character_name(character) for character in characters]
        if characters is not None
        else iter_character_directories(config.image_root)
    )
    for character in character_list:
        floor = max_indices.get(character, 0)
        urls = [(index, build_source_url(character, index)) for index in range(1, config.discovery_probe_limit + 1)]
        with ThreadPoolExecutor(max_workers=config.discovery_max_workers) as executor:
            existence_flags = list(
                executor.map(
                    lambda item: exists_func(item[1], config.request_timeout_seconds, config.user_agent),
                    urls,
                )
            )

        miss_streak = 0
        for (index, url), exists in zip(urls, existence_flags, strict=True):
            if exists:
                candidates.append(
                    UrlCandidate(
                        character=character,
                        index=index,
                        source_url=url,
                        source_filename=source_filename(character, index),
                    )
                )
                miss_streak = 0
            elif index >= floor:
                miss_streak += 1
                if miss_streak >= config.miss_streak_limit:
                    break
    return candidates


def serialize_url_candidates(candidates: Iterable[UrlCandidate]) -> dict[str, object]:
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [asdict(candidate) for candidate in candidates],
    }


def write_url_index(output_path: Path, candidates: Iterable[UrlCandidate]) -> None:
    write_json(output_path, serialize_url_candidates(candidates))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover valid sticker URLs.")
    parser.add_argument("--output", type=Path, default=None, help="Path to write url.json")
    parser.add_argument(
        "--character",
        action="append",
        default=None,
        help="Restrict discovery to one or more lowercase character names.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_phase1_config()
    candidates = discover_urls(config, characters=args.character)
    output_path = args.output or (config.search_root / "url.json")
    write_url_index(output_path, candidates)
    print(json.dumps({"discovered": len(candidates), "output": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
