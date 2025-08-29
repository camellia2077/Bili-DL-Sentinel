# src/processor/content_extractor.py

import os
import json
from typing import List, Dict

class ContentExtractor:
    """负责从本地保存的原始元数据中提取信息并生成最终内容JSON文件。"""

    def create_content_json_from_local_meta(self, user_folder: str, date_str: str, id_str: str):
        """
        【核心重构功能】
        从本地 'metadata/step2' 文件夹中读取指定动态的原始元数据，
        从中提取所有必要字段（url, id_str, pub_ts, pub_time, title, content, stats），
        然后创建或更新最终的内容JSON文件。

        此方法确保了所有数据提取操作都基于本地文件，方便调试。
        """
        step2_metadata_filename = f"{date_str}_{id_str}.json"
        step2_metadata_path = os.path.join(user_folder, 'metadata', 'step2', step2_metadata_filename)
        
        final_content_filename = f"{date_str}_{id_str}.json"
        final_content_filepath = os.path.join(user_folder, final_content_filename)

        # 步骤1: 检查本地的 step2 元数据文件是否存在
        if not os.path.exists(step2_metadata_path):
            print(f"  - 错误：无法找到用于提取内容的源元数据文件: {step2_metadata_filename}")
            return

        # 步骤2: 读取并解析 step2 元数据文件
        try:
            with open(step2_metadata_path, 'r', encoding='utf-8') as f:
                images_data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  - 错误：读取或解析源元数据文件 {step2_metadata_filename} 失败: {e}")
            return
            
        print(f"  - 正在从本地元数据 '{step2_metadata_filename}' 中提取内容...")

        # 步骤3: 从加载的数据中提取所有字段
        try:
            # 初始化所有变量
            post_url = "null"
            username = "null"
            pub_ts = 0
            pub_time = "null"
            title = "null"
            content = "null"
            content_found = False
            like_count, comment_count, forward_count, favorite_count = 0, 0, 0, 0
            
            # 安全地访问嵌套数据
            first_image_meta = images_data[0][-1] if images_data and images_data[0] else {}
            detail = first_image_meta.get('detail', {})
            modules = detail.get('modules', {})
            module_author = modules.get('module_author', {})
            
            # 提取基础信息
            post_url = first_image_meta.get('url', post_url)
            id_str_from_meta = detail.get('id_str', id_str) # 优先使用元数据中的id_str
            username = module_author.get('name', username)
            pub_ts = module_author.get('pub_ts', pub_ts)
            pub_time = module_author.get('pub_time', pub_time)
            
            # 提取标题
            title_text = modules.get('module_title', {}).get('text')
            if title_text:
                title = title_text

            # 提取正文内容（与之前逻辑相同）
            content_parts = []
            module_dynamic = modules.get('module_dynamic', {})
            if module_dynamic and module_dynamic.get('desc') and module_dynamic['desc'].get('rich_text_nodes'):
                for node in module_dynamic['desc']['rich_text_nodes']:
                    if node.get('type') == 'RICH_TEXT_NODE_TYPE_TEXT' and node.get('text'):
                        content_parts.append(node['text'])
                if content_parts:
                    content_found = True
            
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
            
            # 提取统计数据
            module_stat = modules.get('module_stat', {})
            if module_stat:
                like_count = module_stat.get('like', {}).get('count', 0)
                comment_count = module_stat.get('comment', {}).get('count', 0)
                forward_count = module_stat.get('forward', {}).get('count', 0)
                favorite_count = module_stat.get('favorite', {}).get('count', 0)

            # 步骤4: 准备要保存的最终数据结构
            data_to_save = {
                "url": post_url,
                "id_str": id_str_from_meta,
                "username": username,
                "pub_ts": pub_ts,
                "pub_time": pub_time,
                "title": title,
                "content": content,
                "stats": { "likes": like_count, "comments": comment_count, "forwards": forward_count, "favorites": favorite_count }
            }

            # 步骤5: 写入最终的内容JSON文件
            print(f"  - 正在创建最终内容JSON文件: {final_content_filename}")
            with open(final_content_filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

        except (IndexError, KeyError, TypeError, ValueError) as e:
            print(f"  - 从本地元数据提取信息时发生错误: {e}")