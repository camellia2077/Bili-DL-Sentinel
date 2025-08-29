# processor.py

import os
import re
import datetime
import json
import requests
from typing import List, Dict, Any, Optional

# 从其他模块导入依赖项
from api import BilibiliAPI
from database import ArchiveDB

class PostProcessor:
    """处理下载帖子和文件的业务逻辑。"""
    
    def __init__(self, base_output_dir: str, api: BilibiliAPI, db: ArchiveDB):
        """
        初始化处理器。
        :param base_output_dir: 文件保存的基础目录。
        :param api: BilibiliAPI 的实例。
        :param db: ArchiveDB 的实例。
        """
        self.base_output_dir = base_output_dir
        self.api = api
        self.db = db

    def _determine_folder_name(self, user_url: str, user_page_data: Optional[List[Dict]], post_urls: List[str]) -> str:
        """
        通过检查步骤1和步骤2的元数据来确定合适的文件夹名称。
        :param user_url: 用户的 URL，用于回退方案。
        :param user_page_data: 从用户主页获取的初始元数据。
        :param post_urls: 该用户的所有动态 URL 列表。
        :return: 清理过的、可用作文件夹名称的字符串。
        """
        username = None
        # 尝试 1: 从用户主页的摘要元数据（步骤1）中获取用户名
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            first_post_summary = user_page_data[0][-1]
            username = first_post_summary.get('username')

        # 尝试 2: 如果没有获取到用户名，则获取第一个动态的详细元数据（步骤2）
        if not username and post_urls:
            print("  - 摘要中无用户名，正在检查第一个动态的详细信息...")
            first_post_url = post_urls[0]
            detailed_metadata = self.api.get_post_metadata(first_post_url)
            if detailed_metadata:
                first_post_detail = detailed_metadata[0][-1]
                # 尝试从多个可能的字段获取用户名
                username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')

        if username:
            # 清理用户名，移除在文件名中非法的字符
            return re.sub(r'[\\/*?:"<>|]', "", username).strip()

        # 回退方案: 使用用户的数字 ID 作为文件夹名
        match = re.search(r'space.bilibili.com/(\d+)', user_url)
        return match.group(1) if match else re.sub(r'[^a-zA-Z0-9_-]', '_', user_url)

    def process_user(self, user_url: str):
        """
        处理单个用户的主逻辑。
        :param user_url: 要处理的用户的 Bilibili 主页 URL。
        """
        print(f"\n>>>>>>>>> 开始处理用户: {user_url} <<<<<<<<<")

        # [步骤1] 首先获取初始数据和所有动态的 URL
        print("\n[步骤1] 正在获取所有动态的 URL...")
        user_page_data = self.api.get_initial_metadata(user_url)

        if not user_page_data:
            print("  - 未收到任何数据，跳过此用户。")
            return

        post_urls = [item[1] for item in user_page_data if len(item) > 1]
        total_posts = len(post_urls)
        print(f"找到了 {total_posts} 条动态。")

        # 在创建目录或保存文件之前，确定文件夹名称
        folder_name = self._determine_folder_name(user_url, user_page_data, post_urls)
        user_folder = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"用户识别为: '{folder_name}'")
        print(f"文件将保存至: {user_folder}")

        # 保存步骤1的元数据
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

        # 遍历所有动态并处理，同时显示进度
        for index, url in enumerate(post_urls):
            self._process_single_post(url, user_folder, index + 1, total_posts)

    def _process_single_post(self, post_url: str, user_folder: str, current_post_num: int, total_posts: int):
        """
        处理单个动态：获取元数据，下载图片，并更新归档。
        :param post_url: 单个动态的 URL。
        :param user_folder: 该用户的专属文件夹路径。
        :param current_post_num: 当前处理的是第几个动态。
        :param total_posts: 总共有多少个动态。
        """
        print(f"\n[步骤2] 正在处理动态 [{current_post_num}/{total_posts}]: {post_url}")
        
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return

        # 提取动态的关键信息：ID 和发布时间戳
        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        # 保存步骤2的详细元数据
        if id_str and pub_ts:
            try:
                date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                date_str = 'unknown_date'
            
            metadata_filename = f"{date_str}_{pub_ts}_{id_str}.json"
            metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
            os.makedirs(metadata_dir, exist_ok=True)
            metadata_filepath = os.path.join(metadata_dir, metadata_filename)

            if not os.path.exists(metadata_filepath):
                print(f"  - 正在保存动态 {id_str} 的步骤2元数据...")
                try:
                    with open(metadata_filepath, 'w', encoding='utf-8') as f:
                        json.dump(images_data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"  - 警告：保存元数据失败: {e}")
            else:
                print(f"  - 动态 {id_str} 的元数据已存在，跳过保存。")

        # 遍历动态中的每张图片
        for index, image_info in enumerate(images_data[1:]):
            if not isinstance(image_info[-1], dict): continue

            meta = image_info[-1]
            image_url = meta.get('url')
            
            if not all([id_str, pub_ts, image_url]): continue

            # 创建一个唯一的归档条目
            archive_entry = f"bilibili{id_str}_{index + 1}"
            if self.db.exists(archive_entry):
                print(f"  - 在归档中找到，跳过: {archive_entry}")
                continue

            self._download_image(image_url, user_folder, pub_ts, id_str, index + 1, archive_entry)

    def _download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int, archive_entry: str):
        """
        下载单个图片文件。
        :param url: 图片的 URL。
        :param folder: 保存的目标文件夹。
        :param pub_ts: 发布时间戳。
        :param id_str: 动态 ID。
        :param index: 图片在动态中的序号。
        :param archive_entry: 用于写入数据库的归档条目。
        """
        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'

        file_ext = os.path.splitext(url)[1] or '.jpg'
        image_filename = f"{date_str}_{pub_ts}_{id_str}_{index}{file_ext}"
        filepath = os.path.join(folder, image_filename)

        if os.path.exists(filepath):
            print(f"  - 文件已存在，跳过: {image_filename}")
            # 注意：即使文件存在，也应检查是否已归档，如果未归档则补上
            if not self.db.exists(archive_entry):
                self.db.add(archive_entry)
            return
            
        print(f"  - 正在下载: {image_filename}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status() # 如果请求失败 (如 404), 抛出异常
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            # 下载成功后才添加到归档
            self.db.add(archive_entry)
        except requests.exceptions.RequestException as e:
            print(f"  - 下载失败: {e}")