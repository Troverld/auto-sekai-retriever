from __future__ import annotations

import re
from pathlib import Path


IMAGE_NAME_PATTERN = re.compile(r"^(?P<character>[A-Za-z]+)_(?P<index>\d+)\.png$")


def normalize_character_name(name: str) -> str:
    return name.strip().lower()


def titlecase_segment(name: str) -> str:
    normalized = normalize_character_name(name)
    if not normalized:
        raise ValueError("character name cannot be empty")
    return normalized


def image_id(character: str, index: int) -> str:
    return f"{normalize_character_name(character)}_{index:03d}"


def output_filename(character: str, index: int) -> str:
    return f"{normalize_character_name(character)}_{index:02d}.png"


def output_relative_path(character: str, index: int) -> str:
    return f"img_new/{normalize_character_name(character)}/{output_filename(character, index)}"


def source_filename(character: str, index: int) -> str:
    normalized = normalize_character_name(character)
    return f"{normalized}{index}.png"


def parse_existing_png(path: Path) -> tuple[str, int] | None:
    match = IMAGE_NAME_PATTERN.match(path.name)
    if not match:
        return None
    return normalize_character_name(match.group("character")), int(match.group("index"))

