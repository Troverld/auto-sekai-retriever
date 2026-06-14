from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from auto_sekai_retriever.phase2_vlm.prompt import PHASE2_BUCKET_SIZES


BUCKET_ORDER = [
    "objective_actions",
    "basic_emotions",
    "meme_phrases",
    "daily_long_sentences",
]

ASCII_PATTERN = re.compile(r"[A-Za-z]")
LEADING_NUMBER_PATTERN = re.compile(r"^\s*[\d一二三四五六七八九十]+[\.、)\-]\s*")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class CleanCorpus:
    buckets: dict[str, list[str]]
    texts: list[str]


def normalize_text(text: str) -> str:
    text = text.strip()
    text = LEADING_NUMBER_PATTERN.sub("", text)
    text = text.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    text = WHITESPACE_PATTERN.sub("", text)
    return text


def is_similar(left: str, right: str, threshold: float = 0.88) -> bool:
    return SequenceMatcher(a=left, b=right).ratio() >= threshold


def dedupe_bucket(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for raw in items:
        normalized = normalize_text(raw)
        if not normalized:
            continue
        if ASCII_PATTERN.search(normalized):
            continue
        if any(is_similar(normalized, existing) for existing in deduped):
            continue
        deduped.append(normalized)
    return deduped


def pad_bucket(bucket_name: str, items: list[str]) -> list[str]:
    target = PHASE2_BUCKET_SIZES[bucket_name]
    if len(items) >= target:
        return items[:target]
    padded = list(items)
    while len(padded) < target:
        padded.append(f"待补全_{bucket_name}_{len(padded) + 1}")
    return padded


def parse_model_output(raw_text: str) -> dict[str, list[str]]:
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("model output must be a JSON object")

    parsed: dict[str, list[str]] = {}
    for bucket_name in BUCKET_ORDER:
        value = payload.get(bucket_name)
        if not isinstance(value, list):
            raise ValueError(f"missing or invalid bucket: {bucket_name}")
        parsed[bucket_name] = [str(item) for item in value]
    return parsed


def clean_corpus_payload(raw_text: str) -> CleanCorpus:
    parsed = parse_model_output(raw_text)
    buckets: dict[str, list[str]] = {}
    flattened: list[str] = []
    for bucket_name in BUCKET_ORDER:
        cleaned = dedupe_bucket(parsed[bucket_name])
        filled = pad_bucket(bucket_name, cleaned)
        buckets[bucket_name] = filled
        flattened.extend(filled)
    return CleanCorpus(buckets=buckets, texts=flattened)

