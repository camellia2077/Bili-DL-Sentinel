import subprocess
import json
import requests
import os
import sys
import datetime

# --- 全局配置区 ---
COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl"
# 您的输入文件现在应该包含完整的URL，而不仅仅是ID
USER_INPUT_FILE_PATH = "C:/Base1/bili/gallery-dl/users.txt"


def get_all_post_urls(user_url: str, cookie_file: str = None) -> list:
    """第一步：获取指定用户URL下的所有动态URL"""
    # *** 修改点 1: 函数的参数名和打印信息变更 ***
    print(f"\n[Step 1] 正在为地址 {user_url} 获取所有动态地址...")
    
    # *** 修改点 2: 直接使用传入的完整URL，不再拼接 ***
    command = ['gallery-dl', '-j', user_url]
    if cookie_file:
        command.extend(['--cookies', cookie_file])
        
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        data = json.loads(result.stdout)
        post_urls = [item[1] for item in data if len(item) > 1]
        print(f"找到 {len(post_urls)} 条动态。")
        return post_urls
    except subprocess.CalledProcessError as e:
        print(f"执行命令失败: {e}")
        print(f"请确保 'gallery-dl' 已安装并在系统PATH中。错误输出: {e.stderr}")
        return []
    except (json.JSONDecodeError, IndexError) as e:
        print(f"解析JSON或提取URL时出错: {e}")
        return []
    except FileNotFoundError:
        print("错误: 'gallery-dl' 命令未找到。请确保您已经安装了 gallery-dl 并且它在您的系统PATH中。")
        return []


def process_and_download(post_url: str, output_dir: str, cookie_file: str = None):
    """第二步：处理单个动态URL，提取信息、下载图片并保存元数据"""
    print(f"\n[Step 2] 正在处理动态: {post_url}")
    
    command = ['gallery-dl', '-j', post_url]
    if cookie_file:
        command.extend(['--cookies', cookie_file])

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        images_data = json.loads(result.stdout)

        for image_info_list in images_data:
            if not image_info_list or not isinstance(image_info_list[-1], dict):
                continue
            
            metadata = image_info_list[-1]
            
            detail = metadata.get('detail', {})
            id_str = detail.get('id_str')
            modules = detail.get('modules', {})
            module_author = modules.get('module_author', {})
            pub_ts = module_author.get('pub_ts')
            image_url = metadata.get('url')

            if not all([id_str, pub_ts, image_url]):
                print(f"  - 警告: 缺少关键信息 (id, pub_ts, or url)，跳过此图片。")
                continue
            
            try:
                human_readable_date = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                print(f"  - 警告: 无效的时间戳 '{pub_ts}'，将使用 'unknown_date'。")
                human_readable_date = 'unknown_date'
            
            file_extension = os.path.splitext(image_url)[1] or '.jpg'
            base_filename = f"{human_readable_date}_{pub_ts}_{id_str}"
            image_filename = f"{base_filename}{file_extension}"
            filepath = os.path.join(output_dir, image_filename)

            if os.path.exists(filepath):
                print(f"  - 文件已存在: {image_filename}，跳过。")
                continue

            print(f"  - 正在下载图片: {image_url}")
            print(f"  - 保存为: {image_filename}")
            try:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                print(f"  - 下载失败: {e}")
                continue

            metadata_dir = os.path.join(output_dir, 'metadata')
            os.makedirs(metadata_dir, exist_ok=True)
            metadata_filename = f"{base_filename}.json"
            metadata_filepath = os.path.join(metadata_dir, metadata_filename)
            
            print(f"  - 正在保存元数据到: {metadata_filename}")
            try:
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"  - 保存元数据失败: {e}")

    except Exception as e:
        print(f"处理动态 {post_url} 时发生未知错误: {e}")


def main():
    """主函数，负责启动程序"""
    
    output_dir = OUTPUT_DIR_PATH
    cookie_file = COOKIE_FILE_PATH
    input_file = USER_INPUT_FILE_PATH
    
    if cookie_file and not os.path.exists(cookie_file):
        print(f"警告: 指定的Cookie文件未找到: {cookie_file}")
        print("程序将继续尝试运行，但可能会遇到速率限制。")

    print(f"将从文件 '{input_file}' 读取用户URL列表...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # *** 修改点 3: 变量名变更，现在读取的是URL列表 ***
            user_urls_to_process = [line.strip() for line in f if line.strip()]
        if not user_urls_to_process:
            print(f"错误: 输入文件 '{input_file}' 为空或不包含任何有效的URL。")
            sys.exit(1)
    except FileNotFoundError:
        print(f"错误: 输入文件未找到: {input_file}")
        sys.exit(1)
    
    print(f"将要处理的URL: {user_urls_to_process}")

    os.makedirs(output_dir, exist_ok=True)
    print(f"图片将保存到 '{os.path.abspath(output_dir)}' 文件夹中。")
    print("提示: 您可以随时按 Ctrl + C 中止程序。")

    try:
        # *** 修改点 4: 循环遍历URL列表 ***
        for user_url in user_urls_to_process:
            post_urls = get_all_post_urls(user_url, cookie_file)
            for url in post_urls:
                process_and_download(url, output_dir, cookie_file)
    except KeyboardInterrupt:
        print("\n\n程序已被用户中止。正在退出...")
        sys.exit(0)
            
    print("\n所有任务已完成！")

if __name__ == '__main__':
    main()