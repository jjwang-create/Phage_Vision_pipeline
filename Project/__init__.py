# 导出常用类，方便外部直接导入
from .config import PipelineConfig
from .pipeline import Pipeline
from .processor import PDFProcessor
from .utils import Logger

# 定义包级别的元信息
__version__ = "1.0.0"
__author__ = "jjwang"

# 执行初始化操作
print("PDF Processing Pipeline Package Loaded")