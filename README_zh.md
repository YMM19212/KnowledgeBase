# 基于 MinerU 的医疗文献高质量知识库 RAG

这是一个面向赛事 Demo 和后续工程落地的医疗文献 RAG 知识库项目。当前阶段不依赖真实 MinerU 服务，使用 `examples/sample_mineru_output.json` 模拟 MinerU 解析结果；后续只需要替换 MinerU 适配层，即可接入服务器解析流程。

## 核心能力

- FastAPI 后端服务，提供完整知识库、文档、chunk、索引和查询 API。
- SQLite 作为默认元数据数据库，便于本地运行和演示。
- Chroma 向量库适配器，离线或测试场景自动使用 SQLite 向量检索兜底。
- embedding 层可配置：正式环境可用 sentence-transformers，本地无模型时可使用确定性 hash embedding。
- 预留 MinerU 接口：`BaseParser`、`MinerUParserAdapter`、`MockParser`。
- 医疗论文语义切分：识别 Abstract、Methods、Participants、Intervention、Primary outcome、Secondary outcome、Adverse events、Subgroup analysis、Limitations 等医学论文结构。
- 表格、图注、正文分开保留，chunk metadata 包含 document、section、page、source_span、citation_text。
- RAG 查询强制返回 citations、retrieved_chunks、source_text；无足够证据时返回“证据不足，无法可靠回答”。
- 提供 CLI 脚本、Docker、pytest、ruff/black、MIT License 和完整文档。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
MEDRAG_EMBEDDING_BACKEND=hash MEDRAG_VECTOR_STORE=sqlite make ingest-sample
MEDRAG_EMBEDDING_BACKEND=hash MEDRAG_VECTOR_STORE=sqlite make dev
```

访问：

- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

如果希望使用真实 sentence-transformers 和 Chroma：

```bash
make install-rag
make ingest-sample
make dev
```

## Docker 启动

```bash
docker compose up --build
```

后端服务地址为 `http://localhost:8000`，前端控制台地址为 `http://localhost:5173`。

## 前端控制台

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

前端包含 Dashboard、知识库管理、文档/Chunk 查看、可溯源 RAG 问答、MinerU 接入配置、
评测分析和系统设置等页面。

## Jina Embedding 配置

项目支持 Jina Embeddings。默认模型建议：

```bash
MEDRAG_EMBEDDING_BACKEND=jina
MEDRAG_EMBEDDING_MODEL=jina-embeddings-v5-text-small
MEDRAG_JINA_API_KEY=你的 Jina API Key
```

也可以在前端“系统设置 → Embedding 设置”中修改 backend、model 和 API key。
修改 embedding 模型后，需要到知识库详情页点击“重建索引”，使已入库文档使用新向量。

## 导入样例数据

```bash
python scripts/create_kb.py --name "Demo Medical KB"
python scripts/ingest_sample.py --kb-id 1
```

也可以直接创建并导入：

```bash
python scripts/ingest_sample.py --kb-name "Demo Medical KB"
```

## 接入本地 MinerU Pipeline

如果本机已经可以运行：

```bash
mineru -p <input_path> -o <output_path> -b pipeline
```

则可以在前端进入“知识库详情 → 本地 MinerU Pipeline 清洗导入”，上传 PDF 并选择
`method/lang/formula/table` 参数。后端会自动执行 MinerU CLI，读取输出目录中的
`content_list.json`、其他 JSON 或 Markdown，将结果标准化后写入知识库并建立索引。

相关环境变量：

```bash
MEDRAG_MINERU_CLI_COMMAND=mineru
MEDRAG_MINERU_LOCAL_OUTPUT_DIR=./data/mineru_outputs
MEDRAG_MINERU_CLI_TIMEOUT_SECONDS=1800
```

## 查询样例

```bash
python scripts/query.py --kb-id 1 --query "What was the primary outcome at week 24?"
python scripts/query.py --kb-id 1 --query "Were serious adverse events increased?"
```

API 查询：

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id":1,"query":"What was the primary outcome at week 24?","top_k":5}'
```

返回结果包含：

- `answer`：LLM 未配置时为基于证据片段的抽取式回答。
- `citations`：chunk、document、section、page、score、source text。
- `retrieved_chunks`：完整检索片段，便于前端展示和调试。

## 当前 Mock 阶段与正式 MinerU 阶段边界

当前阶段：

- 不上传真实 PDF 到 MinerU。
- `MockParser` 从 `examples/sample_mineru_output.json` 读取模拟解析结果。
- `MinerUParserAdapter` 保留接口，但未真正轮询服务器任务。
- 重点验证知识库工程结构、医疗语义切片、索引、检索、问答和溯源。

正式 MinerU 阶段：

- 实现 `submit_parse_task()`：上传 PDF 到 MinerU 服务并返回 task_id。
- 实现 `get_parse_result()`：轮询或拉取解析完成后的 MinerU JSON。
- 实现 `parse_pdf()`：串联提交、等待、获取、标准化。
- 完善 `normalize_mineru_json()`：把 MinerU 原生 JSON 映射到本项目 `ParsedDocument`。

只要标准化结构不变，后续 chunking、indexing、retrieval、API 都无需大改。

## 目录结构

```text
backend/
  app/
    api/            FastAPI 路由
    core/           配置与日志
    db/             数据库连接
    models/         SQLAlchemy 模型
    schemas/        Pydantic Schema
    parsers/        MinerU/mock 解析适配器
    chunking/       医疗语义切分
    vectorstores/   Chroma/SQLite 向量库
    rag/            embedding、LLM、检索问答
    services/       知识库、文档、索引编排
  tests/            pytest 测试
examples/           样例 MinerU 输出和问题
docs/               架构、API、评估和 MinerU 接入文档
scripts/            命令行工具
```

## License

MIT License。
