# 🏗️ 招投标助手系统 (Bidding Assistant)

基于 LlamaIndex + RAG 的智能招投标文档处理系统，专注于业绩合同管理和智能匹配。

## ✨ 功能特性

### 已完成 ✅

| 模块 | 功能 | 说明 |
|------|------|------|
| **文档解析** | PDF扫描件解析 | PaddleOCR本地识别，支持水印过滤 |
| | Word文档解析 | MarkItDown转换，保留结构 |
| **知识库** | 文档结构化 | AI解析章节层级，生成Node树 |
| | 向量索引 | Qdrant存储，BGE-M3嵌入 |
| | RAG问答 | 带引用来源的智能问答 |
| **业绩管理** | 合同信息提取 | GLM-4.1V视觉识别 + 结构化提取 |
| | 数据库存储 | PostgreSQL存储结构化数据+图片 |
| | 智能匹配 | 根据招标要求自动筛选业绩 |

### 开发中 🚧

- [ ] Web界面（Gradio/Streamlit）
- [ ] 批量导入优化（断点续传、并发处理）
- [ ] 投标文件自动生成
- [ ] 业绩证明材料自动整理

### 规划中 📋

- [ ] 多用户支持
- [ ] 业绩有效期提醒
- [ ] 招标公告自动抓取
- [ ] 竞争对手分析

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| **OCR** | PaddleOCR 3.x（本地） |
| **文档解析** | MarkItDown、python-docx |
| **向量化** | BAAI/bge-m3（硅基流动API） |
| **重排序** | BAAI/bge-reranker-v2-m3 |
| **结构化提取** | Qwen3-8B |
| **视觉识别** | GLM-4.1V-Thinking |
| **核心推理** | DeepSeek-R1-0528-Qwen3-8B |
| **向量数据库** | Qdrant（本地模式） |
| **关系数据库** | PostgreSQL |
| **框架** | LlamaIndex |

---

## 📦 安装

### 1. 克隆项目

```bash
git clone https://github.com/yourname/bidding-assistant.git
cd bidding-assistant
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装Poppler（PDF转图片依赖）

- Windows: 下载 [Poppler](https://github.com/osber/poppler-windows/releases)，解压后配置路径
- Linux: `sudo apt install poppler-utils`
- Mac: `brew install poppler`

### 5. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
# 硅基流动API
SILICONFLOW_API_KEY=your_api_key_here

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bidding_assistant
DB_USER=postgres
DB_PASSWORD=your_password

# Poppler路径（Windows）
POPPLER_PATH=D:\.Software\poppler\Library\bin
```

### 6. 初始化数据库

```bash
python -m src.database
```

---

## 🚀 快速开始

### 处理招标文件（生成知识库）

```bash
# Word文档转Markdown
python -m src.docx_to_markdown "招标文件.docx"

# 解析文档结构
python -m src.node_parser

# 构建向量索引
python -m src.indexer
```

### RAG问答

```bash
python -m src.rag_query
```

```
🙋 你的问题: 供应商资格要求是什么
📝 回答：根据文档，供应商需要满足以下资格要求...
```

### 处理业绩合同

```bash
# 单个文件
python -m src.contract_extractor "合同.pdf"

# 批量处理
python -m src.contract_extractor "./documents/业绩"
```

### 业绩智能匹配

```bash
python -m src.contract_matcher
```

```
📋 请输入业绩要求: 近五年内至少1项能源类企业法律服务业绩

📊 匹配结果:
✅ [1] 深燃天然气常年法律顾问合同 - 匹配度95分
✅ [2] 清洁能源专项法律服务协议 - 匹配度90分
```

---

## 📁 项目结构

```
bidding-assistant/
├── README.md                    # 项目说明
├── requirements.txt             # 依赖清单
├── .env                         # 环境变量
│
├── config/                      # 配置
│   └── settings.py              # 全局配置
│
├── prompts/                     # 提示词模板
│   ├── structure_parse.md       # 文档结构解析
│   ├── contract_extract.md      # 合同信息提取
│   └── ...
│
├── src/                         # 源代码
│   ├── ocr_parser.py            # PDF解析
│   ├── docx_to_markdown.py      # Word解析
│   ├── node_parser.py           # 结构解析
│   ├── indexer.py               # 向量索引
│   ├── rag_query.py             # RAG问答
│   ├── database.py              # 数据库
│   ├── contract_extractor.py    # 合同提取
│   └── contract_matcher.py      # 业绩匹配
│
├── tests/                       # 单元测试
└── documents/                   # 文档目录
```

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单个测试
pytest tests/test_extractor.py -v

# 查看覆盖率
pytest --cov=src tests/
```

---

## 📊 数据库表结构

### contracts（合同表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| file_name | String | 原始文件名 |
| contract_name | String | 合同名称 |
| party_a | String | 甲方名称 |
| party_a_industry | String | 甲方行业 |
| is_state_owned | Boolean | 是否国企 |
| amount | Float | 合同金额（万元） |
| sign_date | String | 签订日期 |
| project_type | String | 项目类型（常法/诉讼/专项） |
| project_detail | Text | 项目详情 |
| team_member | String | 团队成员 |
| image_data | LargeBinary | 图片数据（BLOB） |
| raw_text | Text | OCR原文 |

---

## 🔧 配置说明

### 模型配置

在 `config/settings.py` 中可调整使用的模型：

```python
# 嵌入模型
EMBEDDING_MODEL = "BAAI/bge-m3"

# 结构化提取
EXTRACT_MODEL = "Qwen/Qwen3-8B"

# 视觉识别
VISION_MODEL = "Pro/GLM-4.1V-Thinking"

# 推理模型
REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
```

### 提示词模板

所有提示词存放在 `prompts/` 目录，支持Markdown格式，方便修改和版本管理。

---

## 📝 更新日志

### v0.1.0 (2025-01-09)

- ✅ 完成文档解析模块（PDF/Word）
- ✅ 完成RAG知识库构建
- ✅ 完成合同信息提取
- ✅ 完成业绩智能匹配

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [LlamaIndex](https://github.com/run-llama/llama_index)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [MarkItDown](https://github.com/microsoft/markitdown)
- [硅基流动](https://siliconflow.cn/)
