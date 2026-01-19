from config import PipelineConfig
from pipeline import Pipeline

def main():
    """主函数"""
    # 初始化配置
    config = PipelineConfig()
    
    # 创建并运行流水线
    pipeline = Pipeline(config)
    pipeline.run()

if __name__ == "__main__":
    main()
