# Phase 2: VLM 语料生成实现

本文档定义图片到文本语料的离线生成方式。目标不是生成“看起来像描述”的文本，而是生成能显著提升中文表情包语义检索效果的高质量语料。

## 1. 调用方式

Phase 2 参考现有 [pysrc/test.py](/home/xtx/auto-sekai-retriever/pysrc/test.py)，说明仓库里已经验证过 OpenAI 兼容 SDK 调用链路可通。正式实现时应把实验代码升级为：

1. 可批量遍历图片
2. 可带图片输入
3. 可重试
4. 可缓存
5. 可校验输出结构

## 2. 模型输出必须强约束

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

## 3. Prompt 与后处理

模型输出不稳定，这一层必须做后处理：

1. 去重：完全重复句、近似重复句都要去。
2. 长度限制：过长长句会拖累 embedding 质量，建议限制字符数。
3. 风格约束：禁止输出英文、解释性句子、编号前缀、括号注释。
4. 安全清洗：过滤明显错角色、错误视觉事实、与图无关内容。
5. 不足补齐：若某一类不足指定数量，允许发起单图二次补全请求。

建议保留两份文件：

1. `data/interim/corpus_raw.jsonl`：原始模型响应，便于审计。
2. `public/search/corpus.json`：清洗后正式产物。

## 4. `corpus.json` 建议 schema

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

## 5. 断点续跑与缓存

这是最容易遗漏但必须做的部分。

1. 以 `image_id` 为粒度缓存 Phase 2 结果。
2. 单图成功后立即落盘，不要等全量完成再写。
3. 若图片 `sha256` 未变化且已存在合格语料，默认跳过。
4. 增加 `--force` 选项，允许局部重跑。

## 6. 增量更新接口

Phase 5 在本阶段的具体落点如下：

1. Phase 2 必须从 `manifest.json` 读取图片与 `sha256`，而不是自行扫描图片目录拼状态。
2. 若 `image_id` 对应图片的 `sha256` 未变化，且本地已有合格 `corpus` 记录，则默认复用旧结果。
3. 若仅路径变化但 `sha256` 不变，应更新 `relative_path`，但不重新标注语料。
4. 若 `sha256` 变化，则视为需要重新标注。

## 7. 实现建议

建议拆分为以下职责：

1. `prompt.py`
   负责系统提示词与输出格式约束。
2. `client.py`
   负责模型调用、重试、超时与响应解析。
3. `generate_corpus.py`
   负责批处理调度、断点续跑与正式产物生成。
4. `postprocess.py`
   负责清洗、去重、补齐与结构校验。

优先级上，应先验证小规模样本的语料质量，再扩大到全量处理。
