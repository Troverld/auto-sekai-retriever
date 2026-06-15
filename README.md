# Auto Sekai Retriever

Auto Sekai Retriever is a static web app for searching and generating Project Sekai reaction stickers.

It starts from a sticker-generator UI fork, but the current project focuses on a different problem: semantic retrieval. Instead of browsing images manually or relying on filename matching, users can type natural Chinese queries and retrieve fitting blank stickers directly in the browser, then add custom text and export the result.

The app is deployed via github pages. Try it online at <https://troverld.github.io/auto-sekai-retriever>!

## What It Does

- Semantic sticker search in the browser
- Blank sticker selection from the latest `img_new` asset set
- Editable canvas text with Project Sekai-style font controls
- Copy and download generated stickers with no backend dependency

## How Search Works

This project uses an offline-to-online pipeline:

1. Sticker images are collected and normalized offline.
2. A vision-capable model generates structured text annotations for each image.
3. Those text annotations are embedded offline into a compact search index.
4. In the browser, the user query is embedded with `@huggingface/transformers`.
5. The app ranks candidate stickers by cosine similarity against the precomputed vectors.

The runtime stays fully static: no API server, no database, and no online inference endpoint.

## Frontend Features

- `Search character`: semantic retrieval over the prebuilt search dataset
- `Pick character`: manual browsing over the same `img_new` dataset
- Canvas text controls:
  - font family
  - font size
  - line spacing
  - letter spacing
  - stroke width
  - text / stroke color
  - curved text
  - vertical text
  - text behind image
  - custom image upload
  - reset all

The default rendering path now uses the new manifest-driven dataset and no longer depends on the legacy `characters.json` sticker metadata.

## Project Structure

- `src/`: React frontend
- `src/search/`: browser-side search loading, ranking, and embedding logic
- `public/search/`: precomputed manifest, corpus, and vector index
- `public/img_new/`: latest sticker image assets
- `pysrc/`: offline data preparation pipeline
- `docs/`: project notes and implementation documents
- `sekai-stickers/`: local reference fork used for UI and behavior comparison

## Local Development

Requirements:

- Node.js
- npm

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm start
```

Create a production build:

```bash
npm run build
```

## Status

The backend and offline indexing pipeline are already in place. Current work is focused on frontend polish and editor behavior.

## Refreshing the Dataset

The upstream sticker site may add new images at any time. When that happens, refresh the local dataset and rebuild the search assets with the pipeline below.

### 1. Prepare the Python Environment

Requirements:

- Python 3.11+
- A working virtual environment
- An OpenAI-compatible API key for Phase 2

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set the required environment variable for Phase 2:

```bash
export OPENAI_API_KEY=your_key_here
```

Optional environment variables:

```bash
export OPENAI_BASE_URL=...
export OPENAI_MODEL=gpt-5.4
export REASONING_EFFORT=medium
export ASR_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

### 2. Discover and Download New Stickers

Phase 1 discovers valid sticker URLs from the upstream site, downloads new PNGs into `public/img_new/`, and rebuilds `public/search/manifest.json`.

Run the full Phase 1 pipeline:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase1_crawl.run
```

If you want to force re-download existing files:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase1_crawl.run --force
```

Useful targeted discovery command:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase1_crawl.discover --character mafuyu
```

Phase 1 outputs:

- `public/img_new/`
- `public/search/url.json`
- `public/search/manifest.json`
- `public/search/download_failures.json` if any downloads fail

### 3. Regenerate Corpus Annotations

Phase 2 reads `manifest.json`, sends each image through the VLM tagging step, and writes a cleaned corpus to `public/search/corpus.json`.

Run the full corpus generation step:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase2_vlm.generate_corpus
```

Useful partial runs:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase2_vlm.generate_corpus --limit 20
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase2_vlm.generate_corpus --image-id mafuyu_017
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase2_vlm.generate_corpus --force --image-id mafuyu_017
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase2_vlm.generate_corpus --dry-run --limit 20
```

Phase 2 outputs:

- `public/search/corpus.json`
- `data/interim/corpus_raw.jsonl`

Phase 2 is incremental by design:

- unchanged images with valid 25-text corpus entries are skipped
- changed images can be selectively regenerated with `--image-id` or `--force`

### 4. Rebuild Embeddings

Phase 3 converts `corpus.json` into vector assets used by the browser-side search runtime.

Run:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase3_embed.generate_embeddings
```

Useful partial runs:

```bash
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase3_embed.generate_embeddings --limit 20
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase3_embed.generate_embeddings --image-id mafuyu_017
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase3_embed.generate_embeddings --force --image-id mafuyu_017
PYTHONPATH=pysrc python -m auto_sekai_retriever.phase3_embed.generate_embeddings --dry-run --limit 20
```

Depending on your current workflow, this step may regenerate:

- `public/search/embeddings.json`
- or the binary search assets consumed by the frontend, such as:
  - `public/search/embeddings.meta.json`
  - `public/search/embeddings.int8.bin`

If your production frontend is using the binary assets, make sure they are rebuilt from the latest corpus before deploying.

### 5. Verify the Updated Frontend Assets

After the offline pipeline finishes:

1. Confirm that new images exist under `public/img_new/`
2. Confirm that `public/search/manifest.json` includes them
3. Confirm that `public/search/corpus.json` contains 25 texts per updated image
4. Confirm that the embedding assets were regenerated from the latest corpus

Then build the frontend:

```bash
npm run build
```

And test locally:

```bash
npm start
```

### 6. Commit the Updated Assets

Once validation is complete, commit the refreshed static assets:

- `public/img_new/`
- `public/search/manifest.json`
- `public/search/url.json`
- `public/search/corpus.json`
- regenerated embedding assets

Recommended workflow for routine updates:

1. Run Phase 1 to discover and download upstream additions
2. Run Phase 2 only for new or changed images
3. Run Phase 3 to refresh the vector index
4. Rebuild the frontend
5. Commit and deploy

This keeps the site current even when the upstream sticker source adds new content without notice.

## License

Distributed under the MIT License. See [`LICENCE`](./LICENCE).
