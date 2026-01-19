import os
import json
import time
from typing import List, Dict, Any
from config import PipelineConfig
from utils import Logger
from processor import PDFProcessor

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
