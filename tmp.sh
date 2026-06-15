PYTHONPATH=pysrc python - <<'PY'
import json
from pathlib import Path
from datetime import datetime, timezone

from auto_sekai_retriever.phase2_vlm.generate_corpus import load_manifest, build_corpus_item, write_corpus

manifest_path = Path("public/search/manifest.json")
raw_path = Path("data/interim/corpus_raw.jsonl")
corpus_path = Path("public/search/corpus.json")

manifest_items = {item.image_id: item for item in load_manifest(manifest_path)}

latest = {}
with raw_path.open("r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        image_id = row["image_id"]
        raw_text = row["raw_text"]
        if image_id in manifest_items:
            latest[image_id] = build_corpus_item(manifest_items[image_id], raw_text)

ordered_items = [
    latest[item.image_id]
    for item in manifest_items.values()
    if item.image_id in latest
]

write_corpus(corpus_path, "gpt-5.4", ordered_items)
print(f"rebuilt corpus.json with {len(ordered_items)} items")
PY