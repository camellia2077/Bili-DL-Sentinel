import subprocess
import os
import sys
import locale
import pathlib
import datetime
import time  # 新增: 用于精确计时
import json  # 新增: 用于生成JSON格式的报告

from user_map import user_map

# ==============================================================================
# 1. 初始化与配置
# ==============================================================================
cookies_path = r"C:\Base1\bili\gallery-dl\space.bilibili.com_cookies.txt"
# 这是总的下载根目录
download_dir = r"C:\Base1\bili\gallery-dl"



# ==============================================================================
# 程序主逻辑
# ==============================================================================

def main():
    """
    主函数，执行自动化下载流程
    """
    # 修改: 用于存储每个用户更详细的下载统计结果
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
        
        new_files_count = 0
        start_time = time.monotonic() # 新增: 记录开始时间
        
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
                        new_files_count += 1
            process.wait()
            
            end_time = time.monotonic() # 新增: 记录结束时间
            duration = end_time - start_time
            print(f"\n[*] 用户 {user_id} 处理完成，耗时: {duration:.2f} 秒。")
            
            # 修改: 记录当前用户更详细的下载统计
            download_stats[user_folder_name] = {
                "user_id": user_id,
                "status": "success",
                "new_files": new_files_count,
                "duration_seconds": round(duration, 2)
            }

        except Exception as e:
            end_time = time.monotonic()
            duration = end_time - start_time
            print(f"[严重错误] 处理用户 {user_id} 时发生意外错误: {e}")
            # 修改: 记录包含错误信息的统计
            download_stats[user_folder_name] = {
                "user_id": user_id,
                "status": "error",
                "new_files": new_files_count, # 记录出错前已下载的数量
                "duration_seconds": round(duration, 2),
                "error_message": str(e)
            }
            continue

    # --- 修改: 所有用户处理完毕后，生成并输出统计报告 ---
    print(f"\n{'='*60}")
    print(f"{' '*22}下载任务统计总结")
    print(f"{'='*60}")

    # 1. 在控制台打印一份人类可读的总结
    total_downloads = 0
    for user_folder, data in download_stats.items():
        if data['status'] == 'success':
            print(f"用户 [{user_folder}]: 新增 {data['new_files']} 个文件, 耗时 {data['duration_seconds']:.2f} 秒。")
            total_downloads += data['new_files']
        else:
            print(f"用户 [{user_folder}]: 处理失败。错误: {data.get('error_message', '未知')}")
    print(f"\n所有用户总计新增: {total_downloads} 个文件。")
    print(f"{'='*60}")
    
    # 2. 准备用于文件输出的、机器可读的JSON数据
    final_report_data = {
        "report_generated_at_utc": datetime.datetime.utcnow().isoformat(), # 使用ISO 8601标准格式和UTC时间
        "total_new_files": total_downloads,
        "user_stats": download_stats
    }
    # ensure_ascii=False 确保中文字符能正确写入, indent=4 使JSON文件格式化，易于查看
    summary_content_json = json.dumps(final_report_data, indent=4, ensure_ascii=False)

    # 3. 生成文件名并写入JSON数据到TXT文件
    summary_dir = "download_summary"
    try:
        os.makedirs(summary_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
        base_filename = f"dl_summary_{timestamp}.json"
        full_filepath = os.path.join(summary_dir, base_filename)

        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(summary_content_json)
        print(f"\n[+] 统计报告 (JSON格式) 已成功保存至文件: {full_filepath}")

    except (IOError, OSError) as e:
        print(f"\n[!] 错误：无法将统计结果写入文件: {e}")

if __name__ == "__main__":
    main()