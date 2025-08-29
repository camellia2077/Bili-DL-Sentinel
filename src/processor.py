# processor.py

import os
import re
import datetime
import json
import requests
from typing import List, Dict, Any, Optional

# 从其他模块导入依赖项
from api import BilibiliAPI
from config import Config  # 导入 Config 类以进行类型提示

class PostProcessor:
    """处理下载帖子和文件的业务逻辑。"""
    
    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        """
        初始化处理器。
        :param base_output_dir: 文件保存的基础目录。
        :param api: BilibiliAPI 的实例。
        :param config: 应用程序的配置对象。
        """
        self.base_output_dir = base_output_dir
        self.api = api
        self.config = config # 保存配置对象

    def _determine_folder_name(self, user_url: str, user_page_data: Optional[List[Dict]], post_urls: List[str]) -> str:
        """
        通过检查步骤1和步骤2的元数据来确定合适的文件夹名称。
        :param user_url: 用户的 URL，用于回退方案。
        :param user_page_data: 从用户主页获取的初始元数据。
        :param post_urls: 该用户的所有动态 URL 列表。
        :return: 清理过的、可用作文件夹名称的字符串。
        """
        username = None
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            first_post_summary = user_page_data[0][-1]
            username = first_post_summary.get('username')

        if not username and post_urls:
            print("  - 摘要中无用户名，正在检查第一个动态的详细信息...")
            first_post_url = post_urls[0]
            detailed_metadata = self.api.get_post_metadata(first_post_url)
            if detailed_metadata:
                first_post_detail = detailed_metadata[0][-1]
                username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')

        if username:
            return re.sub(r'[\\/*?:"<>|]', "", username).strip()

        match = re.search(r'space.bilibili.com/(\d+)', user_url)
        return match.group(1) if match else re.sub(r'[^a-zA-Z0-9_-]', '_', user_url)

    def process_user(self, user_url: str):
        """
        处理单个用户的主逻辑。
        :param user_url: 要处理的用户的 Bilibili 主页 URL。
        """
        print(f"\n>>>>>>>>> 开始处理用户: {user_url} <<<<<<<<<")

        print("\n[步骤1] 正在获取所有动态的 URL...")
        user_page_data = self.api.get_initial_metadata(user_url)

        if not user_page_data:
            print("  - 未收到任何数据，跳过此用户。")
            return

        post_urls = [item[1] for item in user_page_data if len(item) > 1]
        total_posts = len(post_urls)
        print(f"找到了 {total_posts} 条动态。")

        folder_name = self._determine_folder_name(user_url, user_page_data, post_urls)
        user_folder = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"用户识别为: '{folder_name}'")
        print(f"文件将保存至: {user_folder}")

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

        for index, url in enumerate(post_urls):
            should_continue = self._process_single_post(url, user_folder, index + 1, total_posts)
            if not should_continue:
                break

    def _process_single_post(self, post_url: str, user_folder: str, current_post_num: int, total_posts: int) -> bool:
        """
        处理单个动态：获取元数据，下载图片。
        如果启用了增量下载并找到已存在的元数据文件，则返回 False。
        :return: bool - 如果应继续处理，返回 True，否则返回 False。
        """
        print(f"\n[步骤2] 正在处理动态 [{current_post_num}/{total_posts}]: {post_url}")
        
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
        
        metadata_filename = f"{date_str}_{pub_ts}_{id_str}.json"
        metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_filepath = os.path.join(metadata_dir, metadata_filename)

        # --- 新增：基于文件存在的增量下载检查 ---
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(metadata_filepath):
            print(f"  - 增量检查：发现已存在的元数据文件 for a post ID {id_str}。")
            print("  - 停止处理此用户以进行下一次同步。")
            return False  # 返回 False，通知调用者停止

        print(f"  - 正在保存动态 {id_str} 的步骤2元数据...")
        try:
            with open(metadata_filepath, 'w', encoding='utf-8') as f:
                json.dump(images_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  - 警告：保存元数据失败: {e}")

        for index, image_info in enumerate(images_data[1:]):
            if not isinstance(image_info[-1], dict): continue

            meta = image_info[-1]
            image_url = meta.get('url')
            
            if not image_url: continue

            self._download_image(image_url, user_folder, pub_ts, id_str, index + 1)
            
        return True

    def _download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int):
        """下载单个图片文件。"""
        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'

        file_ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp)', url, re.IGNORECASE)
        file_ext = file_ext_match.group(0) if file_ext_match else '.jpg'
        image_filename = f"{date_str}_{pub_ts}_{id_str}_{index}{file_ext}"
        filepath = os.path.join(folder, image_filename)

        if os.path.exists(filepath):
            print(f"  - 文件已存在，跳过: {image_filename}")
            return
            
        print(f"  - 正在下载: {image_filename}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"  - 下载失败: {e}")