# config.py

class Config:
    """
    一个专门用于保存所有应用程序配置的类。
    这样做的好处是，所有可调整的路径和参数都集中在一个地方，方便修改。
    """
    # 【修改】要下载的用户数字ID列表。
    USERS_ID = [10982073, 3461567555307880]
    
    # 【新增】用户ID到文件夹名称的手动映射。
    # 当API无法获取用户名时，程序会优先使用这里的名称。
    # 键必须是字符串形式的数字ID，值是您希望使用的文件夹名。
    USER_ID_TO_NAME_MAP = {
        "10982073": "明前奶粉罐",
        "3461567555307880": "羲拉C3C"
        # "另一个ID": "对应的文件夹名"
    }

    # 增量下载开关。如果设为 True，当程序遇到第一个已存在于本地的动态元数据时，
    # 将会跳过该用户的所有剩余动态，从而大大提高后续运行的效率。
    INCREMENTAL_DOWNLOAD = True
    
    # Cookie 文件路径，用于 gallery-dl 进行需要登录的访问
    COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
    
    # 图片和元数据保存的基础输出目录
    OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl/bilibili_images"