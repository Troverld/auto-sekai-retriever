from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_sekai_retriever.config import load_phase3_config
from auto_sekai_retriever.phase2_vlm.postprocess import BUCKET_ORDER
from auto_sekai_retriever.phase3_embed.model import SentenceTransformerEmbedder, TextEmbedder, validate_texts
from auto_sekai_retriever.utils.io import write_json


@dataclass(frozen=True)
class ManifestItem:
    image_id: str
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class CorpusItem:
    image_id: str
    relative_path: str
    sha256: str
    texts: list[str]
    weights: list[float]
    buckets: dict[str, list[dict[str, Any]]]
    texts_hash: str


def load_manifest(manifest_path: Path) -> dict[str, ManifestItem]:
    payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        item["image_id"]: ManifestItem(
            image_id=item["image_id"],
            relative_path=item["relative_path"],
            sha256=item["sha256"],
        )
        for item in payload.get("images", [])
    }


def load_corpus(corpus_path: Path) -> tuple[dict[str, CorpusItem], str]:
    payload: dict[str, Any] = json.loads(corpus_path.read_text(encoding="utf-8"))
    items = {
        item["image_id"]: CorpusItem(
            image_id=item["image_id"],
            relative_path=item["relative_path"],
            sha256=item["sha256"],
            texts=list(item["texts"]),
            weights=[float(weight) for weight in item["weights"]],
            buckets=dict(item["buckets"]),
            texts_hash=item["texts_hash"],
        )
        for item in payload.get("items", [])
    }
    return items, str(payload.get("model", ""))


def load_existing_embeddings(embeddings_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    if not embeddings_path.exists():
        return {}, None
    payload: dict[str, Any] = json.loads(embeddings_path.read_text(encoding="utf-8"))
    return {item["image_id"]: item for item in payload.get("items", [])}, payload


def iter_bucket_entries(corpus_item: CorpusItem) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for bucket_name in BUCKET_ORDER:
        bucket_items = corpus_item.buckets.get(bucket_name, [])
        for item in bucket_items:
            entries.append(
                {
                    "bucket": bucket_name,
                    "text": str(item["text"]),
                    "weight": float(item["weight"]),
                }
            )
    return entries


def build_embedding_item(corpus_item: CorpusItem, embedder: TextEmbedder) -> dict[str, Any]:
    validate_texts(corpus_item.texts)
    if len(corpus_item.texts) != 25 or len(corpus_item.weights) != 25:
        raise ValueError(f"{corpus_item.image_id} must have exactly 25 texts and weights")

    metadata_entries = iter_bucket_entries(corpus_item)
    if len(metadata_entries) != len(corpus_item.texts):
        raise ValueError(f"{corpus_item.image_id} bucket entries do not align with texts")

    vectors = embedder.encode_texts(corpus_item.texts)
    if len(vectors) != len(corpus_item.texts):
        raise ValueError(f"{corpus_item.image_id} vector count mismatch")

    entries: list[dict[str, Any]] = []
    for metadata, vector in zip(metadata_entries, vectors, strict=True):
        if len(vector) != embedder.dimension:
            raise ValueError(f"{corpus_item.image_id} vector dimension mismatch")
        entries.append(
            {
                "bucket": metadata["bucket"],
                "text": metadata["text"],
                "weight": metadata["weight"],
                "vector": vector,
            }
        )

    return {
        "image_id": corpus_item.image_id,
        "relative_path": corpus_item.relative_path,
        "sha256": corpus_item.sha256,
        "texts_hash": corpus_item.texts_hash,
        "entries": entries,
    }


def can_reuse_embedding(
    corpus_item: CorpusItem,
    existing: dict[str, Any] | None,
    *,
    model_name: str,
    dimension: int,
    pooling: str,
    force: bool,
) -> bool:
    if force or existing is None:
        return False
    if existing.get("sha256") != corpus_item.sha256:
        return False
    if existing.get("texts_hash") != corpus_item.texts_hash:
        return False
    if existing.get("relative_path") and not isinstance(existing["relative_path"], str):
        return False
    entries = existing.get("entries")
    if not isinstance(entries, list) or len(entries) != 25:
        return False
    if existing.get("model") not in (None, model_name):
        return False
    if existing.get("dimension") not in (None, dimension):
        return False
    if existing.get("pooling") not in (None, pooling):
        return False
    return True


def refresh_reused_item(existing: dict[str, Any], corpus_item: CorpusItem, model_name: str, dimension: int, pooling: str) -> dict[str, Any]:
    refreshed = dict(existing)
    refreshed["relative_path"] = corpus_item.relative_path
    refreshed["sha256"] = corpus_item.sha256
    refreshed["texts_hash"] = corpus_item.texts_hash
    refreshed["model"] = model_name
    refreshed["dimension"] = dimension
    refreshed["pooling"] = pooling
    return refreshed


def write_embeddings(
    embeddings_path: Path,
    *,
    embedder: TextEmbedder,
    corpus_model: str,
    items: list[dict[str, Any]],
) -> None:
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": embedder.model_name,
        "dimension": embedder.dimension,
        "pooling": embedder.pooling,
        "corpus_model": corpus_model,
        "items": items,
    }
    write_json(embeddings_path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 3 embeddings.json from corpus.json")
    parser.add_argument("--manifest", type=Path, default=Path("public/search/manifest.json"))
    parser.add_argument("--corpus", type=Path, default=Path("public/search/corpus.json"))
    parser.add_argument("--output", type=Path, default=Path("public/search/embeddings.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--image-id", action="append", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def select_corpus_items(
    corpus_items: dict[str, CorpusItem],
    manifest_items: dict[str, ManifestItem],
    image_ids: list[str] | None,
    limit: int | None,
) -> list[CorpusItem]:
    ordered = [corpus_items[image_id] for image_id in manifest_items if image_id in corpus_items]
    if image_ids:
        selected_ids = set(image_ids)
        ordered = [item for item in ordered if item.image_id in selected_ids]
    if limit is not None:
        ordered = ordered[:limit]
    return ordered


def main(embedder: TextEmbedder | None = None) -> int:
    args = parse_args()
    manifest_items = load_manifest(args.manifest)
    corpus_items, corpus_model = load_corpus(args.corpus)
    selected = select_corpus_items(corpus_items, manifest_items, args.image_id, args.limit)

    if args.dry_run:
        print(json.dumps({"selected": [item.image_id for item in selected]}, ensure_ascii=False))
        return 0

    runtime_embedder = embedder
    if runtime_embedder is None:
        phase3_config = load_phase3_config()
        runtime_embedder = SentenceTransformerEmbedder(phase3_config)

    existing_items, _ = load_existing_embeddings(args.output)
    items_by_id: dict[str, dict[str, Any]] = {
        image_id: item
        for image_id, item in existing_items.items()
        if image_id in corpus_items and image_id in manifest_items
    }
    reused = 0
    generated = 0

    for corpus_item in selected:
        manifest_item = manifest_items.get(corpus_item.image_id)
        if manifest_item is None:
            raise ValueError(f"missing manifest item for {corpus_item.image_id}")
        normalized_corpus_item = CorpusItem(
            image_id=corpus_item.image_id,
            relative_path=manifest_item.relative_path,
            sha256=manifest_item.sha256,
            texts=corpus_item.texts,
            weights=corpus_item.weights,
            buckets=corpus_item.buckets,
            texts_hash=corpus_item.texts_hash,
        )
        existing = existing_items.get(corpus_item.image_id)
        if can_reuse_embedding(
            normalized_corpus_item,
            existing,
            model_name=runtime_embedder.model_name,
            dimension=runtime_embedder.dimension,
            pooling=runtime_embedder.pooling,
            force=args.force,
        ):
            items_by_id[corpus_item.image_id] = refresh_reused_item(
                existing,
                normalized_corpus_item,
                runtime_embedder.model_name,
                runtime_embedder.dimension,
                runtime_embedder.pooling,
            )
            reused += 1
            continue

        built = build_embedding_item(normalized_corpus_item, runtime_embedder)
        built["model"] = runtime_embedder.model_name
        built["dimension"] = runtime_embedder.dimension
        built["pooling"] = runtime_embedder.pooling
        items_by_id[corpus_item.image_id] = built
        generated += 1

    ordered_items = [items_by_id[image_id] for image_id in manifest_items if image_id in items_by_id]
    write_embeddings(args.output, embedder=runtime_embedder, corpus_model=corpus_model, items=ordered_items)
    print(
        json.dumps(
            {
                "selected": len(selected),
                "generated": generated,
                "reused": reused,
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
