# app.py

import os
import sys
import time
import datetime
import json
from dataclasses import dataclass, asdict

# --- 1. 在数据类中新增字段 ---
@dataclass
class LogEntry:
    """描述单次用户处理任务的日志记录。"""
    user_id: int            # Bilibili用户的数字ID
    user_name: str          # 用户的昵称 (从文件夹名获取)
    timestamp: str          # 本次处理完成时的时间戳
    duration: str           # 处理该用户所花费的时间 (格式化为 "X 分 Y.YY 秒"，便于人类阅读)
    duration_seconds: float # 【新增】处理该用户所花费的总秒数 (浮点数，便于机器分析)
    processed_posts: int    # 本次运行为该用户新处理的动态数量
    downloaded_images: int  # 本次运行成功下载的图片总数
    failed_images: int      # 本次运行下载失败的图片总数

from config import Config
from api import BilibiliAPI
from processor.processor import PostProcessorFacade

class Application:
    """主应用程序类，负责协调整个流程。"""
    
    def __init__(self, config: Config):
        self.config = config
        os.makedirs(self.config.OUTPUT_DIR_PATH, exist_ok=True)
        self.api = BilibiliAPI(self.config.COOKIE_FILE_PATH)
        self.processor = PostProcessorFacade(self.config.OUTPUT_DIR_PATH, self.api, self.config)

    def _write_log(self, log_file_path: str, data: dict):
        records = []
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                if not isinstance(records, list):
                    records = []
            except (json.JSONDecodeError, FileNotFoundError):
                records = []
        
        records.append(data)
        
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=4)

    def run(self):
        """
        启动下载器的主入口点。
        """
        print(f"正在从 'config.py' 的 USERS_ID 列表读取用户 ID...")
        user_ids = self.config.USERS_ID
        
        if not user_ids:
            print(f"错误：配置文件中的 USERS_ID 列表为空。")
            return

        log_file_path = os.path.join(self.config.OUTPUT_DIR_PATH, "processing_time_log.json")

        try:
            for user_id in user_ids:
                start_time = time.perf_counter()

                user_url = f"https://space.bilibili.com/{user_id}/article"
                stats = self.processor.process_user(user_id, user_url)

                end_time = time.perf_counter()
                # 'duration' 变量本身就是我们需要的总秒数 (float类型)
                duration = end_time - start_time
                
                user_name = stats.get("folder_name", str(user_id))
                
                # 创建用于人类阅读的时间字符串
                minutes = int(duration / 60)
                seconds = duration % 60
                time_str = f"{minutes} 分 {seconds:.2f} 秒"

                console_message = (
                    f"\n>>>>>>>>> 完成用户 '{user_name}' 的处理，总耗时: {time_str} <<<<<<<<<\n"
                    f"  - 本次处理动态数: {stats['processed_posts']}\n"
                    f"  - 成功下载图片数: {stats['downloaded_images']}\n"
                    f"  - 下载失败图片数: {stats['failed_images']}\n"
                    f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                )
                print(console_message)
                
                # --- 2. 创建实例时，传入原始的 'duration' 变量 ---
                log_entry_obj = LogEntry(
                    user_id=user_id,
                    user_name=user_name,
                    timestamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    duration=time_str,
                    duration_seconds=round(duration, 2),  # 将原始秒数赋值给新字段，保留两位小数
                    processed_posts=stats['processed_posts'],
                    downloaded_images=stats['downloaded_images'],
                    failed_images=stats['failed_images']
                )

                self._write_log(log_file_path, asdict(log_entry_obj))

        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在退出...")
        
        print(f"\n所有任务已完成！日志已保存到: {log_file_path}")