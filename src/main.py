# main.py

from app import Application
from config import Config

def main():
    """
    主函数，用于实例化并运行应用程序。
    """
    # 1. 创建配置对象
    app_config = Config()
    
    # 2. 使用配置创建应用程序实例
    app = Application(app_config)
    
    # 3. 运行应用程序
    app.run()

if __name__ == '__main__':
    # 当此脚本作为主程序直接运行时，调用 main 函数
    main()