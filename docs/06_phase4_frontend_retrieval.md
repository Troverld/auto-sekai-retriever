# Phase 4: 前端检索实现

本文档定义前端运行时如何消费静态产物、生成 query 向量并完成召回。Phase 4 的边界很明确：前端只做读静态文件、算 query embedding、做 Top-K 排序，不承担离线预处理职责。

## 1. 前端检索产物约定

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

## 2. 运行时职责

前端运行时至少负责：

1. 静态加载 `manifest.json`、`corpus.json`、`embeddings.json`
2. 加载浏览器侧 query embedding 模型
3. 用户输入防抖
4. 计算 query 与多向量库之间的相似度
5. 按五个语义桶分别做带权 max
6. 计算所有 25 向量的带权平均相似度
7. 按当前模式权重合成最终分数
8. 支持礼貌/轻松两种模式切换
9. 输出最终 Top-K 图片结果

## 3. 模型加载约束

前端模型建议使用与离线阶段同 family 的轻量版本。

实现上要满足：

1. 首次访问时可静默下载并缓存模型
2. 模型加载失败时有明确降级提示
3. 不阻塞基础页面渲染
4. 后续如有性能瓶颈，可迁移到 Web Worker

## 4. 数据接口约束

前端不要自行假设数据结构，应严格消费固定 schema。

至少依赖以下字段：

1. `manifest.json`
   `image_id`、`relative_path`
2. `corpus.json`
   `image_id`、`texts`
3. `embeddings.json`
   `image_id`、`vectors`、`dimension`
4. 每个向量对应的元数据
   `bucket`、`weight`

如果后续改为 `embeddings.bin + embeddings.meta.json`，前端也只应通过 meta 文件解析索引关系，不写死偏移逻辑到业务组件中。

## 5. 增量更新接口

Phase 5 在本阶段的具体落点如下：

1. 前端始终以 `image_id` 关联图片、语料和向量，不以路径为主键。
2. 只要静态产物遵守 schema，前端无需知道某张图是全量生成还是增量导入。
3. 如果后续增加 `version`、`generated_at`、`texts_hash`、`bucket`、`weight` 等字段，前端应允许非破坏性扩展。

## 6. 性能与演进建议

当前优先级：

1. 先保证结果正确
2. 再观察首屏模型加载体积
3. 最后再优化相似度计算与数据压缩

若出现性能问题，优先考虑：

1. 向量二进制化
2. Web Worker 化相似度计算
3. 更紧凑的 query 模型

不建议一开始就把前端检索层做得过于复杂。
