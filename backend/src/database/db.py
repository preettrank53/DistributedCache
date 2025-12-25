"""
SQLite Database Manager for DistriCache
"""
import sqlite3
import threading
from typing import Optional
from pathlib import Path
import os


class DatabaseManager:
    """
    SQLite database wrapper for storing cache data.
    
    Thread-safe database operations.
    """
    
    def __init__(self, db_path: str = "cache_db.sqlite"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
    
    def save_to_db(self, key: str, value: str) -> bool:
        """
        Save or update a key-value pair in the database.
        
        Args:
            key: The key
            value: The value (as string)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Use INSERT OR REPLACE for upsert functionality
                cursor.execute("""
                    INSERT OR REPLACE INTO users (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
                
                conn.commit()
                conn.close()
                return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def fetch_from_db(self, key: str) -> Optional[str]:
        """
        Fetch a value from the database by key.
        
        Args:
            key: The key to fetch
            
        Returns:
            The value if found, None otherwise
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT value FROM users WHERE key = ?", (key,))
                result = cursor.fetchone()
                conn.close()
                
                return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
    
    def delete_from_db(self, key: str) -> bool:
        """
        Delete a key-value pair from the database.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM users WHERE key = ?", (key,))
                conn.commit()
                affected_rows = cursor.rowcount
                conn.close()
                
                return affected_rows > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_all(self) -> list[tuple[str, str]]:
        """
        Get all key-value pairs from the database.
        
        Returns:
            List of (key, value) tuples
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT key, value FROM users")
                results = cursor.fetchall()
                conn.close()
                
                return results
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
    
    def clear_db(self) -> bool:
        """
        Clear all entries from the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM users")
                conn.commit()
                conn.close()
                return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def close(self) -> None:
        """Close database connection."""
        # No persistent connection to close, but keeping for compatibility
        pass
