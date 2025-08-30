# downloader.py

import os
import re
import datetime
import requests
import time

class Downloader:
    """负责下载图片文件。"""

    def download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int, user_name: str) -> bool:
        """
        下载单个图片文件，增加了重试机制和用户名显示。
        :return: bool，如果文件下载成功或已存在，则为True，否则为False。
        """
        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'

        file_ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp)', url, re.IGNORECASE)
        file_ext = file_ext_match.group(0) if file_ext_match else '.jpg'
        # 图片命名格式：日期_动态ID_序号.扩展名
        image_filename = f"{date_str}_{id_str}_{index}{file_ext}"
        filepath = os.path.join(folder, image_filename)

        green_user_name = f"\033[92m{user_name}\033[0m"

        if os.path.exists(filepath):
            # 打印消息从 downloader.py 移至 post_handler.py 以减少重复输出
            # print(f"  - [{green_user_name}] 图片已存在，跳过: {image_filename}")
            return True

        print(f"  -  正在下载用户 {green_user_name} 图片: {image_filename}")
        
        # 重试逻辑，总共尝试3次
        for attempt in range(3):
            try:
                response = requests.get(url, stream=True, timeout=30) # 增加超时
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True # 下载成功
            except requests.exceptions.RequestException as e:
                print(f"  - 下载失败: {e}")
                if attempt < 2: # 如果不是最后一次尝试
                    print(f"  - 5秒后重试... (尝试 {attempt + 2}/3)")
                    time.sleep(6)
                else:
                    print("  - 所有重试均失败，跳过此图片。")
        
        return False # 所有尝试都失败了