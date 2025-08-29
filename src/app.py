# app.py

import os
import sys

# 从其他自定义模块导入类
from config import Config
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
        
        os.makedirs(self.config.OUTPUT_DIR_PATH, exist_ok=True)

        self.api = BilibiliAPI(self.config.COOKIE_FILE_PATH)
        
        self.processor = PostProcessor(
            self.config.OUTPUT_DIR_PATH, 
            self.api, 
            self.config
        )

    def run(self):
        """
        启动下载器的主入口点。
        """
        # --- 修改：从 config.py 读取 USERS_ID 列表 ---
        print(f"正在从 'config.py' 的 USERS_ID 列表读取用户 ID...")
        user_ids = self.config.USERS_ID
        
        if not user_ids:
            print(f"错误：配置文件中的 USERS_ID 列表为空。")
            return

        try:
            # 遍历数字ID列表，而不是文件中的URL
            for user_id in user_ids:
                # 按照要求拼接成 /article URL
                user_url = f"https://space.bilibili.com/{user_id}/article"
                self.processor.process_user(user_url)
        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在优雅地退出...")
        
        print("\n所有任务已完成！")