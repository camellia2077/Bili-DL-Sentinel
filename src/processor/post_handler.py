# src/processor/post_handler.py

import os
import datetime
from typing import Dict
from api import BilibiliAPI
from config import Config
from .content_extractor import ContentExtractor
from .downloader import Downloader
from .metadata_saver import MetadataSaver

class PostHandler:
    """处理单个动态的完整流程。"""

    def __init__(self, api: BilibiliAPI, config: Config, extractor: ContentExtractor, downloader: Downloader, saver: MetadataSaver):
        self.api = api
        self.config = config
        self.extractor = extractor
        self.downloader = downloader
        self.saver = saver

    def process(self, user_name: str, post_url: str, user_folder: str) -> bool:
        """
        处理单个动态，协调提取、保存和下载任务。
        【新流程】: 1. 获取数据 -> 2. 保存原始元数据 -> 3. 下载图片 -> 4. 从本地元数据生成内容JSON
        """
        # [修改] 移除了旧的进度打印语句，因为tqdm现在负责显示进度
        # green_user_name = f"\033[92m{user_name}\033[0m"
        # print(f"\n[步骤2] 正在处理用户 {green_user_name} 的动态 [{current_post_num}/{total_posts}]: {post_url}")

        # 步骤 A: 从API获取元数据
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            # tqdm会自动处理这里的打印，使其显示在进度条上方
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        if not (id_str and pub_ts):
            print(f"  - 警告：无法从元数据中获取动态 ID 或发布时间戳，跳过。")
            return True

        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'
        
        # 步骤 B: 检查最终内容JSON文件是否存在以实现增量下载
        content_json_filename = f"{date_str}_{id_str}.json"
        content_json_filepath = os.path.join(user_folder, content_json_filename)
        
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(content_json_filepath):
            green_user_name = f"\033[92m{user_name}\033[0m"
            print(f"  - 增量下载模式：内容文件 '{content_json_filename}' 已存在。")
            print(f"  - 将停止处理用户 {green_user_name} 的剩余动态。")
            return False

        # 如果需要处理，则执行以下完整流程
        # print(f"  - 检测到新动态，开始处理...") # 此消息可以省略以保持输出简洁

        # 步骤 1: 保存从API获取的原始元数据到 'metadata/step2'
        self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)
        
        # 步骤 2: 下载该动态的所有图片
        for index, image_info in enumerate(images_data[1:]):
            if isinstance(image_info[-1], dict) and image_info[-1].get('url'):
                # --- THIS IS THE CORRECTED LINE ---
                # 将 user_name 传递给下载器
                self.downloader.download_image(image_info[-1]['url'], user_folder, pub_ts, id_str, index + 1, user_name)
        
        # 步骤 3: 【核心调用变更】
        # 调用新方法，让它从刚刚保存的本地元数据文件中提取信息并生成最终内容JSON
        self.extractor.create_content_json_from_local_meta(user_folder, date_str, id_str)

        return True