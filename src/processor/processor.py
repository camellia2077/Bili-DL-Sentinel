# processor/processor.py

from api import BilibiliAPI
from config import Config
from .folder_resolver import FolderNameResolver
from .content_extractor import ContentExtractor
from .downloader import Downloader
from .metadata_saver import MetadataSaver
from .post_handler import PostHandler
from .user_processor import UserProcessor

class PostProcessorFacade:
    """
    一个简单的外观类，用于封装和协调所有子系统。
    它负责创建所有对象，并提供一个单一的入口点。
    """
    
    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        # 实例化所有独立的组件
        downloader = Downloader()
        extractor = ContentExtractor()
        saver = MetadataSaver()
        resolver = FolderNameResolver(base_output_dir, api, config)
        
        # 实例化处理流程控制器，并注入它们需要的组件
        post_handler = PostHandler(api, config, extractor, downloader, saver)
        self.user_processor = UserProcessor(api, resolver, saver, post_handler)

    def process_user(self, user_id: int, user_url: str):
        """
        启动处理单个用户的公共入口点。
        """
        self.user_processor.process(user_id, user_url)