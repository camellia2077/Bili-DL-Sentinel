import subprocess
import json
import requests
import os
import sys
import datetime
import re
import sqlite3

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


def process_and_download(post_url: str, user_folder: str, cookie_file: str = None, conn: sqlite3.Connection = None):
    """第二步：处理单个动态URL，提取信息、下载图片并保存元数据"""
    print(f"\n[Step 2] 正在处理动态: {post_url}")
    
    command = ['gallery-dl', '-j', post_url]
    if cookie_file:
        command.extend(['--cookies', cookie_file])

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        images_data = json.loads(result.stdout)

        if not images_data or not images_data[0] or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告: 动态 {post_url} 中未找到有效的图片数据，跳过。")
            return

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
            
            metadata_base_filename = f"{human_readable_date}_{pub_ts}_{id_str}"
            metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata_filename = f"{metadata_base_filename}.json"
            metadata_filepath = os.path.join(metadata_dir, metadata_filename)

            if not os.path.exists(metadata_filepath):
                print(f"  - 正在保存Step 2元数据到: {os.path.join(os.path.basename(user_folder), 'metadata', 'step2', metadata_filename)}")
                try:
                    with open(metadata_filepath, 'w', encoding='utf-8') as f:
                        json.dump(images_data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"  - 保存元数据失败: {e}")
            else:
                print(f"  - 元数据文件已存在: {metadata_filename}，跳过保存。")
        else:
            print(f"  - 警告: 缺少 id_str 或 pub_ts，无法保存此动态的元数据。")

        for index, image_info_list in enumerate(images_data):
            if not image_info_list or not isinstance(image_info_list[-1], dict):
                continue
            
            metadata = image_info_list[-1]
            image_url = metadata.get('url')
            
            detail = metadata.get('detail', {})
            id_str = detail.get('id_str')
            modules = detail.get('modules', {})
            module_author = modules.get('module_author', {})
            pub_ts = module_author.get('pub_ts')

            if not all([id_str, pub_ts, image_url]):
                continue
            
            # --- 新增功能：Archive 数据库集成 ---
            # 构建 archive entry key，序号从1开始
            archive_entry = f"bilibili {id_str}_{index + 1}"

            # 1. 检查 archive 数据库
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM archive WHERE entry = ?", (archive_entry,))
                    if cursor.fetchone():
                        print(f"  - 在 archive 数据库中找到记录，跳过: {archive_entry}")
                        continue
                except sqlite3.Error as e:
                    print(f"  - 查询 archive 数据库时出错: {e}")

            try:
                human_readable_date = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                human_readable_date = 'unknown_date'
            
            file_extension = os.path.splitext(image_url)[1] or '.jpg'
            base_filename = f"{human_readable_date}_{pub_ts}_{id_str}_{index + 1}"
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
                
                # 2. 如果下载成功，则将记录添加到 archive 数据库
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO archive (entry) VALUES (?)", (archive_entry,))
                        conn.commit()
                        print(f"  - 已将记录添加到 archive: {archive_entry}")
                    except sqlite3.Error as e:
                        print(f"  - 添加记录到 archive 数据库失败: {e}")

            except requests.exceptions.RequestException as e:
                print(f"  - 下载失败: {e}")
                continue
            
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

    # --- 新增功能：初始化 Archive 数据库 ---
    conn = None
    try:
        archive_db_path = os.path.join(base_output_dir, 'archive.sqlite')
        print(f"使用 archive 数据库: {archive_db_path}")
        conn = sqlite3.connect(archive_db_path)
        cursor = conn.cursor()
        # 创建 archive 表（如果不存在）
        create_table_query = "CREATE TABLE IF NOT EXISTS archive (entry TEXT PRIMARY KEY) WITHOUT ROWID" #
        cursor.execute(create_table_query)
        conn.commit()
    except sqlite3.Error as e:
        print(f"错误: 无法连接或初始化 archive 数据库: {e}")
        sys.exit(1)

    try:
        for user_url in user_urls_to_process:
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
                    pass
            
            folder_name = username
            if not folder_name:
                match = re.search(r'space.bilibili.com/(\d+)', user_url)
                if match:
                    folder_name = match.group(1)
                else:
                    folder_name = re.sub(r'[^a-zA-Z0-9_-]', '_', user_url)
            
            folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
            
            user_folder = os.path.join(base_output_dir, folder_name)
            os.makedirs(user_folder, exist_ok=True)
            print(f"\n>>>>>>>>> 开始处理用户: {folder_name} <<<<<<<<<")
            print(f"文件将保存到: {user_folder}")

            post_urls = get_all_post_urls(user_url, cookie_file, user_folder)
            for url in post_urls:
                # 将数据库连接传递给处理函数
                process_and_download(url, user_folder, cookie_file, conn)

    except KeyboardInterrupt:
        print("\n\n程序已被用户中止。正在退出...")
    finally:
        # --- 新增功能：关闭数据库连接 ---
        if conn:
            print("\n正在关闭 archive 数据库连接...")
            conn.close()
            
    print("\n所有任务已完成！")

if __name__ == '__main__':
    main()