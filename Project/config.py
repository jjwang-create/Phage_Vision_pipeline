from typing import Dict

class PipelineConfig:
    def __init__(self):
        # API配置
        self.API_KEYS: Dict[str, str] = {
            "kimi": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "deepseek": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "openai": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
        
        # 模型配置
        self.MODELS: Dict[str, str] = {
            "pdf_reader": "kimi",
            "data_extractor": "deepseek",
            "backup_model": "openai"
        }
        
        # 路径配置
        self.PDF_FOLDER_PATH: str = "./pdf_files"  # PDF文件存放目录
        self.OUTPUT_FILE: str = "pipeline_results.json"  # 结果输出文件
        self.LOG_FILE: str = "pipeline_log.txt"  # 日志文件
        
        # 处理配置
        self.MAX_RETRIES: int = 2  # 失败重试次数
        self.RETRY_DELAY: int = 3  # 重试延迟（秒）
        self.RATE_LIMIT_DELAY: int = 1  # 速率限制延迟（秒）
        self.VERBOSE: bool = True  # 详细日志
