# Phase 3: Embedding 生成实现

本文档定义文本语料向向量库的离线转换方式。目标是为前端提供稳定、可加载、召回效果可验证的向量产物。

## 1. 模型与缓存

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

## 2. 向量格式

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
2. 每张图严格对应 25 个向量。
3. 写出前做维度校验。
4. 每个向量都要保留其来源分桶和 `weight`，因为排序不再是简单全局 max。

## 3. 量化与体积控制

虽然设计里提到 2-3 MB，但这取决于存储格式，不能默认成立。

建议：

1. 初版直接用 `float32` JSON，先打通流程。
2. 第二版考虑 `float16` 或 `int8` 量化。
3. 如果 JSON 体积过大，改成 `embeddings.bin + embeddings.meta.json`，前端按二进制读入。

如果前端后续使用 `Transformers.js` 只负责 query embedding，那么静态向量库完全可以用更紧凑的二进制表示。

## 4. 模型一致性问题

这是另一个容易被忽略的点：离线 embedding 模型和前端 query embedding 模型如果不是同一族，召回质量会明显受损。

建议约束：

1. 离线模型与前端模型必须属于同一 embedding family。
2. 若离线使用 `bge-large-zh-v1.5`，前端至少使用其同系列小模型或兼容导出版本。
3. 上线前必须用固定查询集做 A/B 验证，确认小模型 query 不会明显劣化。

## 5. 检索打分规则

不再采用“全 25 向量直接取全局 max”。新的打分方式是六路分数加权：

1. `objective_actions` 内部先求相似度，带上 weight 降序排序，然后加权后相似度再加上 0.4 + 0.3 + 0.2 + 0.1 + 0.0 得到最终得分，因为动作是非排他性的
2. `basic_emotions` 内部相似度带权排序后 0.6 + 0.3 + 0.1，因为情绪是非排他性的
3. `meme_phrases` 内部相似度做带权 max
4. `punchy_chat_quotes` 内部相似度做带权 max
5. `polite_replies` 内部相似度做带权 max
6. 所有 25 个向量做带权平均后，与 query 的相似度

其中“带权”指使用 Phase 2 输出的离散 `weight`。

支持两种模式：

1. 礼貌模式
   六路权重为 `0.2, 0.2, 0.1, 0.1, 0.3, 0.1`
2. 轻松模式
   六路权重为 `0.2, 0.2, 0.2, 0.2, 0.1, 0.1`

顺序固定为：

1. `objective_actions`
2. `basic_emotions`
3. `meme_phrases`
4. `punchy_chat_quotes`
5. `polite_replies`
6. `global_weighted_average`

## 6. 增量更新接口

Phase 5 在本阶段的具体落点如下：

1. Embedding 生成必须基于 `corpus.json` 和 `manifest.json` 联合判断是否重跑。
2. 若 `image_id` 不变且 `sha256` 未变化，同时语料 `texts` 未变化，则复用旧向量。
3. 若图片未变但语料发生变化，也应重算该图全部 25 个向量。
4. 不允许因为路径变化而无谓重算 embedding。

建议后续在向量元数据中记录：

1. `image_id`
2. `sha256`
3. `texts_hash`
4. `model`
5. `dimension`
6. `bucket`
7. `weight`

## 7. 实现建议

建议拆分为以下职责：

1. `model.py`
   负责模型加载、缓存路径配置与 embedding 接口封装。
2. `generate_embeddings.py`
   负责批处理、断点续跑、旧结果复用和正式产物写出。
3. `quantize.py`
   负责后续量化和二进制导出。

第一版先以“检索正确”为目标，不要过早为极致压缩复杂化代码。
