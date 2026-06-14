from __future__ import annotations

import binascii
import zlib
from pathlib import Path

from auto_sekai_retriever.config import Phase1Config
from auto_sekai_retriever.phase1_crawl.manifest import build_manifest
from auto_sekai_retriever.utils.io import write_json


def tiny_png(width: int = 1, height: int = 1) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"
    ihdr = len(ihdr_data).to_bytes(4, "big") + b"IHDR" + ihdr_data
    ihdr += binascii.crc32(b"IHDR" + ihdr_data).to_bytes(4, "big")
    raw = b"\x00" + b"\x00\x00\x00\x00"
    compressed = zlib.compress(raw)
    idat = len(compressed).to_bytes(4, "big") + b"IDAT" + compressed
    idat += binascii.crc32(b"IDAT" + compressed).to_bytes(4, "big")
    iend = (0).to_bytes(4, "big") + b"IEND" + b"" + binascii.crc32(b"IEND").to_bytes(4, "big")
    return signature + ihdr + idat + iend


def test_build_manifest_from_downloaded_images(tmp_path: Path) -> None:
    output_root = tmp_path / "public" / "img_new"
    search_root = tmp_path / "public" / "search"
    image_path = output_root / "mafuyu" / "mafuyu_17.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(tiny_png())
    write_json(
        search_root / "url.json",
        {
            "version": 1,
            "generated_at": "2026-06-14T00:00:00Z",
            "items": [
                {
                    "character": "mafuyu",
                    "index": 17,
                    "source_url": "https://pjsk.moe/sticker-maker/img/mafuyu/mafuyu17.png",
                    "source_filename": "mafuyu17.png",
                }
            ],
        },
    )

    config = Phase1Config(
        image_root=tmp_path / "public" / "img",
        image_output_root=output_root,
        search_root=search_root,
    )

    payload = build_manifest(config)

    assert payload["version"] == 1
    assert len(payload["images"]) == 1
    image = payload["images"][0]
    assert image["image_id"] == "mafuyu_017"
    assert image["character"] == "mafuyu"
    assert image["relative_path"] == "img_new/mafuyu/mafuyu_17.png"
    assert image["source_url"].endswith("/mafuyu/mafuyu17.png")
    assert image["width"] == 1
    assert image["height"] == 1
