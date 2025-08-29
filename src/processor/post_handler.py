# processor/post_handler.py

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

    def process(self, user_name: str, post_url: str, user_folder: str, current_post_num: int, total_posts: int) -> bool:
        """处理单个动态，协调提取、保存和下载任务。"""
        green_user_name = f"\033[92m{user_name}\033[0m"
        # 打印下载信息
        print(f"\n[步骤2] 正在处理用户 {green_user_name} 的动态 [{current_post_num}/{total_posts}]: {post_url}")
        
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
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
        
        self.extractor.extract_and_save(images_data, user_folder, date_str, pub_ts, id_str)

        metadata_filepath = os.path.join(user_folder, 'metadata', 'step2', f"{date_str}_{pub_ts}_{id_str}.json")
        metadata_existed = os.path.exists(metadata_filepath)

        if not (self.config.INCREMENTAL_DOWNLOAD and metadata_existed):
            self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)
        
        for index, image_info in enumerate(images_data[1:]):
            if isinstance(image_info[-1], dict) and image_info[-1].get('url'):
                self.downloader.download_image(image_info[-1]['url'], user_folder, pub_ts, id_str, index + 1)
        
        return not (self.config.INCREMENTAL_DOWNLOAD and metadata_existed)