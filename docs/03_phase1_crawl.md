# Phase 1: 图片爬取实现

本文档定义图片发现、下载、校验、建档与增量更新接口。Phase 1 的核心职责不是单纯“把图拉下来”，而是生成稳定、可复用、可追踪的图片资产清单。

## 1. 输入输出

当前 `public/img/` 已有图片，只作为历史版本保留。

输入：

1. `public/img/` 下的所有文件夹名称统一为小写后即为目标站点名称中 `{character}` 一栏的备选项。
2. 目标站点规则，即为 `https://pjsk.moe/sticker-maker/img/{character}/{name}.png`。一个经验证后合法例子是：`https://pjsk.moe/sticker-maker/img/mafuyu/mafuyu17.png`。

输出：

1. `public/search/url.json`，记录所有爬取的合法链接。
2. `public/search/manifest.json`

## 2. 不要忽略的细节

1. 文件名规范化。
   现有目录大小写并不完全统一，例如 `airi/`、`an/`、`ena/` 与 `Mafuyu/` 并存。输出时统一为小写。
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

## 3. `manifest.json` 建议 schema

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

## 4. 增量更新接口

Phase 5 不单独拆文档，增量约束从第一版起并入本阶段。

核心原则：

1. 以 `sha256` 判断图片内容是否变化。
2. 若仅路径变化但 hash 不变，仍应识别为同一张图。
3. 新图应创建新的 `image_id` 记录；旧图的路径更新不应导致下游语料与向量失效。
4. `manifest.json` 应作为后续 Phase 2 与 Phase 3 的唯一图片索引来源，不直接扫描目录推断状态。

是否引入感知哈希：

1. 第一版可先不做。
2. 如果后续确实存在重命名、轻微裁切、重复导入问题，再加 `phash` 或 `dhash` 作为辅助字段。

## 5. 实现建议

建议拆分为以下职责：

1. `discover.py`
   负责枚举候选 URL 或候选图片编号，产出 `public/search/url.json`。
2. `download.py`
   负责实际下载、跳过逻辑、失败重试和写盘，产出 `public/img_new` 下的文件，排列格式同现有的 `public/img`，以角色名称分列为各个子文件夹。
3. `manifest.py`
   负责计算 hash、尺寸与 `manifest.json` 输出。

流程建议：

1. 先根据规则生成候选 URL 集。
2. 下载成功后立即做文件有效性校验。
3. 校验通过后写入目标路径。
4. 最后统一生成 `manifest.json`。

## 6. 与后续阶段的接口

本阶段对后续阶段至少要稳定提供：

1. `image_id`
2. `relative_path`
3. `sha256`
4. `character`
5. `source_url`

其中 `image_id` 和 `sha256` 是后续缓存与增量更新的核心键。
