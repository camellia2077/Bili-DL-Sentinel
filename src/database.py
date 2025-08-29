# database.py

import sqlite3
from typing import Optional

class ArchiveDB:
    """管理所有与 SQLite 归档数据库的交互。"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接。
        :param db_path: 数据库文件的完整路径。
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        try:
            # Application 类会提前创建好目录，所以这里直接连接
            self.conn = sqlite3.connect(self.db_path)
            self._create_table()
        except sqlite3.Error as e:
            print(f"致命错误：无法连接到数据库 {self.db_path}: {e}")
            raise

    def _create_table(self):
        """如果归档表不存在，则创建它。"""
        if self.conn:
            with self.conn:
                self.conn.execute("CREATE TABLE IF NOT EXISTS archive (entry TEXT PRIMARY KEY) WITHOUT ROWID")

    def exists(self, entry: str) -> bool:
        """
        检查一个条目是否存在于归档中。
        :param entry: 要检查的条目字符串。
        :return: 如果存在则返回 True，否则返回 False。
        """
        if not self.conn:
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM archive WHERE entry = ?", (entry,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"  - 警告：无法查询归档数据库: {e}")
            return False

    def add(self, entry: str):
        """
        向归档中添加一个新条目。
        :param entry: 要添加的条目字符串。
        """
        if not self.conn:
            return
        try:
            with self.conn:
                self.conn.execute("INSERT INTO archive (entry) VALUES (?)", (entry,))
            print(f"  - 已添加到归档: {entry}")
        except sqlite3.Error as e:
            print(f"  - 警告：添加 '{entry}' 到归档失败: {e}")

    def close(self):
        """关闭数据库连接。"""
        if self.conn:
            self.conn.close()
            print("\n正在关闭归档数据库连接。")