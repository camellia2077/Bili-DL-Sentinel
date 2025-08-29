# content_extractor.py

import os
import json
from typing import List, Dict

class ContentExtractor:
    """负责从原始元数据中提取所需信息并保存。"""

    def extract_and_save(self, images_data: List[Dict], user_folder: str, date_str: str, pub_ts: int, id_str: str, post_url: str):
        """从元数据中提取标题、内容和统计数据，并保存到JSON文件。"""
        title = "null"
        content = "null"
        content_found = False
        like_count = 0
        comment_count = 0
        forward_count = 0
        favorite_count = 0

        try:
            modules = images_data[0][-1].get('detail', {}).get('modules', {})
            if not modules:
                raise ValueError("元数据中缺少 'modules' 键")

            title_text = modules.get('module_title', {}).get('text')
            if title_text:
                title = title_text

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
            
            module_stat = modules.get('module_stat', {})
            if module_stat:
                like_count = module_stat.get('like', {}).get('count', 0)
                comment_count = module_stat.get('comment', {}).get('count', 0)
                forward_count = module_stat.get('forward', {}).get('count', 0)
                favorite_count = module_stat.get('favorite', {}).get('count', 0)

        except (IndexError, KeyError, TypeError, ValueError) as e:
            print(f"  - 提取文本内容或统计数据时发生错误: {e}")

        json_filename = f"{date_str}_{pub_ts}_{id_str}.json"
        json_filepath = os.path.join(user_folder, json_filename)

        if not os.path.exists(json_filepath):
            data_to_save = {
                "url": post_url,
                "id_str": id_str,
                "pub_ts": pub_ts,
                "title": title,
                "content": content,
                "stats": { "likes": like_count, "comments": comment_count, "forwards": forward_count, "favorites": favorite_count }
            }
            
            print(f"  - 正在保存JSON内容到: {json_filename}")
            try:
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"  - 警告：保存JSON文件失败: {e}")
        else:
            print(f"  - JSON文件已存在，跳过: {json_filename}")