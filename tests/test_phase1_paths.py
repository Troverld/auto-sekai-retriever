from __future__ import annotations

from auto_sekai_retriever.utils.paths import image_id, normalize_character_name, output_relative_path, source_filename


def test_phase1_path_helpers() -> None:
    assert normalize_character_name("Mafuyu") == "mafuyu"
    assert image_id("Mafuyu", 17) == "mafuyu_017"
    assert source_filename("Mafuyu", 17) == "mafuyu17.png"
    assert output_relative_path("Mafuyu", 17) == "img_new/mafuyu/mafuyu_17.png"

