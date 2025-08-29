# processor/user_processor.py

import os
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

    def process(self, user_id: int, user_url: str):
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
        user_folder = os.path.join(self.resolver.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"用户识别为: '{folder_name}'")
        print(f"文件将保存至: {user_folder}")

        self.saver.save_step1_metadata(user_url, user_folder, user_page_data)

        green_user_name = f"\033[92m{folder_name}\033[0m"
        print(f"\n[步骤2] 开始处理用户 {green_user_name} 的 {total_posts} 条动态...")
        
        # 使用tqdm创建进度条
        for url in tqdm(post_urls, desc=f"处理动态", unit=" 条"):
            # 更新调用，移除不再需要的 index 和 total_posts 参数
            should_continue = self.handler.process(folder_name, url, user_folder)
            if not should_continue:
                break