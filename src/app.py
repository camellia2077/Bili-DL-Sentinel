# app.py

import os
import sys
import time
import datetime # <-- 1. 导入 datetime 模块

# 从其他自定义模块导入类
from config import Config
from api import BilibiliAPI
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

        # --- 新增：定义日志文件路径 ---
        log_file_path = os.path.join(self.config.OUTPUT_DIR_PATH, "processing_time_log.txt")

        try:
            # --- 2. 使用 'with open' 来管理日志文件 ---
            # 'a' 模式表示追加内容，如果文件不存在则会创建它
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                # 记录一次脚本开始运行的时间
                start_run_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_file.write(f"\n--- Script run started at {start_run_time} ---\n")

                # 遍历数字ID列表
                for user_id in user_ids:
                    start_time = time.perf_counter()

                    user_url = f"https://space.bilibili.com/{user_id}/article"
                    self.processor.process_user(user_id, user_url)

                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    
                    user_id_str = str(user_id)
                    user_name = self.config.USER_ID_TO_NAME_MAP.get(user_id_str, user_id_str)
                    
                    minutes = int(duration / 60)
                    seconds = duration % 60
                    time_str = f"{minutes} 分 {seconds:.2f} 秒"

                    # --- 3. 打印到控制台，并同时写入文件 ---
                    
                    # 准备要输出的内容
                    console_message = f"\n>>>>>>>>> 完成用户 '{user_name}' 的处理，总耗时: {time_str} <<<<<<<<<"
                    
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_message = f"[{timestamp}] 完成用户 '{user_name}' 的处理，总耗时: {time_str}\n"

                    # 执行输出
                    print(console_message)
                    log_file.write(log_message)

        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在退出...")
        
        print(f"\n所有任务已完成！日志已保存到: {log_file_path}")