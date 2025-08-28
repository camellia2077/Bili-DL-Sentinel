import subprocess
import os
import sys
import locale
import pathlib

# ==============================================================================
# 1. 初始化与配置
# ==============================================================================
cookies_path = r"C:\Base1\bili\gallery-dl\space.bilibili.com_cookies.txt"
# 这是总的下载根目录
download_dir = r"C:\Base1\bili\gallery-dl"

# --- V V V 请在这里填写您的映射表 V V V ---
# 这是最关键的一步：请将您的用户ID和对应的文件夹名称一一对应地填入。
# 格式： "用户ID": "该用户在bilibili文件夹下的子文件夹名",
user_map = {
    #"": "坂坂白",
    "10982073": "明前奶粉罐",
}
# --- ^ ^ ^ 映射表填写结束 ^ ^ ^ ---

# ==============================================================================
# 程序主逻辑
# ==============================================================================

def main():
    """
    主函数，执行自动化下载流程
    """
    try:
        subprocess.run(["gallery-dl", "--version"], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[错误] 'gallery-dl' 命令未找到或无法执行。")
        sys.exit(1)
    
    # 遍历您定义的映射表
    for user_id, user_folder_name in user_map.items():
        print(f"\n{'='*50}")
        print(f"[*] 开始处理用户 ID: {user_id} (文件夹: {user_folder_name})")
        print(f"{'='*50}")

        # 根据映射信息，直接构建出准确的用户文件夹路径
        # 注意：这里假设了 gallery-dl 的默认结构 'bilibili/用户名'
        user_specific_path = os.path.join(download_dir, "bilibili", user_folder_name)

        # --- 步骤 1: 直接扫描准确的路径，建立文件清单 ---
        pre_existing_files = set()
        if os.path.isdir(user_specific_path):
            print(f"[*] 正在扫描目录 '{user_specific_path}' 中的现有文件...")
            pre_existing_files = {f for f in os.listdir(user_specific_path) if os.path.isfile(os.path.join(user_specific_path, f))}
            print(f"  [完成] 发现 {len(pre_existing_files)} 个已存在的文件。")
        else:
            print(f"[*] 目录 '{user_specific_path}' 不存在，视为没有已存在的文件。")

        # --- 步骤 2: 正式下载并实时监控 ---
        print("\n[*] 开始正式下载并监控...")
        user_url = f"https://space.bilibili.com/{user_id}/article"
        download_command = ["gallery-dl", "--cookies", cookies_path, "-d", download_dir, user_url]
        
        try:
            process = subprocess.Popen(
                download_command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding=locale.getpreferredencoding(False), errors='replace',
                bufsize=1, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )

            for line in iter(process.stdout.readline, ''):
                if not line: break
                
                cleaned_line = line.strip()
                if not cleaned_line: continue
                
                print(f"[gallery-dl]: {cleaned_line}")
                
                path_to_check = cleaned_line
                if path_to_check.startswith('# '):
                    path_to_check = path_to_check[2:]

                if os.path.isabs(path_to_check):
                    current_filename = os.path.basename(path_to_check)
                    if current_filename in pre_existing_files:
                        print(f"\n  [命中] 文件 '{current_filename}' 在预扫描清单中已存在。")
                        print(f"[*] 终止用户 {user_id} 的下载任务，处理下一个用户。")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break
            process.wait()
            print(f"\n[*] 用户 {user_id} 处理完成。")

        except Exception as e:
            print(f"[严重错误] 处理用户 {user_id} 时发生意外错误: {e}")
            continue

    print(f"\n{'='*50}")
    print("[*] 所有用户 ID 已处理完毕。")

if __name__ == "__main__":
    main()