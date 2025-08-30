# app.py

import os
import sys
import time
import datetime
import json
from dataclasses import dataclass, asdict

# --- 1. 更新数据类中 duration 字段的注释，以反映新的格式 ---
@dataclass
class LogEntry:
    """描述单次用户处理任务的日志记录。"""
    user_id: int            # Bilibili用户的数字ID
    user_name: str          # 用户的昵称 (从文件夹名获取)
    timestamp: str          # 本次处理完成时的时间戳
    duration: str           # 【注释更新】处理该用户所花费的时间 (格式化为 "H 小时 M 分 S.SS 秒")
    duration_seconds: float # 处理该用户所花费的总秒数 (浮点数，便于机器分析)
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
                duration = end_time - start_time
                
                user_name = stats.get("folder_name", str(user_id))
                
                # --- 2. 这里是修改的核心：新的时间格式化逻辑 ---

                # 使用 divmod 将总秒数分解为分钟和剩余秒数
                minutes, seconds = divmod(duration, 60)
                # 再将总分钟数分解为小时和剩余分钟数
                hours, minutes = divmod(minutes, 60)

                # int() 用于确保小时和分钟显示为整数
                # 下载的总时间
                time_str = f"{int(hours)}h {int(minutes)}m {seconds:.2f}s"
                
                # --- 修改结束 ---

                console_message = (
                    f"\n>>>>>>>>> 完成用户 '{user_name}' 的处理，总耗时: {time_str} <<<<<<<<<\n"
                    f"  - 本次处理动态数: {stats['processed_posts']}\n"
                    f"  - 成功下载图片数: {stats['downloaded_images']}\n"
                    f"  - 下载失败图片数: {stats['failed_images']}\n"
                    f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                )
                print(console_message)
                
                log_entry_obj = LogEntry(
                    user_id=user_id,
                    user_name=user_name,
                    timestamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    duration=time_str,  # 这里现在是新的格式
                    duration_seconds=round(duration, 2),
                    processed_posts=stats['processed_posts'],
                    downloaded_images=stats['downloaded_images'],
                    failed_images=stats['failed_images']
                )

                self._write_log(log_file_path, asdict(log_entry_obj))

        except KeyboardInterrupt:
            print("\n\n程序被用户中断。正在退出...")
        
        print(f"\n所有任务已完成！日志已保存到: {log_file_path}")