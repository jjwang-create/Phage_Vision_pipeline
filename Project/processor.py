import os
import json
import time
from typing import Dict, Any
from openai import OpenAI
from config import PipelineConfig
from utils import Logger

class PDFProcessor:
    def __init__(self, config: PipelineConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self.clients = self._initialize_clients()
    
    def _initialize_clients(self) -> Dict[str, OpenAI]:
        """初始化API客户端"""
        clients = {
            "kimi": OpenAI(
                api_key=self.config.API_KEYS["kimi"],
                base_url="https://api.moonshot.cn/v1"
            ),
            "deepseek": OpenAI(
                api_key=self.config.API_KEYS["deepseek"],
                base_url="https://api.deepseek.com"
            ),
            "openai": OpenAI(
                api_key=self.config.API_KEYS["openai"]
            )
        }
        return clients
    
    def read_pdf(self, file_path: str) -> str:
        """从PDF中读取文本"""
        model = self.config.MODELS["pdf_reader"]
        client = self.clients[model]
        
        self.logger.log(f"使用{model}读取PDF: {os.path.basename(file_path)}")
        
        try:
            # 上传文件
            file_object = client.files.create(
                file=open(file_path, "rb"),
                purpose="file-extract"
            )
            
            # 获取内容
            file_content = client.files.content(file_id=file_object.id).text
            return file_content
        except Exception as e:
            self.logger.log(f"读取PDF失败: {e}")
            raise
    
    def extract_data(self, text_content: str) -> Dict[str, Any]:
        """从文本中提取结构化数据"""
        model = self.config.MODELS["data_extractor"]
        client = self.clients[model]
        
        self.logger.log(f"使用{model}提取数据")
        
        system_prompt = """
        你是一个专业的数据提取助手。
        请从用户的文本中提取关键信息，并以纯JSON格式输出。
        如果文本中找不到对应信息，请填null。
        
        你需要提取的字段如下：
        1. "title": 文档标题
        2. "summary": 简短总结（不超过200字）
        3. "authors": 作者列表
        4. "publication_date": 出版日期
        5. "keywords": 关键词列表
        6. "main_content": 主要内容概述
        7. "conclusions": 结论
        """
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat" if model == "deepseek" else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请处理以下文本：\n\n{text_content[:8000]}"}  # 限制输入长度
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.logger.log(f"提取数据失败: {e}")
            raise
    
    def process_single_file(self, file_path: str) -> Dict[str, Any]:
        """处理单个PDF文件"""
        retries = 0
        while retries < self.config.MAX_RETRIES:
            try:
                # 1. 读取PDF文本
                raw_text = self.read_pdf(file_path)
                
                # 2. 提取结构化数据
                extracted_data = self.extract_data(raw_text)
                
                # 3. 添加元信息
                extracted_data["source_filename"] = os.path.basename(file_path)
                extracted_data["processing_status"] = "success"
                
                return extracted_data
            except Exception as e:
                retries += 1
                self.logger.log(f"处理文件失败，重试 {retries}/{self.config.MAX_RETRIES}: {e}")
                time.sleep(self.config.RETRY_DELAY)
        
        # 所有重试都失败
        return {
            "source_filename": os.path.basename(file_path),
            "processing_status": "failed",
            "error_message": "超过最大重试次数"
        }
