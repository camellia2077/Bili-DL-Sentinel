# config.py

class Config:
    """
    一个专门用于保存所有应用程序配置的类。
    这样做的好处是，所有可调整的路径和参数都集中在一个地方，方便修改。
    """
    # Cookie 文件路径，用于 gallery-dl 进行需要登录的访问
    COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
    
    # 图片和元数据保存的基础输出目录
    OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl/bilibili_images"
    
    # 包含用户主页 URL 的输入文本文件路径
    USER_INPUT_FILE_PATH = "C:/Base1/bili/gallery-dl/users.txt"
    
    # 归档数据库的文件名
    ARCHIVE_DB_NAME = "archive.sqlite"