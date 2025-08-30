# downloader.py

import os
import re
import datetime
import requests
import time
import json
from typing import List, Dict, Tuple, Literal

# 定义一个类型来表示下载结果，使代码更清晰
DownloadResult = Literal["SUCCESS", "SKIPPED", "FAILED"]

class Downloader:
    """负责下载图片文件，并管理失败的下载。"""

    def _get_undownloaded_filepath(self, folder: str) -> str:
        """获取undownloaded.json文件的完整路径。"""
        return os.path.join(folder, 'undownloaded.json')

    def retry_undownloaded(self, folder: str, user_name: str) -> Tuple[int, int, List[Dict]]:
        """
        尝试重新下载之前失败的图片。
        :return: (成功下载数, 失败下载数, 仍然未下载的列表)
        """
        undownloaded_path = self._get_undownloaded_filepath(folder)
        if not os.path.exists(undownloaded_path):
            return 0, 0, []

        print(f"\n  - 检测到 'undownloaded.json'，正在尝试重新下载 {user_name} 的失败项目...")
        
        try:
            with open(undownloaded_path, 'r', encoding='utf-8') as f:
                failed_items = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  - 警告：读取 'undownloaded.json' 文件失败或格式错误，跳过重试: {e}")
            return 0, 0, []

        still_failed = []
        successful_retries = 0
        failed_retries = 0

        for item in failed_items:
            result = self.download_image(**item)
            if result == "SUCCESS":
                successful_retries += 1
            elif result == "FAILED":
                failed_retries += 1
                still_failed.append(item)
            # 如果结果是 "SKIPPED"，意味着文件现在存在了，所以它不再是失败项，
            # 但它不是在这次重试中下载的，所以 successful_retries 不增加。
        
        print(f"  - 重试完成: {successful_retries} 个成功, {failed_retries} 个失败。")
        return successful_retries, failed_retries, still_failed

    def save_undownloaded_list(self, folder: str, undownloaded_items: List[Dict]):
        """将未下载的图片信息列表保存到 undownloaded.json 文件中。"""
        undownloaded_path = self._get_undownloaded_filepath(folder)
        
        unique_items = []
        seen_identifiers = set()
        for item in undownloaded_items:
            identifier = (item['url'], item['index'])
            if identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                unique_items.append(item)

        if not unique_items:
            if os.path.exists(undownloaded_path):
                try:
                    os.remove(undownloaded_path)
                    print("\n  - 所有图片均已成功下载，已删除 'undownloaded.json'。")
                except OSError as e:
                    print(f"  - 警告：删除 'undownloaded.json' 文件失败: {e}")
            return

        print(f"\n  - 将 {len(unique_items)} 个未下载的图片信息保存到 'undownloaded.json'...")
        try:
            with open(undownloaded_path, 'w', encoding='utf-8') as f:
                json.dump(unique_items, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"  - 错误：写入 'undownloaded.json' 文件失败: {e}")


    def download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int, user_name: str) -> DownloadResult:
        """
        下载单个图片文件，增加了重试机制和用户名显示。
        :return: "SUCCESS" (下载成功), "SKIPPED" (文件已存在), 或 "FAILED" (下载失败).
        """
        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'

        file_ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp)', url, re.IGNORECASE)
        file_ext = file_ext_match.group(0) if file_ext_match else '.jpg'
        image_filename = f"{date_str}_{id_str}_{index}{file_ext}"
        filepath = os.path.join(folder, image_filename)

        if os.path.exists(filepath):
            # 文件已存在，返回 "SKIPPED" 状态
            return "SKIPPED"

        green_user_name = f"\033[92m{user_name}\033[0m"
        print(f"  -  正在下载用户 {green_user_name} 图片: {image_filename}")
        
        for attempt in range(3):
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return "SUCCESS" # 下载成功
            except requests.exceptions.RequestException as e:
                print(f"  - 下载失败: {e}")
                if attempt < 2:
                    print(f"  - 5秒后重试... (尝试 {attempt + 2}/3)")
                    time.sleep(6)
                else:
                    print("  - 所有重试均失败，跳过此图片。")
        
        return "FAILED" # 所有尝试都失败了