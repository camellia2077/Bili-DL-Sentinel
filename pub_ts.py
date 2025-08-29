import subprocess
import json
import requests
import os
import sys
import datetime
import re

# --- 全局配置区 ---
COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl/bilibili_images"
USER_INPUT_FILE_PATH = "C:/Base1/bili/gallery-dl/users.txt"


def get_all_post_urls(user_url: str, cookie_file: str = None, user_folder: str = None) -> list:
    """第一步：获取并保存指定用户URL下的所有动态的元数据，然后返回动态URL列表"""
    print(f"\n[Step 1] 正在为地址 {user_url} 获取所有动态地址...")
    
    command = ['gallery-dl', '-j', user_url]
    if cookie_file:
        command.extend(['--cookies', cookie_file])
        
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        data = json.loads(result.stdout)
        
        if user_folder:
            step1_metadata_dir = os.path.join(user_folder, 'metadata', 'step1')
            os.makedirs(step1_metadata_dir, exist_ok=True)
            safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', user_url.replace("https://", "").replace("http://", "")) + ".json"
            metadata_filepath = os.path.join(step1_metadata_dir, safe_filename)
            
            print(f"  - 正在保存Step 1的元数据到: {os.path.join(os.path.basename(user_folder), 'metadata', 'step1', safe_filename)}")
            try:
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"  - 保存Step 1元数据失败: {e}")

        post_urls = [item[1] for item in data if len(item) > 1]
        print(f"找到 {len(post_urls)} 条动态。")
        return post_urls
    except Exception as e:
        print(f"获取动态列表时发生错误: {e}")
        return []


def process_and_download(post_url: str, user_folder: str, cookie_file: str = None):
    """第二步：处理单个动态URL，提取信息、下载图片并保存元数据"""
    print(f"\n[Step 2] 正在处理动态: {post_url}")
    
    command = ['gallery-dl', '-j', post_url]
    if cookie_file:
        command.extend(['--cookies', cookie_file])

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        images_data = json.loads(result.stdout)

        # 如果此动态没有有效数据，则直接跳过
        if not images_data or not images_data[0] or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告: 动态 {post_url} 中未找到有效的图片数据，跳过。")
            return

        # --- 新的、统一的元数据保存逻辑 ---
        # 提取第一个图片的元数据作为代表，以获取动态的公共信息 (id, pub_ts)
        first_image_metadata = images_data[0][-1]
        detail = first_image_metadata.get('detail', {})
        id_str = detail.get('id_str')
        module_author = detail.get('modules', {}).get('module_author', {})
        pub_ts = module_author.get('pub_ts')

        if id_str and pub_ts:
            try:
                human_readable_date = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                human_readable_date = 'unknown_date'
            
            # 为整个动态创建一个元数据文件名（不带图片索引）
            metadata_base_filename = f"{human_readable_date}_{pub_ts}_{id_str}"
            metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata_filename = f"{metadata_base_filename}.json"
            metadata_filepath = os.path.join(metadata_dir, metadata_filename)

            # 检查元数据文件是否已存在，如果存在则不重复保存
            if not os.path.exists(metadata_filepath):
                print(f"  - 正在保存Step 2元数据到: {os.path.join(os.path.basename(user_folder), 'metadata', 'step2', metadata_filename)}")
                try:
                    # 将整个动态的所有图片信息 (images_data) 保存到一个JSON文件中
                    with open(metadata_filepath, 'w', encoding='utf-8') as f:
                        json.dump(images_data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"  - 保存元数据失败: {e}")
            else:
                print(f"  - 元数据文件已存在: {metadata_filename}，跳过保存。")
        else:
            print(f"  - 警告: 缺少 id_str 或 pub_ts，无法保存此动态的元数据。")

        # --- 图片下载循环（保持不变，但移除了内部的元数据保存）---
        for index, image_info_list in enumerate(images_data):
            if not image_info_list or not isinstance(image_info_list[-1], dict):
                continue
            
            metadata = image_info_list[-1]
            image_url = metadata.get('url')
            
            # 从元数据中重新获取id和ts以确保文件名正确
            detail = metadata.get('detail', {})
            id_str = detail.get('id_str')
            modules = detail.get('modules', {})
            module_author = modules.get('module_author', {})
            pub_ts = module_author.get('pub_ts')

            if not all([id_str, pub_ts, image_url]):
                # print(f"  - 警告: 缺少关键信息 (id, pub_ts, or url)，跳过此图片。")
                continue
            
            try:
                human_readable_date = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                human_readable_date = 'unknown_date'
            
            file_extension = os.path.splitext(image_url)[1] or '.jpg'
            # 图片文件名仍然使用索引来区分
            base_filename = f"{human_readable_date}_{pub_ts}_{id_str}_{index}"
            image_filename = f"{base_filename}{file_extension}"
            filepath = os.path.join(user_folder, image_filename)

            if os.path.exists(filepath):
                print(f"  - 文件已存在: {image_filename}，跳过。")
                continue

            print(f"  - 正在下载图片: {image_url}")
            print(f"  - 保存到: {os.path.join(os.path.basename(user_folder), image_filename)}")
            try:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                print(f"  - 下载失败: {e}")
                continue
            
            # 此处原有的元数据保存代码块已被移除

    except Exception as e:
        print(f"处理动态 {post_url} 时发生未知错误: {e}")


def main():
    """主函数，负责启动程序"""
    
    base_output_dir = OUTPUT_DIR_PATH
    cookie_file = COOKIE_FILE_PATH
    input_file = USER_INPUT_FILE_PATH
    
    if cookie_file and not os.path.exists(cookie_file):
        print(f"警告: 指定的Cookie文件未找到: {cookie_file}")
    
    print(f"将从文件 '{input_file}' 读取用户URL列表...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            user_urls_to_process = [line.strip() for line in f if line.strip()]
        if not user_urls_to_process:
            print(f"错误: 输入文件 '{input_file}' 为空或不包含任何有效的URL。")
            sys.exit(1)
    except FileNotFoundError:
        print(f"错误: 输入文件未找到: {input_file}")
        sys.exit(1)
    
    print(f"将要处理的URL: {user_urls_to_process}")
    os.makedirs(base_output_dir, exist_ok=True)
    print(f"所有文件将保存在基础目录 '{os.path.abspath(base_output_dir)}' 下。")
    print("提示: 您可以随时按 Ctrl + C 中止程序。")

    try:
        for user_url in user_urls_to_process:
            # --- 核心修改：为每个用户确定并创建其专属文件夹 ---
            
            # 1. 尝试从Step 1的第一个post URL中获取用户名 (试探性)
            # 这是一个优化，避免在主循环中重复获取用户名
            temp_command = ['gallery-dl', '-j', '-g', user_url]
            if cookie_file: temp_command.extend(['--cookies', cookie_file])
            
            first_post_url = None
            try:
                result = subprocess.run(temp_command, check=True, capture_output=True, text=True, encoding='utf-8')
                first_post_url = result.stdout.strip().split('\n')[0]
            except Exception:
                print(f"无法为 {user_url} 获取帖子列表，跳过该用户。")
                continue

            username = None
            if first_post_url:
                try:
                    meta_command = ['gallery-dl', '-j', first_post_url]
                    if cookie_file: meta_command.extend(['--cookies', cookie_file])
                    meta_result = subprocess.run(meta_command, check=True, capture_output=True, text=True, encoding='utf-8')
                    metadata = json.loads(meta_result.stdout)[0][-1]
                    username = metadata.get('username')
                    if not username:
                         username = metadata.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')
                except Exception:
                    pass # 获取失败，后面会使用UID作为备用
            
            # 2. 确定文件夹名
            folder_name = username
            if not folder_name:
                # 备用方案：从用户URL中提取UID
                match = re.search(r'space.bilibili.com/(\d+)', user_url)
                if match:
                    folder_name = match.group(1)
                else:
                    folder_name = re.sub(r'[^a-zA-Z0-9_-]', '_', user_url) # 最坏的情况
            
            # 清理文件名，防止特殊字符导致路径问题
            folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
            
            user_folder = os.path.join(base_output_dir, folder_name)
            os.makedirs(user_folder, exist_ok=True)
            print(f"\n>>>>>>>>> 开始处理用户: {folder_name} <<<<<<<<<")
            print(f"文件将保存到: {user_folder}")

            # 3. 开始处理该用户的帖子
            post_urls = get_all_post_urls(user_url, cookie_file, user_folder)
            for url in post_urls:
                process_and_download(url, user_folder, cookie_file)

    except KeyboardInterrupt:
        print("\n\n程序已被用户中止。正在退出...")
        sys.exit(0)
            
    print("\n所有任务已完成！")

if __name__ == '__main__':
    main()
