from __future__ import annotations

import json
from pathlib import Path

from auto_sekai_retriever.phase3_embed.generate_embeddings import (
    CorpusItem,
    build_embedding_item,
    can_reuse_embedding,
    load_corpus,
    load_manifest,
    refresh_reused_item,
    write_embeddings,
)
from auto_sekai_retriever.phase3_embed.quantize import (
    INT8_SCALE,
    build_quantized_outputs,
    dequantize_vector_int8,
    quantize_vector_int8,
)


class FakeEmbedder:
    model_name = "fake/bge"
    dimension = 3
    pooling = "none"

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for index, text in enumerate(texts, start=1):
            base = float(len(text) + index)
            norm = (base * base + 1.0 + 4.0) ** 0.5
            vectors.append([base / norm, 1.0 / norm, 2.0 / norm])
        return vectors


def make_corpus_item() -> CorpusItem:
    buckets = {
        "objective_actions": [{"text": f"动作{i}", "weight": 1.0 if i == 0 else 0.8} for i in range(5)],
        "basic_emotions": [{"text": f"情绪{i}", "weight": 0.8} for i in range(3)],
        "meme_phrases": [{"text": f"梗图{i}", "weight": 0.6} for i in range(5)],
        "punchy_chat_quotes": [{"text": f"短句{i}", "weight": 1.0} for i in range(7)],
        "polite_replies": [{"text": f"礼貌{i}", "weight": 0.8} for i in range(5)],
    }
    texts = [item["text"] for bucket in buckets.values() for item in bucket]
    weights = [float(item["weight"]) for bucket in buckets.values() for item in bucket]
    return CorpusItem(
        image_id="mafuyu_017",
        relative_path="img_new/mafuyu/mafuyu_17.png",
        sha256="abc123",
        texts=texts,
        weights=weights,
        buckets=buckets,
        texts_hash="hash123",
    )


def test_build_embedding_item_keeps_bucket_text_weight_alignment() -> None:
    corpus_item = make_corpus_item()
    item = build_embedding_item(corpus_item, FakeEmbedder())

    assert item["image_id"] == "mafuyu_017"
    assert len(item["entries"]) == 25
    assert item["entries"][0]["bucket"] == "objective_actions"
    assert item["entries"][0]["text"] == "动作0"
    assert item["entries"][0]["weight"] == 1.0
    assert len(item["entries"][0]["vector"]) == 3


def test_can_reuse_embedding_requires_matching_sha_and_texts_hash() -> None:
    corpus_item = make_corpus_item()
    existing = {
        "image_id": corpus_item.image_id,
        "relative_path": "img_new/mafuyu/mafuyu_17.png",
        "sha256": corpus_item.sha256,
        "texts_hash": corpus_item.texts_hash,
        "model": "fake/bge",
        "dimension": 3,
        "pooling": "none",
        "entries": [{"bucket": "objective_actions", "text": "动作0", "weight": 1.0, "vector": [1.0, 0.0, 0.0]}] * 25,
    }

    assert can_reuse_embedding(
        corpus_item,
        existing,
        model_name="fake/bge",
        dimension=3,
        pooling="none",
        force=False,
    )
    assert not can_reuse_embedding(
        CorpusItem(**{**corpus_item.__dict__, "texts_hash": "changed"}),
        existing,
        model_name="fake/bge",
        dimension=3,
        pooling="none",
        force=False,
    )


def test_refresh_reused_item_updates_relative_path_without_recompute() -> None:
    corpus_item = make_corpus_item()
    existing = {
        "image_id": corpus_item.image_id,
        "relative_path": "img_old/mafuyu/mafuyu_17.png",
        "sha256": corpus_item.sha256,
        "texts_hash": corpus_item.texts_hash,
        "entries": [{"bucket": "objective_actions", "text": "动作0", "weight": 1.0, "vector": [1.0, 0.0, 0.0]}] * 25,
    }

    refreshed = refresh_reused_item(existing, corpus_item, "fake/bge", 3, "none")

    assert refreshed["relative_path"] == corpus_item.relative_path
    assert refreshed["model"] == "fake/bge"
    assert refreshed["dimension"] == 3


def test_load_manifest_and_corpus_parse_realistic_payloads(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    corpus_path = tmp_path / "corpus.json"
    corpus_item = make_corpus_item()
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-06-15T00:00:00Z",
                "images": [
                    {
                        "image_id": corpus_item.image_id,
                        "relative_path": corpus_item.relative_path,
                        "sha256": corpus_item.sha256,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    corpus_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-06-15T00:00:00Z",
                "model": "gpt-test",
                "items": [
                    {
                        "image_id": corpus_item.image_id,
                        "relative_path": corpus_item.relative_path,
                        "sha256": corpus_item.sha256,
                        "texts": corpus_item.texts,
                        "weights": corpus_item.weights,
                        "buckets": corpus_item.buckets,
                        "texts_hash": corpus_item.texts_hash,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)
    corpus, corpus_model = load_corpus(corpus_path)

    assert manifest[corpus_item.image_id].sha256 == "abc123"
    assert corpus[corpus_item.image_id].texts_hash == "hash123"
    assert corpus_model == "gpt-test"


def test_write_embeddings_emits_expected_top_level_metadata(tmp_path: Path) -> None:
    output = tmp_path / "embeddings.json"
    item = build_embedding_item(make_corpus_item(), FakeEmbedder())
    item["model"] = "fake/bge"
    item["dimension"] = 3
    item["pooling"] = "none"

    write_embeddings(output, embedder=FakeEmbedder(), corpus_model="gpt-test", items=[item])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["model"] == "fake/bge"
    assert payload["dimension"] == 3
    assert payload["pooling"] == "none"
    assert payload["corpus_model"] == "gpt-test"
    assert len(payload["items"]) == 1


def test_quantize_vector_int8_roundtrip_is_bounded() -> None:
    quantized = quantize_vector_int8([-1.0, -0.5, 0.0, 0.5, 1.0])
    restored = dequantize_vector_int8(quantized.values)

    assert quantized.dimension == 5
    assert restored[0] == -1.0
    assert abs(restored[1] - (-64 / INT8_SCALE)) < 1e-9
    assert restored[2] == 0.0
    assert abs(restored[3] - (64 / INT8_SCALE)) < 1e-9
    assert restored[4] == 1.0


def test_build_quantized_outputs_emits_expected_offsets() -> None:
    item = build_embedding_item(make_corpus_item(), FakeEmbedder())
    item["model"] = "fake/bge"
    item["dimension"] = 3
    item["pooling"] = "none"
    payload = {
        "version": 1,
        "generated_at": "2026-06-15T00:00:00Z",
        "model": "fake/bge",
        "dimension": 3,
        "pooling": "none",
        "corpus_model": "gpt-test",
        "items": [item],
    }

    binary_payload, meta_payload = build_quantized_outputs(payload)

    assert len(binary_payload) == 25 * 3
    assert meta_payload["format"]["dtype"] == "int8"
    assert meta_payload["format"]["entry_count"] == 25
    assert meta_payload["items"][0]["entries"][0]["byte_offset"] == 0
    assert meta_payload["items"][0]["entries"][1]["byte_offset"] == 3
