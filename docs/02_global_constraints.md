# Global Constraints

本文档定义项目的全局实现约束。目标是保证 Python 离线流水线、前端静态产物与测试体系从一开始就可复现、可维护、可扩展。

## 1. 实现原则

1. Python 与前端工程解耦。
   Python 代码全部放在 `pysrc/` 下，不与现有 `src/` 混用。
2. 使用 `uv` 管理 Python 环境与依赖。
3. 所有离线步骤都必须支持重复执行，不因中途中断导致全量重跑。
4. 所有生成物都应有明确 schema，并在写入前做校验。
5. 运行时依赖静态文件，最终可直接部署到 GitHub Pages。

## 2. 建议目录结构

建议新增并逐步收敛到如下结构：

```text
docs/
  00_overview.md
  01_implementation.md
  02_global_constraints.md
  03_phase1_crawl.md
  04_phase2_vlm.md
  05_phase3_embedding.md
  06_phase4_frontend_retrieval.md

pysrc/
  test.py
  auto_sekai_retriever/
    __init__.py
    config.py
    logging.py
    schemas.py
    utils/
      paths.py
      hashing.py
      io.py
    phase1_crawl/
      discover.py
      download.py
      manifest.py
    phase2_vlm/
      prompt.py
      client.py
      generate_corpus.py
      postprocess.py
    phase3_embed/
      model.py
      generate_embeddings.py
      quantize.py
    phase5_incremental/
      reconcile.py

tests/
  conftest.py
  test_phase1_manifest.py
  test_phase2_postprocess.py
  test_phase3_embeddings.py
  test_schemas.py

data/
  raw/
  interim/
  processed/
  cache/

public/
  img/
  search/
    corpus.json
    embeddings.json
    manifest.json
```

说明：

1. `pysrc/auto_sekai_retriever/` 放正式实现。
2. `pysrc/test.py` 视为 Phase 2 调 OpenAI 的已验证实验文件，可保留，但后续逻辑应迁移到包内模块。
3. `tests/` 独立于 `pysrc/`，使用 `pytest`。
4. `data/` 用于本地中间产物和缓存；前端最终消费的内容再复制到 `public/search/`。

## 3. Python 工程约定

## 3.1 `uv` 约定

推荐使用：

```bash
uv venv
uv sync
uv run pytest
uv run python -m auto_sekai_retriever.phase2_vlm.generate_corpus
```

建议维护：

1. `pyproject.toml`：声明依赖、pytest 配置、ruff/format 配置。
2. `uv.lock`：锁定依赖版本，保证复现。
3. `.python-version`：固定 Python 主版本，例如 `3.11` 或 `3.12`。

依赖建议至少包括：

1. `openai`
2. `python-dotenv`
3. `pydantic`
4. `httpx`
5. `Pillow`
6. `sentence-transformers`
7. `torch`
8. `numpy`
9. `orjson`
10. `pytest`

如需 CLI，可加 `typer`；如需进度条，可加 `tqdm`。

## 3.2 配置管理

不要把模型名、缓存路径、并发数写死在代码里。统一用配置层管理，推荐：

1. `.env`：本地敏感配置。
2. `.env.example`：非敏感模板。
3. `config.py`：统一读取环境变量并做类型校验。

建议环境变量：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-5.4
REASONING_EFFORT=medium

HF_HOME=./data/cache/huggingface
TRANSFORMERS_CACHE=./data/cache/huggingface
SENTENCE_TRANSFORMERS_HOME=./data/cache/huggingface

ASR_IMAGE_ROOT=./public/img
ASR_OUTPUT_ROOT=./public/search
ASR_DATA_ROOT=./data
ASR_MAX_CONCURRENCY=4
ASR_REQUEST_RETRIES=5
```

## 3.3 代理约定

如果需要访问非中文互联网资源，命令行前显式加 `on_proxy`。包括但不限于：

1. 拉取 HuggingFace 模型
2. 访问 OpenAI 兼容接口
3. 下载远端图片源

示例：

```bash
on_proxy uv run python -m auto_sekai_retriever.phase3_embed.generate_embeddings
```

但是注意，`test.py` 因为使用了代理站，**确定不需要 `on_proxy`。**

## 4. 测试策略

`pytest` 必须从一开始就建，不要等逻辑写完再补。

至少覆盖：

1. schema 测试
   `manifest.json`、`corpus.json`、`embeddings.json` 的序列化与反序列化校验。
2. Phase 1 测试
   文件名规范化、路径转 `image_id`、hash 稳定性。
3. Phase 2 测试
   模型 JSON 输出清洗、去重、补齐逻辑。
4. Phase 3 测试
   向量数量、维度、归一化、空文本防御。
5. 回归测试
   选一小组固定图片样本，保证产物结构与关键字段不退化。

不建议把真实 API 调用做成默认单元测试。建议拆成：

1. 单元测试：纯本地、可离线运行
2. 集成测试：显式标记，例如 `@pytest.mark.integration`

## 5. 日志、错误处理与可观测性

离线流水线如果没有日志，后续排查成本会很高。

建议：

1. 统一使用结构化日志，至少打印 `phase`、`image_id`、`status`。
2. 每个 phase 结束输出统计摘要：总数、成功数、跳过数、失败数。
3. 失败项单独落盘，例如 `data/interim/failures_phase2.jsonl`。

## 6. 建议 CLI 入口

后续建议统一成模块化命令，避免散落脚本：

```bash
uv run python -m auto_sekai_retriever.phase1_crawl.download
uv run python -m auto_sekai_retriever.phase2_vlm.generate_corpus
uv run python -m auto_sekai_retriever.phase3_embed.generate_embeddings
```

每个命令建议支持：

1. `--limit`
2. `--image-id`
3. `--force`
4. `--dry-run`

## 7. 第一阶段落地顺序

建议按下面顺序推进，而不是并行乱写：

1. 建立 `pyproject.toml`、`uv.lock`、`pytest` 基础设施。
2. 建 `schemas.py` 与 `config.py`，先把产物格式定死。
3. 把 `pysrc/test.py` 的 API 调用整理成 `phase2_vlm/client.py`。
4. 先对少量图片跑通 Phase 2，生成小规模 `corpus.json`。
5. 再实现 Phase 3，先不做量化，优先验证前端可读。
6. 最后补 Phase 1 批量爬取与增量更新。

原因很简单：当前项目最大不确定性不在爬图，而在“语料质量是否足以支撑检索效果”。应先验证 Phase 2 + Phase 3 的召回质量，再投入批量数据工程。

## 8. 当前明确结论

结合现有仓库与新增约束，当前实现基线如下：

1. Python 全部放入 `pysrc/`，与现有 React `src/` 隔离。
2. Python 环境用 `uv` 管理。
3. 测试框架使用 `pytest`。
4. Phase 2 以 [pysrc/test.py](/home/xtx/auto-sekai-retriever/pysrc/test.py) 为调用参考，但要升级为批处理、带缓存、带校验的正式模块。
5. 访问非中文互联网时，bash 命令前显式加 `on_proxy`。
6. HuggingFace 模型缓存到本地目录，并加入 `.gitignore`。
7. 产物主键使用稳定 `image_id`，不要直接用路径。
8. 所有 phase 都必须支持断点续跑与增量更新。
