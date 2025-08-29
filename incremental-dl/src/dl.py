# dl.py

import subprocess
import os
import sys
import locale
import pathlib
import datetime
import time
import json

# From a separate file, import the user map
from user_map import user_map

# ==============================================================================
# 1. Configuration (Centralized Management)
# ==============================================================================
CONFIG = {
    "cookies_path": r"C:\Base1\bili\gallery-dl\space.bilibili.com_cookies.txt",
    "download_dir": r"C:\Base1\bili\gallery-dl",
    "summary_dir": "download_summary"
}

# ==============================================================================
# 2. Functional Logic (Refactored Functions)
# ==============================================================================

def check_gallery_dl_availability():
    """Checks if the gallery-dl command is available, exiting if not."""
    try:
        print("[*] Checking for gallery-dl environment...")
        subprocess.run(
            ["gallery-dl", "--version"],
            check=True,
            capture_output=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
        print("  [SUCCESS] gallery-dl found.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] 'gallery-dl' command not found or executable. Please ensure it is correctly installed and in your system's PATH.")
        sys.exit(1)

def scan_existing_files(directory_path):
    """
    Scans a given directory for files and returns a set of their names.
    """
    print(f"[*] Scanning for existing files in '{directory_path}'...")
    if not os.path.isdir(directory_path):
        print(f"[*] Directory not found, assuming no existing files.")
        return set()
    
    try:
        files = {
            f for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f))
        }
        print(f"  [DONE] Found {len(files)} existing files.")
        return files
    except OSError as e:
        print(f"  [WARNING] Could not scan directory: {e}")
        return set()

def execute_and_monitor_download(download_command, pre_existing_files, user_id):
    """
    Launches gallery-dl, monitors its output in real-time, and terminates
    when an existing file is found. Returns the count of new files downloaded.
    """
    new_files_count = 0
    process = subprocess.Popen(
        download_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors='replace',
        bufsize=1,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    )

    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
        
        print(f"[gallery-dl]: {cleaned_line}")
        
        path_to_check = cleaned_line
        if path_to_check.startswith('# '):
            path_to_check = path_to_check[2:]

        if os.path.isabs(path_to_check):
            current_filename = os.path.basename(path_to_check)
            if current_filename in pre_existing_files:
                print(f"\n  [MATCH] File '{current_filename}' found in pre-scan list.")
                print(f"[*] Terminating task for user {user_id} and moving to the next.")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                break
            else:
                new_files_count += 1
    process.wait()
    return new_files_count

def process_user(user_id, user_folder_name):
    """
    Orchestrates the entire download process for a single user by calling
    helper functions for scanning and execution.
    """
    print(f"\n{'='*50}")
    print(f"[*] Processing User ID: {user_id} (Folder: {user_folder_name})")
    print(f"{'='*50}")

    user_specific_path = os.path.join(CONFIG["download_dir"], "bilibili", user_folder_name)
    pre_existing_files = scan_existing_files(user_specific_path)

    print("\n[*] Starting download and monitoring process...")
    user_url = f"https://space.bilibili.com/{user_id}/article"
    download_command = ["gallery-dl", "--cookies", CONFIG["cookies_path"], "-d", CONFIG["download_dir"], user_url]
    
    start_time = time.monotonic()
    new_files_count = 0
    status = "success"
    error_message = None

    try:
        new_files_count = execute_and_monitor_download(download_command, pre_existing_files, user_id)
    except Exception as e:
        status = "error"
        error_message = str(e)
        print(f"[FATAL ERROR] An unexpected error occurred while processing user {user_id}: {e}")

    duration = time.monotonic() - start_time
    print(f"\n[*] User {user_id} processed in {duration:.2f} seconds.")
    
    result = {
        "user_id": user_id,
        "status": status,
        "new_files": new_files_count,
        "duration_seconds": round(duration, 2)
    }
    if error_message:
        result["error_message"] = error_message
    
    return result

def generate_report(stats):
    """Generates and prints a console summary, then writes a JSON report to a file."""
    print(f"\n{'='*60}")
    print(f"{' '*22}Download Task Summary")
    print(f"{'='*60}")

    # 1. Print a human-readable summary to the console
    total_downloads = 0
    for user_folder, data in stats.items():
        if data['status'] == 'success':
            print(f"User [{user_folder}]: Downloaded {data['new_files']} new files in {data['duration_seconds']:.2f}s.")
            total_downloads += data['new_files']
        else:
            print(f"User [{user_folder}]: Failed. Error: {data.get('error_message', 'Unknown')}")
    print(f"\nTotal new files downloaded across all users: {total_downloads}.")
    print(f"{'='*60}")
    
    # 2. Prepare machine-readable JSON data
    final_report_data = {
        "report_generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_new_files": total_downloads,
        "user_stats": stats
    }
    summary_content_json = json.dumps(final_report_data, indent=4, ensure_ascii=False)

    # 3. Write the JSON report to a file
    try:
        os.makedirs(CONFIG["summary_dir"], exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
        base_filename = f"dl_summary_{timestamp}.json"
        full_filepath = os.path.join(CONFIG["summary_dir"], base_filename)

        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(summary_content_json)
        print(f"\n[+] JSON report saved successfully to: {full_filepath}")

    except (IOError, OSError) as e:
        print(f"\n[!] ERROR: Could not write the report file: {e}")

# ==============================================================================
# 3. Main Program Entry Point
# ==============================================================================

def main():
    """
    Main function to orchestrate the download process.
    """
    check_gallery_dl_availability()
    
    download_stats = {}
    
    for user_id, user_folder_name in user_map.items():
        result = process_user(user_id, user_folder_name)
        download_stats[user_folder_name] = result
        
    if download_stats:
        generate_report(download_stats)
    else:
        print("\n[*] No users were processed.")
    
    print("\n[*] All tasks have been completed.")

if __name__ == "__main__":
    main()