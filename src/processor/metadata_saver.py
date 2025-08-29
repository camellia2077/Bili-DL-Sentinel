# processor/metadata_saver.py

import os
import re
import json
from typing import List, Dict

class MetadataSaver:
    """负责保存原始元数据文件。"""

    def save_step1_metadata(self, user_url: str, user_folder: str, user_page_data: List[Dict]):
        """保存步骤1获取的用户主页元数据。"""
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

    def save_step2_metadata(self, images_data: List[Dict], user_folder: str, date_str: str, pub_ts: int, id_str: str):
        """保存步骤2获取的单个动态元数据。"""
        # 元数据的命名格式
        metadata_filename = f"{date_str}_{id_str}.json"
        metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
        os.makedirs(metadata_dir, exist_ok=True)
        filepath = os.path.join(metadata_dir, metadata_filename)
        
        print(f"  - 正在保存动态 {id_str} 的步骤2元数据...")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(images_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  - 警告：保存元数据失败: {e}")