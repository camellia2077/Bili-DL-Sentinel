# app.py

import os
import sys
import time

# 从其他自定义模块导入类
from config import Config
from api import BilibiliAPI
# 【重点修改】将导入路径从 processor.facade 改为 processor.processor
from processor.processor import PostProcessorFacade

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
        
        self.processor = PostProcessorFacade(
            self.config.OUTPUT_DIR_PATH, 
            self.api, 
            self.config
        )

    def run(self):
        """
        启动下载器的主入口点。
        """
        print(f"正在从 'config.py' 的 USERS_ID 列表读取用户 ID...")
        user_ids = self.config.USERS_ID
        
        if not user_ids:
            print(f"错误：配置文件中的 USERS_ID 列表为空。")
            return

        try:
            # 遍历数字ID列表
            for user_id in user_ids:
                # --- 新增：计时器开始 ---
                start_time = time.perf_counter()

                user_url = f"https://space.bilibili.com/{user_id}/article"
                self.processor.process_user(user_id, user_url)

                # --- 新增：计时器结束并打印结果 ---
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                # 从config中查找用户名，如果找不到就用数字ID
                user_id_str = str(user_id)
                user_name = self.config.USER_ID_TO_NAME_MAP.get(user_id_str, user_id_str)
                
                # 格式化时间输出
                minutes = int(duration / 60)
                seconds = duration % 60
                time_str = f"{minutes} 分 {seconds:.2f} 秒"

                print(f"\n>>>>>>>>> 完成用户 '{user_name}' 的处理，总耗时: {time_str} <<<<<<<<<")

        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在退出...")
        
        print("\n所有任务已完成！")