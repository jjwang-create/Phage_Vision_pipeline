import time

class Logger:
    def __init__(self, log_file: str, verbose: bool = True):
        self.log_file: str = log_file
        self.verbose: bool = verbose
        
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
