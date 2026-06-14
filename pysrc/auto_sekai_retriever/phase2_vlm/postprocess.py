from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from auto_sekai_retriever.phase2_vlm.prompt import PHASE2_ALLOWED_WEIGHTS, PHASE2_BUCKET_SIZES


BUCKET_ORDER = [
    "objective_actions",
    "basic_emotions",
    "meme_phrases",
    "punchy_chat_quotes",
    "polite_replies",
]

ASCII_PATTERN = re.compile(r"[A-Za-z]")
LEADING_NUMBER_PATTERN = re.compile(r"^\s*[\d一二三四五六七八九十]+[\.、)\-]\s*")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class CleanCorpus:
    buckets: dict[str, list[dict[str, float | str]]]
    texts: list[str]
    weights: list[float]


def normalize_weight(value: object) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid weight: {value}") from exc
    if weight not in PHASE2_ALLOWED_WEIGHTS:
        raise ValueError(f"unsupported weight: {weight}")
    return weight


def normalize_text(text: str) -> str:
    text = text.strip()
    text = LEADING_NUMBER_PATTERN.sub("", text)
    text = text.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    text = WHITESPACE_PATTERN.sub("", text)
    return text


def is_similar(left: str, right: str, threshold: float = 0.88) -> bool:
    return SequenceMatcher(a=left, b=right).ratio() >= threshold


def dedupe_bucket(items: list[dict[str, object]]) -> list[dict[str, float | str]]:
    deduped: list[dict[str, float | str]] = []
    for raw in items:
        normalized = normalize_text(str(raw["text"]))
        if not normalized:
            continue
        if ASCII_PATTERN.search(normalized):
            continue
        if any(is_similar(normalized, str(existing["text"])) for existing in deduped):
            continue
        deduped.append({"text": normalized, "weight": normalize_weight(raw["weight"])})
    return deduped


def pad_bucket(bucket_name: str, items: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    target = PHASE2_BUCKET_SIZES[bucket_name]
    if len(items) >= target:
        return items[:target]
    padded = list(items)
    while len(padded) < target:
        padded.append({"text": f"待补全_{bucket_name}_{len(padded) + 1}", "weight": 0.2})
    return padded


def parse_model_output(raw_text: str) -> dict[str, list[dict[str, object]]]:
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("model output must be a JSON object")

    parsed: dict[str, list[dict[str, object]]] = {}
    for bucket_name in BUCKET_ORDER:
        value = payload.get(bucket_name)
        if not isinstance(value, list):
            raise ValueError(f"missing or invalid bucket: {bucket_name}")
        parsed_items: list[dict[str, object]] = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError(f"bucket item must be object: {bucket_name}")
            if "text" not in item or "weight" not in item:
                raise ValueError(f"bucket item missing text/weight: {bucket_name}")
            parsed_items.append({"text": str(item["text"]), "weight": item["weight"]})
        parsed[bucket_name] = parsed_items
    return parsed


def clean_corpus_payload(raw_text: str) -> CleanCorpus:
    parsed = parse_model_output(raw_text)
    buckets: dict[str, list[dict[str, float | str]]] = {}
    flattened: list[str] = []
    weights: list[float] = []
    for bucket_name in BUCKET_ORDER:
        cleaned = dedupe_bucket(parsed[bucket_name])
        filled = pad_bucket(bucket_name, cleaned)
        buckets[bucket_name] = filled
        flattened.extend(str(item["text"]) for item in filled)
        weights.extend(float(item["weight"]) for item in filled)
    return CleanCorpus(buckets=buckets, texts=flattened, weights=weights)
