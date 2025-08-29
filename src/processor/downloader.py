# downloader.py

import os
import re
import datetime
import requests

class Downloader:
    """负责下载图片文件。"""

    def download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int):
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
            print(f"  - 图片已存在，跳过: {image_filename}")
            return
            
        print(f"  - 正在下载新图片: {image_filename}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"  - 下载失败: {e}")