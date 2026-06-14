from __future__ import annotations

import argparse
import json

from auto_sekai_retriever.config import load_phase1_config
from auto_sekai_retriever.phase1_crawl.discover import discover_urls, write_url_index
from auto_sekai_retriever.phase1_crawl.download import download_all
from auto_sekai_retriever.phase1_crawl.manifest import build_manifest
from auto_sekai_retriever.utils.io import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full Phase 1 pipeline.")
    parser.add_argument("--force", action="store_true", help="Re-download existing images.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_phase1_config()

    candidates = discover_urls(config)
    write_url_index(config.search_root / "url.json", candidates)

    results, failures = download_all(candidates, config, force=args.force)

    manifest = build_manifest(config)
    write_json(config.search_root / "manifest.json", manifest)

    print(
        json.dumps(
            {
                "discovered": len(candidates),
                "downloaded": sum(1 for item in results if item.status == "downloaded"),
                "skipped": sum(1 for item in results if item.status == "skipped"),
                "failed": len(failures),
                "manifest_images": len(manifest["images"]),
            },
            ensure_ascii=False,
        )
    )
    if failures:
        write_json(config.search_root / "download_failures.json", {"items": failures})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

