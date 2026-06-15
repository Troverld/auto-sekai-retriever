from __future__ import annotations

import argparse
import json
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_sekai_retriever.utils.io import ensure_parent, write_json


INT8_SCALE = 127
INT8_DTYPE = "int8"


@dataclass(frozen=True)
class QuantizedVector:
    values: bytes
    dimension: int


def quantize_vector_int8(vector: list[float]) -> QuantizedVector:
    if not vector:
        raise ValueError("vector must not be empty")
    quantized = array("b")
    for value in vector:
        clipped = max(-1.0, min(1.0, float(value)))
        quantized.append(int(round(clipped * INT8_SCALE)))
    return QuantizedVector(values=quantized.tobytes(), dimension=len(vector))


def dequantize_vector_int8(values: bytes) -> list[float]:
    quantized = array("b")
    quantized.frombytes(values)
    return [value / INT8_SCALE for value in quantized]


def load_embeddings(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_quantized_outputs(payload: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    dimension = int(payload["dimension"])
    items_meta: list[dict[str, Any]] = []
    binary_chunks: list[bytes] = []
    byte_offset = 0
    entry_count = 0

    for item in payload["items"]:
        entries_meta: list[dict[str, Any]] = []
        item_entry_count = 0
        for entry in item["entries"]:
            vector = list(entry["vector"])
            quantized = quantize_vector_int8(vector)
            if quantized.dimension != dimension:
                raise ValueError(f"dimension mismatch for {item['image_id']}")
            binary_chunks.append(quantized.values)
            entries_meta.append(
                {
                    "bucket": entry["bucket"],
                    "weight": float(entry["weight"]),
                    "byte_offset": byte_offset,
                }
            )
            byte_offset += len(quantized.values)
            entry_count += 1
            item_entry_count += 1

        items_meta.append(
            {
                "image_id": item["image_id"],
                "relative_path": item["relative_path"],
                "sha256": item["sha256"],
                "texts_hash": item["texts_hash"],
                "entry_count": item_entry_count,
                "entries": entries_meta,
            }
        )

    meta = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": "embeddings.json",
            "model": payload["model"],
            "pooling": payload["pooling"],
            "corpus_model": payload.get("corpus_model"),
        },
        "format": {
            "dtype": INT8_DTYPE,
            "scale": INT8_SCALE,
            "dimension": dimension,
            "entry_count": entry_count,
            "item_count": len(items_meta),
            "bytes_per_vector": dimension,
            "binary_file": "embeddings.int8.bin",
        },
        "items": items_meta,
    }
    return b"".join(binary_chunks), meta


def write_binary(path: Path, payload: bytes) -> None:
    ensure_parent(path)
    path.write_bytes(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantize embeddings.json into int8 binary + meta outputs")
    parser.add_argument("--input", type=Path, default=Path("public/search/embeddings.json"))
    parser.add_argument("--output-bin", type=Path, default=Path("public/search/embeddings.int8.bin"))
    parser.add_argument("--output-meta", type=Path, default=Path("public/search/embeddings.meta.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_embeddings(args.input)
    binary_payload, meta_payload = build_quantized_outputs(payload)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "input": str(args.input),
                    "output_bin": str(args.output_bin),
                    "output_meta": str(args.output_meta),
                    "bytes": len(binary_payload),
                    "items": meta_payload["format"]["item_count"],
                    "entries": meta_payload["format"]["entry_count"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    write_binary(args.output_bin, binary_payload)
    write_json(args.output_meta, meta_payload)
    print(
        json.dumps(
            {
                "output_bin": str(args.output_bin),
                "output_meta": str(args.output_meta),
                "bytes": len(binary_payload),
                "items": meta_payload["format"]["item_count"],
                "entries": meta_payload["format"]["entry_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
