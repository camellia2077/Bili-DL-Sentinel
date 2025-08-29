# api.py

import subprocess
import json
from typing import List, Dict, Any, Optional

class BilibiliAPI:
    """一个用于通过 gallery-dl 工具与 Bilibili 交互的封装器。"""
    
    def __init__(self, cookie_file: Optional[str]):
        """
        初始化 API 封装器。
        :param cookie_file: 指向 cookies.txt 文件的路径，可以为 None。
        """
        self.cookie_file = cookie_file

    def _run_command(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        一个集中的辅助函数，用于运行 gallery-dl 并解析其 JSON 输出。
        :param url: 要传递给 gallery-dl 的 URL。
        :return: 解析后的 JSON 数据，如果出错则返回 None。
        """
        command = ['gallery-dl', '-j', url]
        if self.cookie_file:
            command.extend(['--cookies', self.cookie_file])
        try:
            # 运行子进程，捕获输出，并使用 utf-8 编码
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"  - 错误: gallery-dl 执行失败，URL: {url}。错误输出: {e.stderr.strip()}")
        except json.JSONDecodeError:
            print(f"  - 错误: 解析来自 gallery-dl 的 JSON 数据失败，URL: {url}。")
        except Exception as e:
            print(f"  - 错误: 运行 gallery-dl 时发生未知错误: {e}")
        return None
    
    def get_post_metadata(self, post_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取单个动态的详细元数据。
        :param post_url: 单个动态的 URL。
        :return: 包含元数据信息的列表，或在失败时返回 None。
        """
        return self._run_command(post_url)

    def get_initial_metadata(self, user_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取用户主页的初始元数据转储，这通常包含了所有动态的 URL 列表。
        :param user_url: 用户主页的 URL。
        :return: 包含元数据信息的列表，或在失败时返回 None。
        """
        return self._run_command(user_url)