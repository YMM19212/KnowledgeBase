# 基于 MinerU 的医疗文献高质量知识库 RAG

一个面向医疗 PDF 文献的端到端 RAG 知识库系统。项目重点解决医疗文献中常见的复杂版式解析、医学语义级切分、自动化入库、向量检索、可溯源问答和演示级 Web 控制台。

当前版本已经支持本地 MinerU Pipeline：如果你的机器可以运行 `mineru -p <input_path> -o <output_path> -b pipeline`，就可以在前端上传 PDF，系统会自动调用 MinerU 清洗、读取输出结果、切分、向量化、入库并提供 RAG 查询。

> English documentation: [README_en.md](README_en.md)

## 项目亮点

- **本地 MinerU 接入**：支持通过 Web 页面上传 PDF，并调用本机 `mineru` CLI 的 pipeline 模式清洗文献。
- **医疗语义切分**：按医学论文结构切分，而不是固定字数切分，重点保留 Primary outcome、Secondary outcome、Adverse events、Subgroup analysis、Limitations 等上下文。
- **可溯源 RAG**：回答返回 citations、document_id、section_path、page、score 和 source text，证据不足时明确拒答。
- **Jina Embeddings**：内置 Jina Embeddings 支持，默认模型为 `jina-embeddings-v5-text-small`，系统设置页可修改。
- **工程化后端**：FastAPI + SQLite + Chroma/SQLite Vector Store + Pydantic Settings + pytest。
- **专业 Web 控制台**：React + TypeScript + Vite + Tailwind，包含知识库管理、文档管理、RAG 问答、MinerU 配置、评测分析和系统设置。
- **可部署**：提供 Dockerfile、docker-compose、Makefile、CLI 脚本和完整文档。

## 系统架构

```text
医疗 PDF / MinerU JSON / Mock 样例
        │
        ▼
Parser Adapter
MockParser / LocalMinerUParserAdapter / MinerUParserAdapter
        │
        ▼
ParsedDocument 标准结构
标题、摘要、章节、正文、表格、图注、页码、来源
        │
        ▼
MedicalSemanticChunker
章节逻辑 + 医学语义 + 表格/图注独立保留
        │
        ▼
Metadata DB + Vector Store
SQLite + Chroma 或 SQLite fallback
        │
        ▼
RAG Query
Jina / Sentence Transformers / Hash Embedding
        │
        ▼
Answer + Citations + Retrieved Chunks
```

## 功能概览

### 后端能力

- 创建、查看、删除知识库
- 上传/导入文档
- 本地 MinerU Pipeline 清洗并入库
- Mock MinerU 样例导入
- 文档解析状态查看
- chunk 列表查看
- 重建索引
- RAG 查询
- Embedding 设置动态修改
- MinerU CLI 状态检查
- 系统统计与配置查看

### 前端页面

- **Dashboard**：知识库数量、文档数量、chunk 数量、问答次数、最近导入文档、处理流程图。
- **知识库管理**：创建、删除、进入详情。
- **知识库详情**：文档列表、Mock 导入、PDF 上传、本地 MinerU 清洗、重建索引。
- **文档详情**：文档元信息、章节结构、chunk 搜索、content_type 过滤。
- **RAG 问答**：选择知识库、设置 top_k 和 metadata filter、展示 answer/citations/retrieved_chunks。
- **MinerU 配置**：查看本地 MinerU CLI 状态、输出目录、Parser 模式。
- **评测分析**：展示 Recall@K、Citation Coverage、Chunk Completeness 等 mock 指标。
- **系统设置**：展示并修改 Embedding backend、model、Jina API key。

## 快速启动

### 1. 后端

```bash
python -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
make dev
```

后端地址：

- Health: [http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. 前端

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

前端地址：

- Web Console: [http://localhost:5173](http://localhost:5173)

### 3. Docker Compose

```bash
docker compose up --build
```

默认端口：

- 后端：`http://localhost:8000`
- 前端：`http://localhost:5173`

## 配置 Jina Embeddings

项目支持 Jina Embeddings。推荐配置：

```bash
MEDRAG_EMBEDDING_BACKEND=jina
MEDRAG_EMBEDDING_MODEL=jina-embeddings-v5-text-small
MEDRAG_JINA_API_KEY=your_jina_api_key
```

也可以在前端修改：

```text
系统设置 → Embedding 设置
```

说明：

- API key 不会返回明文到前端，只展示脱敏值。
- 前端保存的设置会写入 SQLite 的 `app_settings` 表，优先级高于 `.env`。
- 修改 embedding backend/model 后，已入库文档需要重新向量化。
- 重新向量化入口：`知识库详情 → 重建索引`。

## 使用本地 MinerU Pipeline 入库

如果本机已经安装 MinerU，并且可以运行：

```bash
mineru -p <input_path> -o <output_path> -b pipeline
```

即可在前端进行交互式清洗入库：

```text
知识库 → 进入某个知识库详情 → 本地 MinerU Pipeline 清洗导入
```

页面支持设置：

- 上传 PDF / 图片
- `method`: `auto` / `txt` / `ocr`
- `lang`: `ch` / `en` / `ch_server` / `ch_lite`
- 是否启用 formula parsing
- 是否启用 table parsing

后端执行流程：

```text
上传文件
  -> 保存到 data/storage
  -> 调用 mineru CLI
  -> 输出到 data/mineru_outputs
  -> 优先读取 content_list.json
  -> 回退读取其他 JSON 或 Markdown
  -> 标准化为 ParsedDocument
  -> 医疗语义切分
  -> embedding
  -> 写入向量库
```

相关环境变量：

```bash
MEDRAG_MINERU_CLI_COMMAND=mineru
MEDRAG_MINERU_LOCAL_OUTPUT_DIR=./data/mineru_outputs
MEDRAG_MINERU_CLI_TIMEOUT_SECONDS=1800
```

## 使用已清洗好的 MinerU 目录入库

如果已经有 MinerU 清洗产物，例如本项目的 `CompetitionMinerU/`：

```text
CompetitionMinerU/
  article_name/
    auto/
      *_content_list.json
      *.md
      *_middle.json
      *_origin.pdf
      images/
```

可以直接导入，不会再次运行 MinerU：

```bash
python scripts/ingest_mineru_outputs.py \
  --input-dir CompetitionMinerU \
  --kb-name "Competition Medical Literature KB"
```

或使用 Makefile：

```bash
make ingest-competition
```

脚本会优先读取每篇文献的 `*_content_list.json`，自动标准化、语义切分、向量化并写入知识库。

## 导入样例数据

如果暂时没有 PDF，可先导入样例临床试验文献：

```bash
python scripts/ingest_sample.py --kb-name "Demo Medical KB"
```

或先创建知识库再导入：

```bash
python scripts/create_kb.py --name "Demo Medical KB"
python scripts/ingest_sample.py --kb-id 1
```

## 命令行查询

```bash
python scripts/query.py \
  --kb-id 1 \
  --query "What was the primary outcome at week 24?"
```

API 查询示例：

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "query": "What was the primary outcome at week 24?",
    "top_k": 5
  }'
```

返回结果包含：

- `answer`：基于检索证据的回答；未配置 LLM 时为抽取式回答。
- `citations`：引用来源，包含 chunk、document、section、page、score、source_text。
- `retrieved_chunks`：完整检索片段，用于调试召回与排序。

## 核心 API

```text
GET    /health
GET    /api/v1/stats
GET    /api/v1/config

POST   /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases/{kb_id}
DELETE /api/v1/knowledge-bases/{kb_id}

POST   /api/v1/knowledge-bases/{kb_id}/documents
POST   /api/v1/knowledge-bases/{kb_id}/documents/mineru-local
GET    /api/v1/knowledge-bases/{kb_id}/documents
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/chunks

POST   /api/v1/knowledge-bases/{kb_id}/index/rebuild
POST   /api/v1/query
POST   /api/v1/parse/mock

GET    /api/v1/mineru/local/status
GET    /api/v1/settings/embedding
PUT    /api/v1/settings/embedding
```

更多说明见：[docs/api.md](docs/api.md)。

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/            FastAPI 路由
│   │   ├── core/           配置与日志
│   │   ├── db/             数据库连接
│   │   ├── models/         SQLAlchemy 模型
│   │   ├── schemas/        Pydantic Schema
│   │   ├── parsers/        Mock / Local MinerU / Remote MinerU 适配器
│   │   ├── chunking/       医疗语义切分
│   │   ├── vectorstores/   Chroma / SQLite 向量库
│   │   ├── rag/            Embedding、LLM、RAG 查询
│   │   └── services/       知识库、索引、设置等业务服务
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/          控制台页面
│   │   ├── components/     布局与 UI 组件
│   │   ├── lib/            API client 与类型
│   │   └── hooks/
│   └── README.md
├── docs/
├── examples/
├── scripts/
├── data/
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## 开发与测试

后端：

```bash
ruff check backend scripts
pytest
```

前端：

```bash
cd frontend
npm run lint
npm run build
```

## 文档

- [系统架构](docs/architecture.md)
- [API 文档](docs/api.md)
- [MinerU 接入说明](docs/mineru_integration.md)
- [医疗语义切分策略](docs/chunking_strategy.md)
- [评测计划](docs/evaluation_plan.md)

## 当前边界与后续计划

当前已经支持：

- Mock MinerU 样例导入
- 本地 MinerU CLI Pipeline 入库
- 已清洗 MinerU 目录批量导入
- Jina Embedding
- SQLite/Chroma 向量索引
- 可溯源 RAG 问答
- Web 控制台演示

后续可以继续增强：

- MinerU 清洗任务队列
- WebSocket/SSE 实时日志
- 多文档证据一致性判断
- MedBench 或自定义评测集自动评测
- 用户权限与多租户隔离
- 更完整的表格结构化查询

## License

MIT License。
