# processor/post_handler.py

import os
import datetime
from typing import Tuple
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

    def process(self, user_name: str, post_url: str, user_folder: str) -> Tuple[bool, int, int]:
        """
        处理单个动态，协调提取、保存和下载任务。
        返回一个元组: (是否继续处理下一个动态, 成功下载的图片数, 下载失败的图片数)
        """
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True, 0, 0

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        if not (id_str and pub_ts):
            print(f"  - 警告：无法从元数据中获取动态 ID 或发布时间戳，跳过。")
            return True, 0, 0

        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'
        
        content_json_filename = f"{date_str}_{id_str}.json"
        content_json_filepath = os.path.join(user_folder, content_json_filename)
        
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(content_json_filepath):
            # 由于 tqdm 的存在，这条消息只在处理第一个已存在的动态时打印一次
            # print(f"  - 增量下载模式：内容文件 '{content_json_filename}' 已存在。")
            return False, 0, 0

        self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)
        
        successful_downloads = 0
        failed_downloads = 0
        for index, image_info in enumerate(images_data[1:]):
            if isinstance(image_info[-1], dict) and image_info[-1].get('url'):
                success = self.downloader.download_image(image_info[-1]['url'], user_folder, pub_ts, id_str, index + 1, user_name)
                if success:
                    successful_downloads += 1
                else:
                    failed_downloads += 1
        
        self.extractor.create_content_json_from_local_meta(user_folder, date_str, id_str)

        return True, successful_downloads, failed_downloads