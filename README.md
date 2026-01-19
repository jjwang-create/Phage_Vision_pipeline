# PDF处理流水线 (PDF Processing Pipeline)

一个功能完整、结构清晰的自动化PDF处理系统，用于批量提取PDF文档内容并生成结构化数据。

## 功能特点

- **批量PDF处理**：自动扫描指定文件夹中的所有PDF文件，逐个处理
- **AI驱动的内容提取**：使用Kimi API读取PDF内容，DeepSeek API提取结构化数据
- **多模型支持**：可配置使用Kimi、DeepSeek或OpenAI模型
- **灵活的配置管理**：所有参数集中管理，无需修改核心代码
- **健壮的错误处理**：内置重试机制，提高处理成功率
- **完善的日志系统**：详细记录处理过程，便于调试和监控
- **速率限制**：智能控制API请求频率，防止API节流
- **结构化输出**：提取的信息以JSON格式保存，便于后续分析

## 技术栈

- Python 3.8+
- OpenAI SDK
- Kimi API
- DeepSeek API

## 安装步骤

1. **克隆或下载项目**
   ```bash
   cd E:\用户min\Desktop\Project_File\Project
   ```

2. **安装依赖**
   ```bash
   pip install openai
   ```

3. **配置API密钥**
   - 打开 `config.py` 文件
   - 在 `API_KEYS` 字典中填入你的API密钥

## 配置说明

主要配置项位于 `config.py` 文件中，可根据需要调整：

```python
class PipelineConfig:
    def __init__(self):
        # API配置
        self.API_KEYS = {
            "kimi": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "deepseek": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "openai": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
        
        # 模型配置
        self.MODELS = {
            "pdf_reader": "kimi",       # 可选: kimi, deepseek, openai
            "data_extractor": "deepseek",  # 可选: deepseek, openai, kimi
            "backup_model": "openai"
        }
        
        # 路径配置
        self.PDF_FOLDER_PATH = "./pdf_files"  # PDF文件存放目录
        self.OUTPUT_FILE = "pipeline_results.json"  # 结果输出文件
        self.LOG_FILE = "pipeline_log.txt"  # 日志文件
        
        # 处理配置
        self.MAX_RETRIES = 2  # 失败重试次数
        self.RETRY_DELAY = 3  # 重试延迟（秒）
        self.RATE_LIMIT_DELAY = 1  # 速率限制延迟（秒）
        self.VERBOSE = True  # 详细日志
```

## 使用方法

### 1. 准备PDF文件
将需要处理的PDF文件放入配置中指定的文件夹（默认：`./pdf_files`）。

### 2. 运行流水线

#### 方式一：直接运行主程序
```bash
python main.py
```

#### 方式二：作为模块导入使用
```python
from config import PipelineConfig
from pipeline import Pipeline

# 初始化配置
config = PipelineConfig()

# 创建并运行流水线
pipeline = Pipeline(config)
results = pipeline.run()

# 处理结果
for result in results:
    print(f"文件名: {result['source_filename']}, 状态: {result['processing_status']}")
```

### 3. 查看结果
- 处理结果保存在配置中指定的JSON文件（默认：`pipeline_results.json`）
- 日志信息同时输出到控制台和日志文件（默认：`pipeline_log.txt`）

## 项目结构

```
Project/
├── __init__.py          # 包初始化文件
├── config.py            # 配置管理模块
├── utils.py             # 工具类模块（Logger）
├── processor.py         # PDF处理核心模块
├── pipeline.py          # 流水线调度模块
├── main.py              # 主程序入口
├── README.md            # 项目说明文档
└── trivial_pdf_extract_pipeline.py  # 原始参考文件
```

## 输出结果示例

```json
[
    {
        "title": "学术论文标题",
        "summary": "这是一篇关于人工智能的学术论文...",
        "authors": ["作者1", "作者2"],
        "publication_date": "2023-01-01",
        "keywords": ["人工智能", "机器学习", "深度学习"],
        "main_content": "本文介绍了一种新的机器学习方法...",
        "conclusions": "该方法在实验中取得了良好的效果...",
        "source_filename": "paper.pdf",
        "processing_status": "success"
    },
    {
        "source_filename": "failed_paper.pdf",
        "processing_status": "failed",
        "error_message": "超过最大重试次数"
    }
]
```

## 提取的字段说明

- `title`: 文档标题
- `summary`: 简短总结（不超过200字）
- `authors`: 作者列表
- `publication_date`: 出版日期
- `keywords`: 关键词列表
- `main_content`: 主要内容概述
- `conclusions`: 结论
- `source_filename`: 源文件名
- `processing_status`: 处理状态（success/failed）
- `error_message`: 错误信息（仅当处理失败时）

## 性能和成本估算

处理20000篇文献的大致估算：
- **成本**：约6800元（基于当前API定价）
- **处理时间**：5.6小时至7天（取决于API调用频率）
- **Token消耗**：约940百万Token

## 扩展建议

1. **添加更多提取字段**：修改 `processor.py` 中的 `extract_data` 方法
2. **支持更多文档类型**：扩展 `PDFProcessor` 类，支持Word、Excel等文件
3. **添加数据验证**：对提取的数据进行验证和清洗
4. **支持异步处理**：使用异步API调用，提高并发处理能力
5. **添加可视化界面**：创建Web或GUI界面，方便非技术用户使用

## 注意事项

1. **API密钥安全**：请妥善保管你的API密钥，避免泄露
2. **API使用限制**：注意各API的使用限制和配额，避免超额
3. **文件大小限制**：单个PDF文件大小建议不超过50MB
4. **网络连接**：确保网络连接稳定，避免处理过程中断
5. **版权问题**：确保你有权处理和分析这些PDF文件

## 许可证

本项目采用MIT许可证。

## 贡献指南

欢迎提交Issue和Pull Request，共同改进这个项目。

## 更新日志

### v1.0.0 (2026-01-19)
- 初始版本
- 实现基本的PDF处理功能
- 支持Kimi和DeepSeek API
- 模块化设计，便于扩展
