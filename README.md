# 招投标助手系统 - 项目总结

## 🎯 项目目标

构建一个**自动化招投标助手系统**，核心解决：

1. 招标文件智能问答
2. 业绩合同批量管理
3. 业绩智能匹配筛选

---

## 📁 项目结构

```
bidding-assistant/
├── main.py                  # 主入口（文件类型自动识别）
├── ocr_parser.py            # PDF扫描件 → Markdown
├── docx_to_markdown.py      # Word文档 → Markdown
├── text_cleaner.py          # 水印过滤
├── node_parser.py           # AI结构化解析 → Node
├── indexer.py               # Node → 向量索引（Qdrant）
├── rag_query.py             # RAG问答系统
├── database.py              # PostgreSQL数据库
├── contract_extractor.py    # 合同信息提取 + 入库
├── contract_matcher.py      # 业绩智能匹配
├── .env                     # API密钥配置
├── cache/                   # OCR缓存目录
├── qdrant_data/             # 向量数据库
├── output/                  # 输出文件
└── documents/               # 文档存放
    └── 业绩/                # 业绩合同PDF
```

---

## 🛠️ 技术栈

|层级|技术|用途|
|---|---|---|
|**PDF解析**|PaddleOCR 3.x|扫描件文字识别（本地、免费）|
|**Word解析**|MarkItDown|Word转Markdown|
|**视觉校验**|GLM-4.1V|图片识别纠错（API）|
|**结构提取**|Qwen3-8B|文档结构化解析（API）|
|**向量化**|BAAI/bge-m3|文本嵌入（API）|
|**重排序**|BAAI/bge-reranker-v2-m3|检索结果重排（API）|
|**推理**|DeepSeek-R1-0528-Qwen3-8B|问答生成、业绩匹配（API）|
|**向量库**|Qdrant（本地）|向量存储与检索|
|**关系库**|PostgreSQL|合同结构化数据存储|
|**框架**|LlamaIndex|RAG核心框架|

---

## ✅ 已完成功能

### 1️⃣ 文档解析层

|功能|文件|说明|
|---|---|---|
|PDF转Markdown|`ocr_parser.py`|PaddleOCR识别 + 水印过滤|
|Word转Markdown|`docx_to_markdown.py`|MarkItDown一键转换|
|自动识别|`main.py`|根据文件后缀自动分流处理|

### 2️⃣ RAG问答系统

|功能|文件|说明|
|---|---|---|
|AI结构解析|`node_parser.py`|文档层级结构提取|
|向量索引|`indexer.py`|Node → Qdrant向量库|
|智能问答|`rag_query.py`|检索 + Rerank + LLM生成答案|

**效果示例：**

```
🙋 问题: 业绩要求有哪些
📝 回答: 近五年内响应人至少拥有1项能源类企业法律服务业绩...
📚 来源: 第一章 采购公告 > 二、响应人资格及信誉要求 > 3.
```

### 3️⃣ 业绩管理系统

|功能|文件|说明|
|---|---|---|
|数据库|`database.py`|PostgreSQL表结构、CRUD操作|
|信息提取|`contract_extractor.py`|OCR + GLM视觉提取 + 入库|
|批量处理|`contract_extractor.py`|文件夹批量导入|
|缓存机制|`contract_extractor.py`|避免重复OCR|

**合同表字段：**

```
├── 甲方信息（名称、行业、是否国企）
├── 合同信息（金额、日期、收费方式）
├── 项目信息（类型、详情、标的额、对方当事人）
├── 团队成员
├── 图片数据（BLOB存储）
└── OCR原文
```

### 4️⃣ 业绩智能匹配

|功能|文件|说明|
|---|---|---|
|需求解析|`contract_matcher.py`|AI理解招标要求|
|同义词扩展|`contract_matcher.py`|燃气=天然气等|
|数据库筛选|`contract_matcher.py`|时间、行业、金额等条件|
|AI评估|`contract_matcher.py`|匹配度评分 + 风险提示|

**效果示例：**

```
📋 业绩要求: 近五年内至少1项能源类企业法律服务业绩

📊 匹配结果:
✅ [4] 专项法律服务协议 - 深燃清洁能源（95分）
✅ [5] 常年法律顾问合同 - 深汕深燃天然气（90分）
✅ [6] 法律顾问合同 - 梧州深燃天然气（90分）
```

---

## 📊 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                      招投标助手系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【招标文件处理】                                            │
│  Word/PDF ──→ Markdown ──→ Node ──→ Qdrant ──→ RAG问答     │
│                                                             │
│  【业绩合同处理】                                            │
│  PDF ──→ OCR ──→ GLM视觉提取 ──→ PostgreSQL ──→ 业绩匹配   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 环境配置

### .env 文件

```bash
# 硅基流动API
SILICONFLOW_API_KEY=your_api_key

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bidding_assistant
DB_USER=postgres
DB_PASSWORD=your_password
```

### 依赖安装

```bash
pip install paddlepaddle paddleocr pdf2image pillow
pip install llama-index llama-index-vector-stores-qdrant qdrant-client
pip install openai httpx python-dotenv markitdown
pip install sqlalchemy psycopg2-binary
```

### 外部依赖

- **Poppler**：PDF转图片（配置路径）
- **PostgreSQL**：数据库服务

---

## ▶️ 使用方法

### 招标文件问答

```bash
# 1. 转换文档
python main.py "招标文件.docx"

# 2. 解析结构
python node_parser.py

# 3. 构建索引
python indexer.py

# 4. 启动问答
python rag_query.py
```

### 业绩管理

```bash
# 批量导入合同
python contract_extractor.py "./documents/业绩"

# 业绩匹配
python contract_matcher.py
```

---

## 🚀 后续可扩展

|方向|说明|
|---|---|
|**Web界面**|Flask/Streamlit可视化操作|
|**投标文件生成**|根据招标要求自动生成响应文件|
|**多项目管理**|支持多个招标项目独立管理|
|**团队协作**|多用户权限管理|
|**数据统计**|业绩数据可视化分析|

---

## 📈 学习收获

|Day|内容|
|---|---|
|**Day 1**|环境搭建、PaddleOCR、MarkItDown、水印过滤|
|**Day 2**|LlamaIndex Node概念、AI结构解析、向量索引|
|**Day 3**|RAG问答、Rerank重排序、PostgreSQL、合同提取、业绩匹配|

---

**项目核心价值**：将原本需要人工翻阅大量PDF的业绩筛选工作，自动化为秒级匹配，大幅提升招投标效率！ 🎉
