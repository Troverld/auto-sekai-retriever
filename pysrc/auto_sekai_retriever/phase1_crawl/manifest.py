from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_sekai_retriever.config import Phase1Config, load_phase1_config
from auto_sekai_retriever.utils.hashing import sha256_file
from auto_sekai_retriever.utils.io import write_json
from auto_sekai_retriever.utils.paths import image_id, normalize_character_name, parse_existing_png


@dataclass(frozen=True)
class ManifestImage:
    image_id: str
    character: str
    relative_path: str
    source_url: str
    filename: str
    sha256: str
    width: int
    height: int


def read_png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n") or header[12:16] != b"IHDR":
        raise ValueError(f"invalid png file: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def load_url_map(search_root: Path) -> dict[tuple[str, int], str]:
    url_path = search_root / "url.json"
    if not url_path.exists():
        return {}
    payload: dict[str, Any] = json.loads(url_path.read_text(encoding="utf-8"))
    mapping: dict[tuple[str, int], str] = {}
    for item in payload.get("items", []):
        character = normalize_character_name(item["character"])
        index = int(item["index"])
        mapping[(character, index)] = item["source_url"]
    return mapping


def build_manifest_image(path: Path, image_output_root: Path, source_url_map: dict[tuple[str, int], str]) -> ManifestImage:
    parsed = parse_existing_png(path)
    if parsed is None:
        raise ValueError(f"unexpected file name format: {path.name}")
    character, index = parsed
    width, height = read_png_dimensions(path)
    relative_path = path.relative_to(image_output_root.parent).as_posix()
    source_url = source_url_map.get((character, index), f"https://pjsk.moe/sticker-maker/img/{character}/{character}{index}.png")
    return ManifestImage(
        image_id=image_id(character, index),
        character=normalize_character_name(character),
        relative_path=relative_path,
        source_url=source_url,
        filename=path.name,
        sha256=sha256_file(path),
        width=width,
        height=height,
    )


def build_manifest(config: Phase1Config) -> dict[str, object]:
    source_url_map = load_url_map(config.search_root)
    images = []
    for path in sorted(config.image_output_root.rglob("*.png")):
        images.append(asdict(build_manifest_image(path, config.image_output_root, source_url_map)))
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "images": images,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manifest.json from downloaded images.")
    parser.add_argument("--output", type=Path, default=None, help="Path to write manifest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_phase1_config()
    payload = build_manifest(config)
    output_path = args.output or (config.search_root / "manifest.json")
    write_json(output_path, payload)
    print(json.dumps({"images": len(payload["images"]), "output": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
