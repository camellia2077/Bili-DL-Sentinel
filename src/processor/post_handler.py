# processor/post_handler.py

import os
import datetime
from typing import Tuple, List, Dict
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

    def process(self, user_name: str, post_url: str, user_folder: str) -> Tuple[bool, int, List[Dict]]:
        """
        处理单个动态，协调提取、保存和下载任务。
        返回一个元组: (是否继续处理下一个动态, 成功下载的图片数, 失败下载的图片信息列表)
        """
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True, 0, []

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        if not (id_str and pub_ts):
            print(f"  - 警告：无法从元数据中获取动态 ID 或发布时间戳，跳过。")
            return True, 0, []

        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'
        
        content_json_filename = f"{date_str}_{id_str}.json"
        content_json_filepath = os.path.join(user_folder, content_json_filename)
        
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(content_json_filepath):
            return False, 0, []

        # 【修改点】在保存前检查步骤2的元数据文件是否存在
        metadata_filename = f"{date_str}_{id_str}.json"
        metadata_filepath = os.path.join(user_folder, 'metadata', 'step2', metadata_filename)
        if not os.path.exists(metadata_filepath):
            self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)
        else:
            print(f"  - 步骤2元数据 '{metadata_filename}' 已存在，跳过保存。")
        
        successful_downloads = 0
        failed_downloads_info: List[Dict] = []
        total_images_to_process = len(images_data) - 1
        skipped_count = 0

        for index, image_info in enumerate(images_data[1:]):
            if isinstance(image_info[-1], dict) and image_info[-1].get('url'):
                image_url = image_info[-1]['url']
                download_args = {
                    "url": image_url,
                    "folder": user_folder,
                    "pub_ts": pub_ts,
                    "id_str": id_str,
                    "index": index + 1,
                    "user_name": user_name
                }
                
                # 【修改点】根据 download_image 的新返回值更新计数器
                result = self.downloader.download_image(**download_args)
                if result == "SUCCESS":
                    successful_downloads += 1
                elif result == "FAILED":
                    failed_downloads_info.append(download_args)
                elif result == "SKIPPED":
                    skipped_count += 1
        
        if skipped_count > 0 and skipped_count == total_images_to_process:
            print(f"  - 所有 {skipped_count} 张图片均已存在，全部跳过。")
        elif skipped_count > 0:
            print(f"  - 跳过 {skipped_count} 张已存在的图片。")

        self.extractor.create_content_json_from_local_meta(user_folder, date_str, id_str)

        return True, successful_downloads, failed_downloads_info