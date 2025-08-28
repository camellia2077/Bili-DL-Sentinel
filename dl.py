import subprocess
import os
import sys
import locale
import pathlib
import datetime  # 新增: 用于生成时间戳

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
    # 新增: 用于存储每个用户的下载统计结果
    download_stats = {}

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

        user_specific_path = os.path.join(download_dir, "bilibili", user_folder_name)

        pre_existing_files = set()
        if os.path.isdir(user_specific_path):
            print(f"[*] 正在扫描目录 '{user_specific_path}' 中的现有文件...")
            pre_existing_files = {f for f in os.listdir(user_specific_path) if os.path.isfile(os.path.join(user_specific_path, f))}
            print(f"  [完成] 发现 {len(pre_existing_files)} 个已存在的文件。")
        else:
            print(f"[*] 目录 '{user_specific_path}' 不存在，视为没有已存在的文件。")

        print("\n[*] 开始正式下载并监控...")
        user_url = f"https://space.bilibili.com/{user_id}/article"
        download_command = ["gallery-dl", "--cookies", cookies_path, "-d", download_dir, user_url]
        
        # 新增: 初始化当前用户的新增文件计数器
        new_files_count = 0
        
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
                    else:
                        # 新增: 如果文件不在预扫描清单中，说明是新文件，计数器加一
                        new_files_count += 1
            process.wait()
            print(f"\n[*] 用户 {user_id} 处理完成。")
            
            # 新增: 记录当前用户的下载统计
            download_stats[user_folder_name] = new_files_count # 使用文件夹名作为键，更直观

        except Exception as e:
            print(f"[严重错误] 处理用户 {user_id} 时发生意外错误: {e}")
            download_stats[user_folder_name] = f"处理时发生错误: {e}"
            continue

    # --- 新增: 所有用户处理完毕后，生成并输出统计报告 ---
    print(f"\n{'='*60}")
    print(f"{' '*22}下载任务统计总结")
    print(f"{'='*60}")

    # 1. 准备报告内容
    total_downloads = 0
    summary_lines = []
    
    # 添加报告头和时间
    report_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary_lines.append(f"下载统计报告 ({report_time})")
    summary_lines.append("="*40)

    for user_folder, count in download_stats.items():
        if isinstance(count, int):
            line = f"用户 [{user_folder}]: 新增 {count} 个文件。"
            summary_lines.append(line)
            total_downloads += count
        else: # 如果是错误信息
            line = f"用户 [{user_folder}]: {count}"
            summary_lines.append(line)
    
    summary_lines.append("="*40)
    summary_lines.append(f"所有用户总计新增: {total_downloads} 个文件。")
    
    summary_content = "\n".join(summary_lines)

    # 2. 在控制台打印报告
    print(summary_content)
    print(f"{'='*60}")

    # --- V V V 这里是修改部分 V V V ---

    # 3. 生成文件名并写入TXT文件
    summary_dir = "download_summary"  # 定义文件夹名称
    
    try:
        # 确保报告文件夹存在，如果不存在则创建
        os.makedirs(summary_dir, exist_ok=True)

        # 准备文件名和完整路径
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
        base_filename = f"dl_{timestamp}.txt"
        full_filepath = os.path.join(summary_dir, base_filename)

        # 将报告内容写入文件
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        print(f"\n[+] 统计结果已成功保存至文件: {full_filepath}")

    except (IOError, OSError) as e:
        print(f"\n[!] 错误：无法将统计结果写入文件: {e}")

    # --- ^ ^ ^ 修改结束 ^ ^ ^ ---

if __name__ == "__main__":
    main()