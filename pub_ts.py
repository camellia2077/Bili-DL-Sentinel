# pub_ts.py (Corrected folder naming logic)
import subprocess
import json
import requests
import os
import sys
import datetime
import re
import sqlite3
from typing import List, Dict, Any, Optional

# ==============================================================================
# 1. CONFIGURATION CLASS
# ==============================================================================
class Config:
    """A dedicated class for holding all application configurations."""
    COOKIE_FILE_PATH = "C:/Base1/bili/gallery-dl/space.bilibili.com_cookies.txt"
    OUTPUT_DIR_PATH = "C:/Base1/bili/gallery-dl/bilibili_images"
    USER_INPUT_FILE_PATH = "C:/Base1/bili/gallery-dl/users.txt"
    ARCHIVE_DB_NAME = "archive.sqlite"

# ==============================================================================
# 2. DATABASE ABSTRACTION LAYER
# ==============================================================================
class ArchiveDB:
    """Manages all interactions with the SQLite archive database."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        try:
            # The directory is created by the Application class before this is called
            self.conn = sqlite3.connect(self.db_path)
            self._create_table()
        except sqlite3.Error as e:
            print(f"FATAL: Could not connect to database {self.db_path}: {e}")
            raise

    def _create_table(self):
        """Creates the archive table if it doesn't exist."""
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS archive (entry TEXT PRIMARY KEY) WITHOUT ROWID")

    def exists(self, entry: str) -> bool:
        """Checks if an entry exists in the archive."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM archive WHERE entry = ?", (entry,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"  - Warning: Could not query archive database: {e}")
            return False

    def add(self, entry: str):
        """Adds a new entry to the archive."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO archive (entry) VALUES (?)", (entry,))
            print(f"  - Added to archive: {entry}")
        except sqlite3.Error as e:
            print(f"  - Warning: Failed to add '{entry}' to archive: {e}")

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print("\nClosing archive database connection.")

# ==============================================================================
# 3. API WRAPPER
# ==============================================================================
class BilibiliAPI:
    """A wrapper for interacting with Bilibili via the gallery-dl tool."""
    def __init__(self, cookie_file: Optional[str]):
        self.cookie_file = cookie_file

    def _run_command(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """A centralized helper to run gallery-dl and parse JSON output."""
        command = ['gallery-dl', '-j', url]
        if self.cookie_file:
            command.extend(['--cookies', self.cookie_file])
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"  - Error: gallery-dl failed for {url}. Stderr: {e.stderr.strip()}")
        except json.JSONDecodeError:
            print(f"  - Error: Failed to parse JSON from gallery-dl for {url}.")
        except Exception as e:
            print(f"  - Error: An unexpected error occurred while running gallery-dl: {e}")
        return None
    
    def get_post_metadata(self, post_url: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches detailed metadata for a single post."""
        return self._run_command(post_url)

    def get_initial_metadata(self, user_url: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches the initial metadata dump for a user page."""
        return self._run_command(user_url)

# ==============================================================================
# 4. CORE BUSINESS LOGIC / PROCESSOR
# ==============================================================================
class PostProcessor:
    """Handles the business logic of processing posts and downloading files."""
    def __init__(self, base_output_dir: str, api: BilibiliAPI, db: ArchiveDB):
        self.base_output_dir = base_output_dir
        self.api = api
        self.db = db

    def _determine_folder_name(self, user_url: str, user_page_data: Optional[List[Dict]], post_urls: List[str]) -> str:
        """
        Determines the appropriate folder name by checking Step 1 and Step 2 metadata.
        """
        username = None
        # Attempt 1: Check the summary metadata from the user page (Step 1)
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            first_post_summary = user_page_data[0][-1]
            username = first_post_summary.get('username')

        # Attempt 2: If no username, fetch detailed metadata for the first post (Step 2)
        if not username and post_urls:
            print("  - Username not in summary, checking first post for details...")
            first_post_url = post_urls[0]
            detailed_metadata = self.api.get_post_metadata(first_post_url)
            if detailed_metadata:
                first_post_detail = detailed_metadata[0][-1]
                username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')

        if username:
            # Sanitize username for folder name
            return re.sub(r'[\\/*?:"<>|]', "", username).strip()

        # Fallback: Use the user's numeric ID
        match = re.search(r'space.bilibili.com/(\d+)', user_url)
        return match.group(1) if match else re.sub(r'[^a-zA-Z0-9_-]', '_', user_url)

    def process_user(self, user_url: str):
        """Main processing logic for a single user."""
        print(f"\n>>>>>>>>> Starting process for user: {user_url} <<<<<<<<<")

        # Fetch initial data and post URLs first
        print("\n[Step 1] Fetching all post URLs...")
        user_page_data = self.api.get_initial_metadata(user_url)

        if not user_page_data:
            print("  - No data received. Skipping user.")
            return

        post_urls = [item[1] for item in user_page_data if len(item) > 1]
        total_posts = len(post_urls) # Get total number of posts
        print(f"Found {total_posts} posts.")

        # Now, determine the folder name *before* creating directories or saving files
        folder_name = self._determine_folder_name(user_url, user_page_data, post_urls)
        user_folder = os.path.join(self.base_output_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        print(f"User identified as: '{folder_name}'")
        print(f"Files will be saved to: {user_folder}")

        # Save Step 1 metadata
        metadata_dir = os.path.join(user_folder, 'metadata', 'step1')
        os.makedirs(metadata_dir, exist_ok=True)
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', user_url.replace("https://", "").replace("http://", "")) + ".json"
        metadata_filepath = os.path.join(metadata_dir, safe_filename)
        
        print(f"  - Saving Step 1 metadata to: {os.path.join(os.path.basename(user_folder), 'metadata', 'step1', safe_filename)}")
        try:
            with open(metadata_filepath, 'w', encoding='utf-8') as f:
                json.dump(user_page_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  - Warning: Failed to save Step 1 metadata: {e}")

        # --- MODIFICATION START ---
        # Loop through posts with an index for progress tracking
        for index, url in enumerate(post_urls):
            self._process_single_post(url, user_folder, index + 1, total_posts)
        # --- MODIFICATION END ---

    # --- MODIFICATION START ---
    # Update the function signature to accept progress numbers
    def _process_single_post(self, post_url: str, user_folder: str, current_post_num: int, total_posts: int):
        """Processes a single post: fetches metadata, downloads images, and updates archive."""
        # Update the print statement to show progress
        print(f"\n[Step 2] Processing post [{current_post_num}/{total_posts}]: {post_url}")
    # --- MODIFICATION END ---
        
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - Warning: No valid data found for post {post_url}. Skipping.")
            return

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        # Save Step 2 metadata
        if id_str and pub_ts:
            try:
                date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                date_str = 'unknown_date'
            
            metadata_filename = f"{date_str}_{pub_ts}_{id_str}.json"
            metadata_dir = os.path.join(user_folder, 'metadata', 'step2')
            os.makedirs(metadata_dir, exist_ok=True)
            metadata_filepath = os.path.join(metadata_dir, metadata_filename)

            if not os.path.exists(metadata_filepath):
                print(f"  - Saving Step 2 metadata for post {id_str}...")
                try:
                    with open(metadata_filepath, 'w', encoding='utf-8') as f:
                        json.dump(images_data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"  - Warning: Failed to save metadata: {e}")
            else:
                print(f"  - Metadata for post {id_str} already exists. Skipping save.")

        for index, image_info in enumerate(images_data[1:]):
            if not isinstance(image_info[-1], dict): continue

            meta = image_info[-1]
            image_url = meta.get('url')
            
            if not all([id_str, pub_ts, image_url]): continue

            archive_entry = f"bilibili{id_str}_{index + 1}"
            if self.db.exists(archive_entry):
                print(f"  - Found in archive, skipping: {archive_entry}")
                continue

            self._download_image(image_url, user_folder, pub_ts, id_str, index + 1, archive_entry)

    def _download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int, archive_entry: str):
        """Downloads a single image file."""
        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'

        file_ext = os.path.splitext(url)[1] or '.jpg'
        image_filename = f"{date_str}_{pub_ts}_{id_str}_{index}{file_ext}"
        filepath = os.path.join(folder, image_filename)

        if os.path.exists(filepath):
            print(f"  - File already exists, skipping: {image_filename}")
            return
            
        print(f"  - Downloading: {image_filename}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.db.add(archive_entry)
        except requests.exceptions.RequestException as e:
            print(f"  - Download failed: {e}")

# ==============================================================================
# 5. APPLICATION ORCHESTRATOR
# ==============================================================================
class Application:
    """The main application class that orchestrates the entire process."""
    def __init__(self, config: Config):
        self.config = config
        
        # Create the output directory first
        os.makedirs(self.config.OUTPUT_DIR_PATH, exist_ok=True)

        # Now that the directory is guaranteed to exist, initialize the database
        db_path = os.path.join(self.config.OUTPUT_DIR_PATH, self.config.ARCHIVE_DB_NAME)
        self.db = ArchiveDB(db_path)
        
        self.api = BilibiliAPI(self.config.COOKIE_FILE_PATH)
        self.processor = PostProcessor(self.config.OUTPUT_DIR_PATH, self.api, self.db)

    def run(self):
        """The main entry point to start the downloader."""
        print(f"Reading user URLs from '{self.config.USER_INPUT_FILE_PATH}'...")
        try:
            with open(self.config.USER_INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
                user_urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"FATAL: Input file not found: {self.config.USER_INPUT_FILE_PATH}")
            sys.exit(1)
        
        if not user_urls:
            print(f"Error: Input file is empty or has no valid URLs.")
            return

        try:
            for user_url in user_urls:
                self.processor.process_user(user_url)
        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user. Exiting gracefully...")
        finally:
            self.db.close()
        
        print("\nAll tasks completed!")

def main():
    """Main function to instantiate and run the application."""
    app_config = Config()
    app = Application(app_config)
    app.run()

if __name__ == '__main__':
    main()