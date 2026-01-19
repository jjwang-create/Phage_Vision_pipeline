import os
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI

# ================= 配置区域 =================
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
            "pdf_reader": "kimi",
            "data_extractor": "deepseek",
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

# ================= 工具类 =================
class Logger:
    def __init__(self, log_file: str, verbose: bool = True):
        self.log_file = log_file
        self.verbose = verbose
        
    def log(self, message: str):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # 写入文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # 打印到控制台
        if self.verbose:
            print(log_entry.strip())

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

class Pipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = Logger(config.LOG_FILE, config.VERBOSE)
        self.processor = PDFProcessor(config, self.logger)
    
    def get_pdf_files(self) -> List[str]:
        """获取所有PDF文件路径"""
        if not os.path.exists(self.config.PDF_FOLDER_PATH):
            self.logger.log(f"错误：找不到文件夹 {self.config.PDF_FOLDER_PATH}")
            return []
        
        pdf_files = [
            os.path.join(self.config.PDF_FOLDER_PATH, f)
            for f in os.listdir(self.config.PDF_FOLDER_PATH)
            if f.lower().endswith('.pdf')
        ]
        
        self.logger.log(f"扫描到 {len(pdf_files)} 个PDF文件")
        return pdf_files
    
    def run(self) -> List[Dict[str, Any]]:
        """运行流水线"""
        self.logger.log("开始运行PDF处理流水线")
        
        # 获取所有PDF文件
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            self.logger.log("没有找到PDF文件，流水线终止")
            return []
        
        # 处理所有文件
        all_results = []
        total_files = len(pdf_files)
        
        for index, file_path in enumerate(pdf_files, 1):
            filename = os.path.basename(file_path)
            self.logger.log(f"[{index}/{total_files}] 正在处理文件：{filename}")
            
            try:
                result = self.processor.process_single_file(file_path)
                all_results.append(result)
                
                if result["processing_status"] == "success":
                    self.logger.log(f"文件 {filename} 处理成功")
                else:
                    self.logger.log(f"文件 {filename} 处理失败")
            except Exception as e:
                self.logger.log(f"处理文件 {filename} 时发生未捕获异常：{e}")
                all_results.append({
                    "source_filename": filename,
                    "processing_status": "failed",
                    "error_message": str(e)
                })
            
            # 速率限制
            time.sleep(self.config.RATE_LIMIT_DELAY)
            self.logger.log("-" * 50)
        
        # 保存结果
        self._save_results(all_results)
        
        self.logger.log("PDF处理流水线运行完成")
        return all_results
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """保存结果到JSON文件"""
        self.logger.log(f"正在保存结果到 {self.config.OUTPUT_FILE}")
        
        with open(self.config.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        self.logger.log(f"结果已保存到 {self.config.OUTPUT_FILE}")
        
        # 生成统计信息
        success_count = sum(1 for r in results if r["processing_status"] == "success")
        failure_count = len(results) - success_count
        self.logger.log(f"处理统计：成功 {success_count} 个，失败 {failure_count} 个")

# ================= 主程序 =================
def main():
    """主函数"""
    # 初始化配置
    config = PipelineConfig()
    
    # 创建并运行流水线
    pipeline = Pipeline(config)
    pipeline.run()

if __name__ == "__main__":
    main()
