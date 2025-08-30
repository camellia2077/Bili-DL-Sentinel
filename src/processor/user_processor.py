# processor/user_processor.py

import os
from typing import Dict, List
from tqdm import tqdm
from api import BilibiliAPI
from .folder_resolver import FolderNameResolver
from .metadata_saver import MetadataSaver
from .post_handler import PostHandler

class UserProcessor:
    """处理单个用户的完整流程。"""

    def __init__(self, api: BilibiliAPI, resolver: FolderNameResolver, saver: MetadataSaver, handler: PostHandler):
        self.api = api
        self.resolver = resolver
        self.saver = saver
        self.handler = handler

    def process(self, user_id: int, user_url: str) -> Dict:
        """
        处理单个用户的主逻辑。
        返回包含处理统计数据的字典。
        """
        print(f"\n>>>>>>>>> 开始处理用户ID: {user_id} ({user_url}) <<<<<<<<<")

        print("\n[步骤1] 正在获取所有动态的 URL...")
        user_page_data = self.api.get_initial_metadata(user_url)

        if not user_page_data:
            print("  - 未收到任何数据，跳过此用户。")
            return {"processed_posts": 0, "downloaded_images": 0, "failed_images": 0, "folder_name": str(user_id)}

        post_urls = [item[1] for item in user_page_data if len(item) > 1]
        total_posts = len(post_urls)
        print(f"找到了 {total_posts} 条动态。")

        folder_name = self.resolver.determine_folder_name(user_id, user_page_data, post_urls)
        user_folder = os.path.join(self.resolver.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"用户识别为: '{folder_name}'")
        print(f"文件将保存至: {user_folder}")

        self.saver.save_step1_metadata(user_url, user_folder, user_page_data)

        # 在处理新动态之前，重试之前失败的下载
        successful_retries, _, persistent_failures = self.handler.downloader.retry_undownloaded(user_folder, folder_name)

        green_user_name = f"\033[92m{folder_name}\033[0m"
        print(f"\n[步骤2] 开始处理用户 {green_user_name} 的 {total_posts} 条动态...")
        
        processed_posts_count = 0
        # 下载成功总数从重试成功数开始计算
        total_successful_downloads = successful_retries
        # 用于收集本次运行中新失败的下载
        session_failures: List[Dict] = []
        
        for url in tqdm(post_urls, desc=f"处理动态", unit=" 条"):
            should_continue, successful, new_failures = self.handler.process(folder_name, url, user_folder)
            
            if not should_continue:
                green_user_name_plain = f"'{folder_name}'"
                print(f"\n  - 增量下载模式：检测到已下载的内容，将停止处理用户 {green_user_name_plain} 的剩余动态。")
                break
            
            processed_posts_count += 1
            total_successful_downloads += successful
            if new_failures:
                session_failures.extend(new_failures)

        # 合并本次运行失败的和之前一直失败的
        all_failures = persistent_failures + session_failures
        self.handler.downloader.save_undownloaded_list(user_folder, all_failures)
        
        total_failed_downloads = len(all_failures)

        return {
            "processed_posts": processed_posts_count,
            "downloaded_images": total_successful_downloads,
            "failed_images": total_failed_downloads,
            "folder_name": folder_name
        }