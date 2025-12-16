import logging
import os
from datetime import datetime

class Logger:
    """日志管理类"""
    
    def __init__(self, log_dir="logs"):
        """初始化日志配置"""
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志文件名格式
        log_filename = os.path.join(log_dir, f"zifeiyuSec_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("zifeiyuSec")
    
    def get_logger(self):
        """获取日志记录器"""
        return self.logger

# 创建全局日志记录器实例
global_logger = Logger()
logger = global_logger.get_logger()