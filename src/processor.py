# processor.py

import os
import re
import datetime
import json
import requests
from typing import List, Dict, Any, Optional

# 从其他模块导入依赖项
from api import BilibiliAPI
from config import Config

class PostProcessor:
    """处理下载帖子和文件的业务逻辑。"""
    
    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        self.base_output_dir = base_output_dir
        self.api = api
        self.config = config

    def _sanitize_filename(self, filename: str) -> str:
        """清理字符串，使其可以安全地用作文件名。"""
        return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

    def _scan_for_existing_folder(self, user_id: int) -> Optional[str]:
        """扫描输出目录，通过元数据反向查找与user_id匹配的文件夹名。"""
        print("  - 警告：正在扫描现有文件夹以匹配用户ID... 这可能需要一些时间。")
        try:
            for folder_name in os.listdir(self.base_output_dir):
                user_folder = os.path.join(self.base_output_dir, folder_name)
                if not os.path.isdir(user_folder):
                    continue

                meta_dir = os.path.join(user_folder, 'metadata', 'step2')
                if not os.path.isdir(meta_dir):
                    continue

                for meta_file in os.listdir(meta_dir):
                    if not meta_file.endswith('.json'):
                        continue
                    
                    try:
                        with open(os.path.join(meta_dir, meta_file), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        uid_from_meta = data[0][-1].get('detail', {}).get('modules', {}).get('module_author', {}).get('mid')
                        if uid_from_meta and uid_from_meta == user_id:
                            print(f"  - 匹配成功！在文件夹 '{folder_name}' 中找到了用户ID {user_id}。")
                            return folder_name
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        except Exception as e:
            print(f"  - 扫描文件夹时出错: {e}")
        return None

    def _determine_folder_name(self, user_id: int, user_page_data: Optional[List[Dict]], post_urls: List[str]) -> str:
        """
        【优化】通过多级回退机制确定文件夹名称。
        最高优先级: Config映射 -> API获取 -> 扫描本地文件夹 -> 数字ID
        """
        user_id_str = str(user_id)
        if user_id_str in self.config.USER_ID_TO_NAME_MAP:
            mapped_name = self.config.USER_ID_TO_NAME_MAP[user_id_str]
            print(f"  - 在Config文件中找到高优先级映射: {user_id_str} -> {mapped_name}")
            return self._sanitize_filename(mapped_name)

        print("  - Config文件中无映射，尝试从API获取用户名...")
        username = None
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            username = user_page_data[0][-1].get('username')
        
        if not username and post_urls:
            detailed_metadata = self.api.get_post_metadata(post_urls[0])
            if detailed_metadata:
                first_post_detail = detailed_metadata[0][-1]
                username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')

        if username:
            print(f"  - 已通过API获取用户名: {username}")
            return self._sanitize_filename(username)

        print("  - 未能从API获取用户名，将尝试扫描本地文件夹...")
        folder_name = self._scan_for_existing_folder(user_id)
        if folder_name:
            return folder_name

        print(f"  - 未找到任何匹配项，将使用数字ID '{user_id}' 作为文件夹名。")
        return str(user_id)

    def process_user(self, user_id: int, user_url: str):
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

        folder_name = self._determine_folder_name(user_id, user_page_data, post_urls)
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
    
    # --- 【重点修改】更新此函数以兼容两种JSON结构 ---
    def _extract_and_save_text_content(self, images_data: List[Dict], user_folder: str, date_str: str, pub_ts: int, id_str: str):
        """从元数据中提取标题和内容，并保存到txt文件。"""
        title = "null"
        content = "null"
        content_found = False

        try:
            modules = images_data[0][-1].get('detail', {}).get('modules', {})
            if not modules:
                # 如果没有modules，直接跳出
                raise ValueError("元数据中缺少 'modules' 键")

            # 1. 提取标题 (逻辑不变)
            title_text = modules.get('module_title', {}).get('text')
            if title_text:
                title = title_text

            # 2. 提取内容 (兼容两种结构)
            content_parts = []
            
            # 尝试结构一: module_dynamic (常见于图文动态)
            module_dynamic = modules.get('module_dynamic', {})
            if module_dynamic and module_dynamic.get('desc') and module_dynamic['desc'].get('rich_text_nodes'):
                for node in module_dynamic['desc']['rich_text_nodes']:
                    if node.get('type') == 'RICH_TEXT_NODE_TYPE_TEXT' and node.get('text'):
                        content_parts.append(node['text'])
                if content_parts:
                    content_found = True
            
            # 尝试结构二: module_content (常见于纯文本动态)
            if not content_found:
                module_content = modules.get('module_content', {})
                if module_content and module_content.get('paragraphs'):
                    for paragraph in module_content['paragraphs']:
                        text_block = paragraph.get('text', {})
                        if text_block and text_block.get('nodes'):
                            for node in text_block['nodes']:
                                if node.get('type') == 'TEXT_NODE_TYPE_WORD' and node.get('word', {}).get('words'):
                                    content_parts.append(node['word']['words'])

            if content_parts:
                content = "".join(content_parts)

        except (IndexError, KeyError, TypeError, ValueError) as e:
            print(f"  - 提取文本内容时发生错误或遇到未知结构: {e}")

        # 3. 构建并保存txt文件 (逻辑不变)
        txt_filename = f"{date_str}_{pub_ts}_{id_str}.txt"
        txt_filepath = os.path.join(user_folder, txt_filename)

        if not os.path.exists(txt_filepath):
            print(f"  - 正在保存文本内容到: {txt_filename}")
            try:
                with open(txt_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"标题: {title}\n")
                    f.write(f"内容: {content}\n")
            except Exception as e:
                print(f"  - 警告：保存文本文件失败: {e}")
        else:
            print(f"  - 文本文件已存在，跳过: {txt_filename}")

    def _process_single_post(self, post_url: str, user_folder: str, current_post_num: int, total_posts: int) -> bool:
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
        
        self._extract_and_save_text_content(images_data, user_folder, date_str, pub_ts, id_str)

        metadata_filename = f"{date_str}_{pub_ts}_{id_str}.json"
        metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_filepath = os.path.join(metadata_dir, metadata_filename)

        metadata_existed = os.path.exists(metadata_filepath)

        if self.config.INCREMENTAL_DOWNLOAD and metadata_existed:
            print(f"  - 增量检查：发现已存在的元数据文件。现在将检查该动态的图片完整性...")
        else:
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
        
        if self.config.INCREMENTAL_DOWNLOAD and metadata_existed:
            print("  - 图片完整性检查完成。停止处理此用户以进行下一次同步。")
            return False
        
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