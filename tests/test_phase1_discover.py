from __future__ import annotations

from pathlib import Path

from auto_sekai_retriever.config import Phase1Config
from auto_sekai_retriever.phase1_crawl.discover import build_source_url, discover_urls, infer_existing_max_indices


def test_infer_existing_max_indices(tmp_path: Path) -> None:
    image_root = tmp_path / "public" / "img"
    (image_root / "Mafuyu").mkdir(parents=True)
    (image_root / "airi").mkdir(parents=True)
    (image_root / "Mafuyu" / "Mafuyu_01.png").write_bytes(b"")
    (image_root / "Mafuyu" / "Mafuyu_17.png").write_bytes(b"")
    (image_root / "airi" / "Airi_18.png").write_bytes(b"")

    maxima = infer_existing_max_indices(image_root)

    assert maxima == {"mafuyu": 17, "airi": 18}


def test_discover_urls_uses_lowercase_characters_and_stops_after_misses(tmp_path: Path) -> None:
    image_root = tmp_path / "public" / "img"
    (image_root / "Mafuyu").mkdir(parents=True)
    (image_root / "Mafuyu" / "Mafuyu_17.png").write_bytes(b"")

    existing = {
        build_source_url("mafuyu", 1),
        build_source_url("mafuyu", 2),
        build_source_url("mafuyu", 17),
        build_source_url("mafuyu", 18),
    }

    def fake_exists(url: str, timeout: float, user_agent: str) -> bool:
        return url in existing

    config = Phase1Config(
        image_root=image_root,
        image_output_root=tmp_path / "public" / "img_new",
        search_root=tmp_path / "public" / "search",
        discovery_probe_limit=32,
        miss_streak_limit=3,
    )

    discovered = discover_urls(config, exists_func=fake_exists)

    assert [item.index for item in discovered] == [1, 2, 17, 18]
    assert all(item.character == "mafuyu" for item in discovered)

