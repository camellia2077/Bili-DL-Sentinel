# config.py

class Config:
    """
    一个专门用于保存所有应用程序配置的类。
    这样做的好处是，所有可调整的路径和参数都集中在一个地方，方便修改。
    """
    # 【新增】要下载的用户数字ID列表。程序将遍历此列表。
    USERS_ID = [10982073,3461567555307880]

    # 【新增】增量下载开关。如果设为 True，当程序遇到第一个已存在于本地的动态元数据时，
    # 将会跳过该用户的所有剩余动态，从而大大提高后续运行的效率。
    INCREMENTAL_DOWNLOAD = True
    
    # Cookie 文件路径，用于 gallery-dl 进行需要登录的访问
    COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
    
    # 图片和元数据保存的基础输出目录
    OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl/bilibili_images"