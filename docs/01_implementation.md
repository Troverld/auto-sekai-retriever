# Implementation Plan

本文档用于把 [00_overview.md](/home/xtx/auto-sekai-retriever/docs/00_overview.md) 的目标落到可执行实现层，补充目录规范、数据格式、测试、缓存、增量更新与工程约束。默认原则是：离线预处理尽量可复现、可断点续跑、可校验；前端运行时尽量只消费静态产物，不依赖任何后端。

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

## 4. Phase 1: 图片爬取实现细节

## 4.1 输入输出

输入：

1. 当前 `public/img/` 已有图片
2. 目标站点规则，例如 `https://pjsk.moe/sticker-maker/img/{character}/{name}.png`

输出：

1. 更新后的 `public/img/`
2. `public/search/manifest.json`
3. 可选的下载日志 `data/interim/download_report.json`

## 4.2 不要忽略的细节

1. 文件名规范化。
   现有目录大小写并不完全统一，例如 `airi/`、`an/`、`ena/` 与 `Mafuyu/` 并存。需要定义唯一规范 ID，避免后续路径和主键混乱。
2. 图片主键不要直接绑定相对路径。
   建议定义稳定 `image_id`，例如 `mafuyu_001`、`airi_018`。
3. 保留源信息。
   `manifest.json` 中记录 `source_url`、`character`、`filename`、`width`、`height`、`sha256`。
4. 下载必须幂等。
   已存在且 hash 未变化的文件跳过。
5. 下载必须支持断点续跑。
   单图失败不影响整体，最终输出失败列表。
6. 图片有效性校验。
   下载后至少校验 HTTP 状态、MIME、文件大小、PNG 可打开性。

## 4.3 `manifest.json` 建议 schema

```json
{
  "version": 1,
  "generated_at": "2026-06-14T00:00:00Z",
  "images": [
    {
      "image_id": "mafuyu_017",
      "character": "mafuyu",
      "relative_path": "img/Mafuyu/Mafuyu_17.png",
      "source_url": "https://pjsk.moe/sticker-maker/img/mafuyu/mafuyu17.png",
      "sha256": "...",
      "width": 512,
      "height": 512
    }
  ]
}
```

## 5. Phase 2: VLM 语料生成实现细节

## 5.1 调用方式

Phase 2 参考现有 [pysrc/test.py](/home/xtx/auto-sekai-retriever/pysrc/test.py)，说明仓库里已经验证过 OpenAI 兼容 SDK 调用链路可通。正式实现时应把实验代码升级为：

1. 可批量遍历图片
2. 可带图片输入
3. 可重试
4. 可缓存
5. 可校验输出结构

## 5.2 模型输出必须强约束

不要只让模型返回自由文本。建议强制返回 JSON，对四类语料分别输出数组：

```json
{
  "objective_actions": ["..."],
  "basic_emotions": ["..."],
  "meme_phrases": ["..."],
  "daily_long_sentences": ["..."]
}
```

数量约束：

1. `objective_actions`: 3
2. `basic_emotions`: 3
3. `meme_phrases`: 7
4. `daily_long_sentences`: 7

总数固定为 20，便于后续 embedding 与前端检索逻辑保持定长。

写 prompt 时显式要求不能输出重复描述。pytest 时为节省 token，可以使用 `OPENAI_MODEL=gpt-5.2` + `REASONING_EFFORT=low`；真实标注时使用 `5.5` + `medium`。

## 5.3 Prompt 与后处理

模型输出不稳定，这一层必须做后处理：

1. 去重：完全重复句、近似重复句都要去。
2. 长度限制：过长长句会拖累 embedding 质量，建议限制字符数。
3. 风格约束：禁止输出英文、解释性句子、编号前缀、括号注释。
4. 安全清洗：过滤明显错角色、错误视觉事实、与图无关内容。
5. 不足补齐：若某一类不足指定数量，允许发起单图二次补全请求。

建议保留两份文件：

1. `data/interim/corpus_raw.jsonl`：原始模型响应，便于审计。
2. `public/search/corpus.json`：清洗后正式产物。

## 5.4 `corpus.json` 建议 schema

```json
{
  "version": 1,
  "generated_at": "2026-06-14T00:00:00Z",
  "model": "gpt-5.4",
  "items": [
    {
      "image_id": "mafuyu_017",
      "relative_path": "img/Mafuyu/Mafuyu_17.png",
      "texts": [
        "叹气",
        "无语",
        "差不多得了"
      ],
      "buckets": {
        "objective_actions": ["叹气", "扶额", "侧目"],
        "basic_emotions": ["无语", "烦躁", "冷淡"],
        "meme_phrases": ["差不多得了", "你继续", "行行行都对"],
        "daily_long_sentences": [
          "这天是一秒钟也聊不下去了"
        ]
      }
    }
  ]
}
```

其中：

1. `texts` 为最终平铺后的 20 句数组。
2. `buckets` 用于保留语义分桶，方便后续重新调权、诊断质量。

## 5.5 断点续跑与缓存

这是最容易遗漏但必须做的部分。

1. 以 `image_id` 为粒度缓存 Phase 2 结果。
2. 单图成功后立即落盘，不要等全量完成再写。
3. 若图片 `sha256` 未变化且已存在合格语料，默认跳过。
4. 增加 `--force` 选项，允许局部重跑。

## 6. Phase 3: Embedding 生成实现细节

## 6.1 模型与缓存

离线 embedding 建议先按设计使用 `BAAI/bge-large-zh-v1.5`。HuggingFace 模型必须缓存到本地，并写入 `.gitignore`。

建议本地缓存目录：

```text
data/cache/huggingface/
```

`.gitignore` 至少应覆盖：

```gitignore
.venv/
__pycache__/
.pytest_cache/
.env
data/cache/
data/interim/
```

如果后续把 `data/processed/` 也作为本地产物而非发布产物，同样应忽略。

## 6.2 向量格式

先以实现简单为第一目标，可以先输出 JSON；但要注意后续体积与加载速度。

推荐正式结构：

```json
{
  "version": 1,
  "generated_at": "2026-06-14T00:00:00Z",
  "model": "BAAI/bge-large-zh-v1.5",
  "dimension": 1024,
  "pooling": "none",
  "items": [
    {
      "image_id": "mafuyu_017",
      "vectors": [
        [0.01, -0.02, 0.03]
      ]
    }
  ]
}
```

实现建议：

1. 先做 L2 normalize，再写出。
2. 每张图严格对应 20 个向量。
3. 写出前做维度校验。

## 6.3 量化与体积控制

虽然设计里提到 2-3 MB，但这取决于存储格式，不能默认成立。

建议：

1. 初版直接用 `float32` JSON，先打通流程。
2. 第二版考虑 `float16` 或 `int8` 量化。
3. 如果 JSON 体积过大，改成 `embeddings.bin + embeddings.meta.json`，前端按二进制读入。

如果前端后续使用 `Transformers.js` 只负责 query embedding，那么静态向量库完全可以用更紧凑的二进制表示。

## 6.4 模型一致性问题

这是另一个容易被忽略的点：离线 embedding 模型和前端 query embedding 模型如果不是同一族，召回质量会明显受损。

建议约束：

1. 离线模型与前端模型必须属于同一 embedding family。
2. 若离线使用 `bge-large-zh-v1.5`，前端至少使用其同系列小模型或兼容导出版本。
3. 上线前必须用固定查询集做 A/B 验证，确认小模型 query 不会明显劣化。

## 7. Phase 4: 前端检索产物约定

Python 侧需要为前端消费方式负责，不能只产出“理论正确”的文件。

建议前端静态产物放在：

```text
public/search/
  manifest.json
  corpus.json
  embeddings.json
```

前端读取时只依赖这三类文件，不扫描 `public/img/` 目录。

原因：

1. 浏览器侧无法直接列目录。
2. 前端需要稳定元数据，不应反推文件名。
3. 后续新增权重字段、标签类别、时间戳时更容易扩展。

## 8. 测试策略

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

## 9. 日志、错误处理与可观测性

离线流水线如果没有日志，后续排查成本会很高。

建议：

1. 统一使用结构化日志，至少打印 `phase`、`image_id`、`status`。
2. 每个 phase 结束输出统计摘要：总数、成功数、跳过数、失败数。
3. 失败项单独落盘，例如 `data/interim/failures_phase2.jsonl`。

## 10. 增量更新策略

Phase 5 里提到的“增量导入”建议从第一版就留接口。

核心原则：

1. 以 `sha256` 判断图片内容是否变化。
2. 若仅路径变化但 hash 不变，复用旧语料与旧向量。
3. 若 hash 变化，视为新图，重新跑 Phase 2 和 Phase 3。
4. 所有正式产物都用 `image_id` 关联，不用路径做主键。

是否引入感知哈希：

1. 第一版可先不做。
2. 如果后续确实存在重命名、轻微裁切、重复导入问题，再加 `phash` 或 `dhash` 作为辅助字段。

## 11. 建议 CLI 入口

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

## 12. 第一阶段落地顺序

建议按下面顺序推进，而不是并行乱写：

1. 建立 `pyproject.toml`、`uv.lock`、`pytest` 基础设施。
2. 建 `schemas.py` 与 `config.py`，先把产物格式定死。
3. 把 `pysrc/test.py` 的 API 调用整理成 `phase2_vlm/client.py`。
4. 先对少量图片跑通 Phase 2，生成小规模 `corpus.json`。
5. 再实现 Phase 3，先不做量化，优先验证前端可读。
6. 最后补 Phase 1 批量爬取与 Phase 5 增量更新。

原因很简单：当前项目最大不确定性不在爬图，而在“语料质量是否足以支撑检索效果”。应先验证 Phase 2 + Phase 3 的召回质量，再投入批量数据工程。

## 13. 当前明确结论

结合现有仓库与新增约束，当前实现基线如下：

1. Python 全部放入 `pysrc/`，与现有 React `src/` 隔离。
2. Python 环境用 `uv` 管理。
3. 测试框架使用 `pytest`。
4. Phase 2 以 [pysrc/test.py](/home/xtx/auto-sekai-retriever/pysrc/test.py) 为调用参考，但要升级为批处理、带缓存、带校验的正式模块。
5. 访问非中文互联网时，bash 命令前显式加 `on_proxy`。
6. HuggingFace 模型缓存到本地目录，并加入 `.gitignore`。
7. 产物主键使用稳定 `image_id`，不要直接用路径。
8. 所有 phase 都必须支持断点续跑与增量更新。

这份文档作为后续 Python 侧实现的工程基准。若后续实际验证发现前端加载 JSON 向量库体积或速度不可接受，应优先调整产物格式，不要修改整体离线生成链路。
