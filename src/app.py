# app.py

import os
import sys

# 从其他自定义模块导入类
from config import Config
from database import ArchiveDB
from api import BilibiliAPI
from processor import PostProcessor

class Application:
    """主应用程序类，负责协调整个流程。"""
    
    def __init__(self, config: Config):
        """
        初始化应用程序，创建所有必要的对象实例。
        :param config: 包含所有配置信息的 Config 对象。
        """
        self.config = config
        
        # 首先创建基础输出目录，确保它存在
        os.makedirs(self.config.OUTPUT_DIR_PATH, exist_ok=True)

        # 目录已确认存在，现在可以安全地初始化数据库了
        db_path = os.path.join(self.config.OUTPUT_DIR_PATH, self.config.ARCHIVE_DB_NAME)
        self.db = ArchiveDB(db_path)
        
        # 初始化 API 封装器和核心处理器
        self.api = BilibiliAPI(self.config.COOKIE_FILE_PATH)
        self.processor = PostProcessor(self.config.OUTPUT_DIR_PATH, self.api, self.db)

    def run(self):
        """
        启动下载器的主入口点。
        """
        print(f"正在从 '{self.config.USER_INPUT_FILE_PATH}' 读取用户 URL...")
        try:
            with open(self.config.USER_INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
                # 读取所有行，并移除空白行和行首尾的空白字符
                user_urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"致命错误：输入文件未找到: {self.config.USER_INPUT_FILE_PATH}")
            sys.exit(1)
        
        if not user_urls:
            print(f"错误：输入文件为空或不包含有效的 URL。")
            return

        try:
            # 遍历 URL 列表，对每个用户进行处理
            for user_url in user_urls:
                self.processor.process_user(user_url)
        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在优雅地退出...")
        finally:
            # 无论程序是正常完成还是被中断，都确保数据库连接被关闭
            self.db.close()
        
        print("\n所有任务已完成！")