# processor.py

import os
import re
import datetime
import json
from typing import List, Dict

# 从新模块导入依赖项
from api import BilibiliAPI
from config import Config
from .folder_resolver import FolderNameResolver
from .content_extractor import ContentExtractor
from .downloader import Downloader

class PostProcessor:
    """
    总协调器，负责编排整个处理流程。
    它使用辅助类来处理具体任务。
    """
    
    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        self.base_output_dir = base_output_dir
        self.api = api
        self.config = config
        # 实例化辅助类
        self.resolver = FolderNameResolver(base_output_dir, api, config)
        self.extractor = ContentExtractor()
        self.downloader = Downloader()

    def process_user(self, user_id: int, user_url: str):
        """处理单个用户的主逻辑。"""
        print(f"\n>>>>>>>>> 开始处理用户ID: {user_id} ({user_url}) <<<<<<<<<")

        print("\n[步骤1] 正在获取所有动态的 URL...")
        user_page_data = self.api.get_initial_metadata(user_url)

        if not user_page_data:
            print("  - 未收到任何数据，跳过此用户。")
            return

        post_urls = [item[1] for item in user_page_data if len(item) > 1]
        total_posts = len(post_urls)
        print(f"找到了 {total_posts} 条动态。")

        folder_name = self.resolver.determine_folder_name(user_id, user_page_data, post_urls)
        user_folder = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"用户识别为: '{folder_name}'")
        print(f"文件将保存至: {user_folder}")

        # 保存步骤1的原始元数据
        self._save_step1_metadata(user_url, user_folder, user_page_data)

        for index, url in enumerate(post_urls):
            should_continue = self._process_single_post(url, user_folder, index + 1, total_posts)
            if not should_continue:
                break
    
    def _save_step1_metadata(self, user_url: str, user_folder: str, user_page_data: List[Dict]):
        """保存步骤1获取的原始元数据。"""
        metadata_dir = os.path.join(user_folder, 'metadata', 'step1')
        os.makedirs(metadata_dir, exist_ok=True)
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', user_url.replace("https://", "").replace("http://", "")) + ".json"
        metadata_filepath = os.path.join(metadata_dir, safe_filename)
        
        print(f"  - 正在保存步骤1的元数据到: {os.path.join(os.path.basename(user_folder), 'metadata', 'step1', safe_filename)}")
        try:
            with open(metadata_filepath, 'w', encoding='utf-8') as f:
                json.dump(user_page_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  - 警告：保存步骤1的元数据失败: {e}")

    def _process_single_post(self, post_url: str, user_folder: str, current_post_num: int, total_posts: int) -> bool:
        """处理单个动态，协调提取、保存和下载任务。"""
        print(f"\n[步骤2] 正在处理动态 [{current_post_num}/{total_posts}]: {post_url}")
        
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True

        # 从元数据中提取关键信息
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
        
        # 委派任务给辅助类
        self.extractor.extract_and_save(images_data, user_folder, date_str, pub_ts, id_str)

        # 保存步骤2的原始元数据
        metadata_filename = f"{date_str}_{pub_ts}_{id_str}.json"
        metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_filepath = os.path.join(metadata_dir, metadata_filename)

        metadata_existed = os.path.exists(metadata_filepath)

        if not (self.config.INCREMENTAL_DOWNLOAD and metadata_existed):
            print(f"  - 正在保存动态 {id_str} 的步骤2元数据...")
            try:
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    json.dump(images_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"  - 警告：保存元数据失败: {e}")
        
        # 委派下载任务
        for index, image_info in enumerate(images_data[1:]):
            if isinstance(image_info[-1], dict) and image_info[-1].get('url'):
                self.downloader.download_image(image_info[-1]['url'], user_folder, pub_ts, id_str, index + 1)
        
        return not (self.config.INCREMENTAL_DOWNLOAD and metadata_existed)