from __future__ import annotations

import json

from auto_sekai_retriever.phase2_vlm.postprocess import clean_corpus_payload


def test_clean_corpus_payload_dedupes_and_pads() -> None:
    raw = json.dumps(
        {
            "objective_actions": ["叹气", " 叹气 ", "扶额"],
            "basic_emotions": ["无语", "烦躁", "无语"],
            "meme_phrases": ["差不多得了", "差不多得了", "你继续"],
            "daily_long_sentences": ["这天是一秒钟也聊不下去了"],
        },
        ensure_ascii=False,
    )

    cleaned = clean_corpus_payload(raw)

    assert len(cleaned.buckets["objective_actions"]) == 3
    assert cleaned.buckets["objective_actions"][:2] == ["叹气", "扶额"]
    assert len(cleaned.buckets["basic_emotions"]) == 3
    assert len(cleaned.buckets["meme_phrases"]) == 7
    assert len(cleaned.buckets["daily_long_sentences"]) == 7
    assert len(cleaned.texts) == 20


def test_clean_corpus_payload_filters_ascii_and_numbering() -> None:
    raw = json.dumps(
        {
            "objective_actions": ["1. 叹气", "OK", "扶额"],
            "basic_emotions": ["1、无语", "烦躁", "冷淡"],
            "meme_phrases": ["A", "你继续", "行行行都对", "差不多得了", "急了急了", "绷不住了", "这就开始了"],
            "daily_long_sentences": [
                "1. 这天是一秒钟也聊不下去了",
                "你要不先冷静一下再说",
                "我现在看你讲话就头疼",
                "这事你开心就好",
                "行那就按你说的来",
                "你是不是对自己太自信了",
                "我已经不想继续解释了",
            ],
        },
        ensure_ascii=False,
    )

    cleaned = clean_corpus_payload(raw)

    assert "OK" not in cleaned.texts
    assert "叹气" in cleaned.texts
    assert all(not item.startswith("1.") for item in cleaned.texts)

