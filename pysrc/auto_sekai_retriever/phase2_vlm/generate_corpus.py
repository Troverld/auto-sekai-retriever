from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_sekai_retriever.phase2_vlm.client import Phase2VLMClient, serialize_raw_response
from auto_sekai_retriever.phase2_vlm.postprocess import clean_corpus_payload
from auto_sekai_retriever.utils.hashing import sha256_bytes
from auto_sekai_retriever.utils.io import ensure_parent, write_json


@dataclass(frozen=True)
class ManifestItem:
    image_id: str
    character: str
    relative_path: str
    sha256: str


def load_manifest(manifest_path: Path) -> list[ManifestItem]:
    payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        ManifestItem(
            image_id=item["image_id"],
            character=item["character"],
            relative_path=item["relative_path"],
            sha256=item["sha256"],
        )
        for item in payload["images"]
    ]


def load_existing_corpus(corpus_path: Path) -> dict[str, dict[str, Any]]:
    if not corpus_path.exists():
        return {}
    payload: dict[str, Any] = json.loads(corpus_path.read_text(encoding="utf-8"))
    return {item["image_id"]: item for item in payload.get("items", [])}


def append_jsonl(path: Path, line: str) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build_corpus_item(manifest_item: ManifestItem, raw_text: str) -> dict[str, Any]:
    cleaned = clean_corpus_payload(raw_text)
    return {
        "image_id": manifest_item.image_id,
        "relative_path": manifest_item.relative_path,
        "sha256": manifest_item.sha256,
        "texts": cleaned.texts,
        "weights": cleaned.weights,
        "buckets": cleaned.buckets,
        "texts_hash": sha256_bytes("\n".join(cleaned.texts).encode("utf-8")),
    }


def write_corpus(corpus_path: Path, model_name: str, items: list[dict[str, Any]]) -> None:
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "items": items,
    }
    write_json(corpus_path, payload)


def should_skip(manifest_item: ManifestItem, existing: dict[str, Any], force: bool) -> bool:
    if force or not existing:
        return False
    return existing.get("sha256") == manifest_item.sha256 and len(existing.get("texts", [])) == 25


def select_manifest_items(
    items: list[ManifestItem],
    image_ids: list[str] | None,
    limit: int | None,
    sample_size: int | None,
    seed: int,
) -> list[ManifestItem]:
    selected = items
    if image_ids:
        image_id_set = set(image_ids)
        selected = [item for item in selected if item.image_id in image_id_set]
    if sample_size is not None:
        rng = random.Random(seed)
        sample_size = min(sample_size, len(selected))
        selected = rng.sample(selected, sample_size)
    if limit is not None:
        selected = selected[:limit]
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 2 corpus.json from manifest.json")
    parser.add_argument("--manifest", type=Path, default=Path("public/search/manifest.json"))
    parser.add_argument("--corpus", type=Path, default=Path("public/search/corpus.json"))
    parser.add_argument("--raw-jsonl", type=Path, default=Path("data/interim/corpus_raw.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--image-id", action="append", default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_items = load_manifest(args.manifest)
    selected = select_manifest_items(manifest_items, args.image_id, args.limit, args.sample_size, args.seed)
    if args.dry_run:
        print(json.dumps({"selected": [item.image_id for item in selected]}, ensure_ascii=False))
        return 0

    existing_map = load_existing_corpus(args.corpus)
    client = Phase2VLMClient()
    items_by_id = dict(existing_map)

    for manifest_item in selected:
        existing = items_by_id.get(manifest_item.image_id)
        if should_skip(manifest_item, existing, args.force):
            continue
        image_path = Path("public") / manifest_item.relative_path
        raw_text = client.tag_image(manifest_item.image_id, manifest_item.character, image_path)
        append_jsonl(args.raw_jsonl, serialize_raw_response(manifest_item.image_id, raw_text))
        items_by_id[manifest_item.image_id] = build_corpus_item(manifest_item, raw_text)

    ordered_items = [items_by_id[item.image_id] for item in manifest_items if item.image_id in items_by_id]
    write_corpus(args.corpus, client.config.model, ordered_items)
    print(json.dumps({"processed": len(selected), "written": len(ordered_items), "corpus": str(args.corpus)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
