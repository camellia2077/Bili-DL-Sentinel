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
# 2. Functional Logic (Extracted Functions)
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

def process_user(user_id, user_folder_name):
    """
    Handles the download task for a single user.
    This includes pre-scanning, launching the download, real-time monitoring,
    interruption, timing, and result statistics.
    Returns a dictionary containing the processing result.
    """
    print(f"\n{'='*50}")
    print(f"[*] Processing User ID: {user_id} (Folder: {user_folder_name})")
    print(f"{'='*50}")

    user_specific_path = os.path.join(CONFIG["download_dir"], "bilibili", user_folder_name)

    # Pre-scan for existing files
    pre_existing_files = set()
    if os.path.isdir(user_specific_path):
        print(f"[*] Scanning for existing files in '{user_specific_path}'...")
        try:
            pre_existing_files = {
                f for f in os.listdir(user_specific_path)
                if os.path.isfile(os.path.join(user_specific_path, f))
            }
            print(f"  [DONE] Found {len(pre_existing_files)} existing files.")
        except OSError as e:
            print(f"  [WARNING] Could not scan directory: {e}")
    else:
        print(f"[*] Directory '{user_specific_path}' not found, assuming no existing files.")

    print("\n[*] Starting download and monitoring process...")
    user_url = f"https://space.bilibili.com/{user_id}/article"
    download_command = ["gallery-dl", "--cookies", CONFIG["cookies_path"], "-d", CONFIG["download_dir"], user_url]
    
    new_files_count = 0
    start_time = time.monotonic()
    
    try:
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
        
        duration = time.monotonic() - start_time
        print(f"\n[*] User {user_id} processed in {duration:.2f} seconds.")
        
        return {
            "user_id": user_id,
            "status": "success",
            "new_files": new_files_count,
            "duration_seconds": round(duration, 2)
        }

    except Exception as e:
        duration = time.monotonic() - start_time
        print(f"[FATAL ERROR] An unexpected error occurred while processing user {user_id}: {e}")
        return {
            "user_id": user_id,
            "status": "error",
            "new_files": new_files_count,
            "duration_seconds": round(duration, 2),
            "error_message": str(e)
        }

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
        base_filename = f"dl_summary_{timestamp}.json"  # Using .json extension is recommended
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