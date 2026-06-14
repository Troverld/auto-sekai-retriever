## 1. 项目背景与目标

本项目旨在构建一个**高精度的纯前端动漫表情包检索与生成平台**。
当前的聊天软件表情包收藏夹存在检索困难、匹配死板的问题，且手动为几百张表情包打标签费时费力。本项目基于现有的开源贴纸生成器（Fork 自 `sekai-stickers`）前端框架，剥离其固定的文字，引入 **基于语义向量的 AI 检索能力 (Semantic Vector Search)**，使用户可以通过复杂的自然语言（甚至阴阳怪气、长句吐槽）精准召回词意相符的空白表情包，并在前端完成自定义文本的渲染和一键复制。

**核心约束与特点：**
* **零后端部署**：完全依托静态网页托管（GitHub Pages），无 API 服务器，无数据库。
* **极致的检索准度**：超越传统的“文件名匹配”和“字面量模糊搜索”，理解复杂的中文互联网语境。

---

## 2. 核心挑战与技术选型（Why Text Embedding over CLIP?）

在表情包检索任务中，最大的挑战在于 **“视觉客观描述”与“人类复杂情绪/梗”之间的语义鸿沟（Semantic Gap）**。

* **被否决的方案（CLIP 跨模态联合匹配）：** 
  开源的 CLIP 模型存在严重的“字面主义（Literalism）”。例如图片内容为“角色微笑着拿刀”，CLIP 的文本空间只能对齐到“蓝发女孩拿刀”，而无法对齐到用户实际搜索的“你在教我做事？”或“顺着网线打你”。且前端加载中文 CLIP 模型体积过大（>100MB），不符合轻量化要求。
* **最终方案（VLM 数据增强 + 纯文本向量化降维打击）：** 
  利用视觉大模型（VLM）强大的推理能力，**离线**将跨模态任务“翻译”为纯文本语料库（类似于 RAG 中的 HyDE 思想）；随后在线阶段仅需在统一的纯文本向量空间中计算余弦相似度。这不仅解决了语义鸿沟，还将在线计算量降到了最低。

---

## 3. 算法架构规划 (Algorithm Pipeline)

整个系统分为“离线预计算流水线（Python）”和“在线推理端（前端 WebAssembly）”两部分。

### Phase 1: 最新表情包爬取

当前的 `public/img` 中储存的图片并非最新版本。尝试爬取格式形如 `https://pjsk.moe/sticker-maker/img/mafuyu/mafuyu27.png` 或 `https://pjsk.moe/sticker-maker/img/airi/airi30.png` 的所有图片。

### Phase 2: 离线特征工程（Data Augmentation via VLM）
* **任务**：将图片的视觉特征转化为极其丰富的文本语料。
* **工具**：Python + OpenAI 库调用具有识图能力的大模型获取文本标签。
* **策略**：遍历所有图片，要求大模型输出包含如下维度的语料数组，以下四类分别 3+3+7+7 分布：
  1. 客观动作描述（如：叹气、喝茶、翻白眼）
  2. 基础情绪词（如：开心、无语、嘲讽）
  3. 二次元/互联网梗（如：差不多得了、急了急了）
  4. 适合搭配的日常长句（如：这天是一秒钟也聊不下去了）
* **产出**：格式化为 `corpus.json`（图片到语料列表的映射）。

### Phase 3: 离线向量化（Text Embedding Extraction）
* **任务**：将纯文本语料转化为高维稠密向量。
* **工具**：Python + HuggingFace `sentence-transformers` + 高精度中文 text2vec 大模型，如 `BAAI/bge-large-zh-v1.5`。
* **策略**：
  * 读取 `corpus.json`，将每张图的 20 句话分别提取为 1024 维度的特征向量。
  * **不采用**求平均向量（Mean Pooling），而是保留 20 个独立向量（Multi-vector Representation），以最大化长尾语义的召回率。500 张图约生成 10,000 个向量，整体文件大小压缩后极小（约 2-3 MB）。
* **产出**：`embeddings.json`（图片 ID 到 向量矩阵 的映射）。

### Phase 4: 在线实时检索（Browser-side Inference）
* **任务**：纯前端将用户输入转为向量，并进行 Top-K 相似度召回。
* **工具**：React + `Transformers.js` (WebAssembly)。
* **策略**：
  1. **模型加载**：用户首次访问时，后台静默下载并缓存离线处理大模型的量化版本，如 `Xenova/bge-small-zh-v1.5`。
  2. **实时计算**：用户输入文本时（触发 debounce），模型在浏览器端将其转化为 Query 向量。
  3. **距离度量**：执行 C++ 级别的高效循环，计算 Query 向量与 `embeddings.json` 中 10,000 个向量的**余弦相似度（Cosine Similarity）**。
  4. **池化排序**：对属于同一张图片的多个相似度得分取 Max（即只要有一句话击中即可），最终按得分倒序输出 Top 10 图片。

### Phase 5: 可扩展性与后期维护
* **任务**：支持对图片的增量导入。
* **工具**：使用某种模糊哈希方法，让图片-语料列表映射关于图像路径更鲁棒，且支持随时导入新图片集合，并在后端更新 `corpus.json` 和 `embeddings.json` 并推送。

---

## 4. 系统部署视图

系统最终架构为一个纯粹的静态前端应用：

```text
[ 开发者本地环境 ]
  1. 原始图片集
  2. script/vlm_tagger.py (生成 corpus.json)
  3. script/embedder.py   (生成 embeddings.json)
        |
        v (预处理产物推送到 Git)
        
[ GitHub 代码仓库 ] -> (GitHub Actions: CI/CD 自动打包) -> [ GitHub Pages 静态托管 ]
        |
        v (用户浏览器端)
[ 运行时 Web App ]
  - UI 层: React + CSS (复用 sekai-stickers 组件)
  - 检索层: Transformers.js (加载 bge-small-zh) + embeddings.json
  - 渲染层: Fabric.js / Canvas (处理文字缩放、旋转、导出)
  - 导出层: navigator.clipboard.write (一键复制为 Blob 发送)
```

---

## 5. 演进路线图 (Roadmap)

我们采取由粗到细、前后端解耦的敏捷开发模式（前端部分依赖 Cursor / Vibe 编程）。

* **[ ] Step 1: 语料库构建 (Algorithm/Python)**
  - [ ] 编写并运行大模型脚本，清洗脏数据，生成高质量的 `corpus.json`。
* **[ ] Step 2: 降维与向量导出 (Algorithm/Python)**
  - [ ] 编写 embedding 脚本，导出 `embeddings.json` 并验证生成体积。
* **[ ] Step 3: 前端工程初始化 (Frontend/Vibe)**
  - [ ] Fork 并梳理原仓库，移除无用逻辑，保留画廊与 Canvas 编辑器。
  - [ ] 安装 `@xenova/transformers`，编写模型加载与预热 Hook。
* **[ ] Step 4: 核心计算逻辑集成 (Frontend/Vibe)**
  - [ ] 编写前端余弦相似度计算与 Top-K 排序逻辑。
  - [ ] 集成防抖（Debounce）搜索框，与 UI 状态绑定。
* **[ ] Step 5: 部署与测试 (DevOps)**
  - [ ] 配置 `vite.config.js` 和 GitHub Actions 自动化部署流。
  - [ ] 端到端测试：在微信/Telegram 中测试图片的剪贴板复制表现。

---
*编撰提示：本设计文档侧重于确立基于“RAG 思想的纯前端计算”基调。后续开发中，若发现向量计算性能遭遇瓶颈，可引入 Web Worker 进行子线程计算，以确保 UI 线程的丝滑。*