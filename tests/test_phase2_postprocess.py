from __future__ import annotations

import json

from auto_sekai_retriever.phase2_vlm.postprocess import clean_corpus_payload


def test_clean_corpus_payload_dedupes_and_pads() -> None:
    raw = json.dumps(
        {
            "objective_actions": [{"text": "叹气", "weight": 1.0}, {"text": " 叹气 ", "weight": 0.8}, {"text": "扶额", "weight": 0.8}],
            "basic_emotions": [{"text": "无语", "weight": 1.0}, {"text": "烦躁", "weight": 0.8}, {"text": "无语", "weight": 0.6}],
            "meme_phrases": [{"text": "差不多得了", "weight": 1.0}, {"text": "差不多得了", "weight": 0.8}, {"text": "你继续", "weight": 0.6}],
            "punchy_chat_quotes": [{"text": "给老子整不会了", "weight": 1.0}],
            "polite_replies": [{"text": "收到，非常感谢", "weight": 1.0}],
        },
        ensure_ascii=False,
    )

    cleaned = clean_corpus_payload(raw)

    assert len(cleaned.buckets["objective_actions"]) == 5
    assert [item["text"] for item in cleaned.buckets["objective_actions"][:2]] == ["叹气", "扶额"]
    assert len(cleaned.buckets["basic_emotions"]) == 3
    assert len(cleaned.buckets["meme_phrases"]) == 5
    assert len(cleaned.buckets["punchy_chat_quotes"]) == 7
    assert len(cleaned.buckets["polite_replies"]) == 5
    assert len(cleaned.texts) == 25
    assert len(cleaned.weights) == 25


def test_clean_corpus_payload_filters_ascii_and_numbering() -> None:
    raw = json.dumps(
        {
            "objective_actions": [{"text": "1. 叹气", "weight": 1.0}, {"text": "OK", "weight": 0.8}, {"text": "扶额", "weight": 0.6}],
            "basic_emotions": [{"text": "1、无语", "weight": 1.0}, {"text": "烦躁", "weight": 0.8}, {"text": "冷淡", "weight": 0.6}],
            "meme_phrases": [{"text": "A", "weight": 1.0}, {"text": "你继续", "weight": 0.8}, {"text": "行行行都对", "weight": 0.6}, {"text": "差不多得了", "weight": 0.4}, {"text": "急了急了", "weight": 0.2}],
            "punchy_chat_quotes": [
                {"text": "1. 给老子整不会了", "weight": 1.0},
                {"text": "你看我开心吗", "weight": 0.8},
                {"text": "槽点太多不知道从哪吐", "weight": 0.6},
                {"text": "你先演着", "weight": 0.4},
                {"text": "这波真是绝了", "weight": 0.2},
                {"text": "我直接裂开", "weight": 0.8},
                {"text": "别太离谱", "weight": 0.6},
            ],
            "polite_replies": [
                {"text": "1. 收到，非常感谢", "weight": 1.0},
                {"text": "辛苦啦", "weight": 0.8},
                {"text": "非常抱歉给您添麻烦了", "weight": 0.6},
                {"text": "感谢分享", "weight": 0.4},
                {"text": "初次见面请多关照", "weight": 0.2},
            ],
        },
        ensure_ascii=False,
    )

    cleaned = clean_corpus_payload(raw)

    assert "OK" not in cleaned.texts
    assert "叹气" in cleaned.texts
    assert all(not item.startswith("1.") for item in cleaned.texts)
    assert 1.0 in cleaned.weights
