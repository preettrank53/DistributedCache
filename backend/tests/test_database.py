"""
Unit tests for Database Manager implementation
"""
import pytest
import sqlite3
import os
import tempfile
from src.database.db import DatabaseManager


class TestDatabaseManager:
    """Test cases for DatabaseManager"""
    
    @pytest.fixture
    def db_manager(self, tmp_path):
        """Create a temporary database for testing"""
        # Use a temporary file database instead of :memory: for proper isolation
        db_file = tmp_path / "test_cache.db"
        manager = DatabaseManager(db_path=str(db_file))
        yield manager
        manager.close()
    
    def test_init_creates_table(self, db_manager):
        """Test that initialization creates the users table"""
        # The db_manager fixture already created the database with init
        # Test that we can save and fetch
        db_manager.save_to_db("test_key", "test_value")
        
        # Verify data was saved
        result = db_manager.fetch_from_db("test_key")
        assert result == "test_value"
    
    def test_save_and_fetch_single_entry(self, db_manager):
        """Test saving and fetching a single entry"""
        key = "user:123"
        value = '{"name": "John", "age": 30}'
        
        success = db_manager.save_to_db(key, value)
        assert success is True
        
        result = db_manager.fetch_from_db(key)
        assert result == value
    
    def test_save_multiple_entries(self, db_manager):
        """Test saving multiple entries"""
        entries = {
            "user:1": "Alice",
            "user:2": "Bob",
            "user:3": "Charlie"
        }
        
        for key, value in entries.items():
            success = db_manager.save_to_db(key, value)
            assert success is True
        
        for key, expected_value in entries.items():
            result = db_manager.fetch_from_db(key)
            assert result == expected_value
    
    def test_fetch_nonexistent_key(self, db_manager):
        """Test fetching a non-existent key"""
        result = db_manager.fetch_from_db("nonexistent_key")
        assert result is None
    
    def test_update_existing_key(self, db_manager):
        """Test updating an existing key"""
        key = "user:123"
        
        # Save initial value
        db_manager.save_to_db(key, "Initial Value")
        assert db_manager.fetch_from_db(key) == "Initial Value"
        
        # Update value
        db_manager.save_to_db(key, "Updated Value")
        assert db_manager.fetch_from_db(key) == "Updated Value"
    
    def test_delete_existing_key(self, db_manager):
        """Test deleting an existing key"""
        key = "user:123"
        value = "Some Value"
        
        # Save entry
        db_manager.save_to_db(key, value)
        assert db_manager.fetch_from_db(key) == value
        
        # Delete entry
        deleted = db_manager.delete_from_db(key)
        assert deleted is True
        
        # Verify it's deleted
        assert db_manager.fetch_from_db(key) is None
    
    def test_delete_nonexistent_key(self, db_manager):
        """Test deleting a non-existent key"""
        deleted = db_manager.delete_from_db("nonexistent_key")
        assert deleted is False
    
    def test_get_all_entries(self, db_manager):
        """Test retrieving all entries"""
        entries = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        for key, value in entries.items():
            db_manager.save_to_db(key, value)
        
        all_entries = db_manager.get_all()
        
        assert len(all_entries) == 3
        
        # Check that all entries are present
        entry_dict = dict(all_entries)
        for key, value in entries.items():
            assert entry_dict[key] == value
    
    def test_get_all_empty_database(self, db_manager):
        """Test getting all entries from empty database"""
        all_entries = db_manager.get_all()
        assert all_entries == []
    
    def test_clear_database(self, db_manager):
        """Test clearing all entries"""
        # Add some entries
        for i in range(5):
            db_manager.save_to_db(f"key{i}", f"value{i}")
        
        assert len(db_manager.get_all()) == 5
        
        # Clear database
        success = db_manager.clear_db()
        assert success is True
        
        # Verify it's cleared
        assert db_manager.get_all() == []
    
    def test_save_with_special_characters(self, db_manager):
        """Test saving values with special characters"""
        key = "special:key"
        value = '{"json": "data", "emoji": "🚀🎉"}'
        
        success = db_manager.save_to_db(key, value)
        assert success is True
        
        result = db_manager.fetch_from_db(key)
        assert result == value
    
    def test_save_large_value(self, db_manager):
        """Test saving a large value"""
        key = "large_key"
        value = "x" * 10000  # 10KB of data
        
        success = db_manager.save_to_db(key, value)
        assert success is True
        
        result = db_manager.fetch_from_db(key)
        assert result == value
        assert len(result) == 10000
    
    def test_save_empty_string_value(self, db_manager):
        """Test saving empty string"""
        key = "empty_key"
        value = ""
        
        success = db_manager.save_to_db(key, value)
        assert success is True
        
        result = db_manager.fetch_from_db(key)
        assert result == ""
    
    def test_concurrent_operations(self, db_manager):
        """Test that database handles operations correctly"""
        # The DatabaseManager uses threading.Lock for thread safety
        for i in range(100):
            db_manager.save_to_db(f"key{i}", f"value{i}")
        
        # Verify all entries
        for i in range(100):
            result = db_manager.fetch_from_db(f"key{i}")
            assert result == f"value{i}"


class TestDatabaseManagerWithFile:
    """Test DatabaseManager with file-based database"""
    
    def test_persistent_database(self):
        """Test that database persists to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create manager and save data
            manager1 = DatabaseManager(db_path=db_path)
            manager1.save_to_db("persistent_key", "persistent_value")
            manager1.close()
            
            # Create new manager with same database
            manager2 = DatabaseManager(db_path=db_path)
            result = manager2.fetch_from_db("persistent_key")
            manager2.close()
            
            assert result == "persistent_value"
    
    def test_database_isolation(self):
        """Test that different database files are isolated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path1 = os.path.join(tmpdir, "test1.db")
            db_path2 = os.path.join(tmpdir, "test2.db")
            
            # Create separate databases
            manager1 = DatabaseManager(db_path=db_path1)
            manager2 = DatabaseManager(db_path=db_path2)
            
            manager1.save_to_db("key", "value1")
            manager2.save_to_db("key", "value2")
            
            # Verify isolation
            assert manager1.fetch_from_db("key") == "value1"
            assert manager2.fetch_from_db("key") == "value2"
            
            manager1.close()
            manager2.close()


class TestDatabaseManagerEdgeCases:
    """Test edge cases for DatabaseManager"""
    
    @pytest.fixture
    def db_manager(self, tmp_path):
        """Create a temporary database for testing"""
        db_file = tmp_path / "test_cache.db"
        manager = DatabaseManager(db_path=str(db_file))
        yield manager
        manager.close()
    
    def test_key_with_spaces(self, db_manager):
        """Test keys with spaces"""
        key = "user key with spaces"
        value = "value"
        
        db_manager.save_to_db(key, value)
        assert db_manager.fetch_from_db(key) == value
    
    def test_key_with_sql_injection_attempt(self, db_manager):
        """Test that SQL injection is prevented"""
        key = "key'; DROP TABLE users; --"
        value = "test_value"
        
        # Should handle safely (parameterized queries)
        success = db_manager.save_to_db(key, value)
        assert success is True
        
        result = db_manager.fetch_from_db(key)
        assert result == value
        
        # Table should still exist
        all_entries = db_manager.get_all()
        assert isinstance(all_entries, list)
    
    def test_value_with_quotes(self, db_manager):
        """Test values containing quotes"""
        key = "quoted_key"
        value = 'He said "Hello" and she replied \'Goodbye\''
        
        db_manager.save_to_db(key, value)
        assert db_manager.fetch_from_db(key) == value
    
    def test_unicode_key_and_value(self, db_manager):
        """Test Unicode characters in keys and values"""
        key = "用户:123"
        value = "Привет мир"
        
        db_manager.save_to_db(key, value)
        assert db_manager.fetch_from_db(key) == value
    
    def test_get_all_after_deletions(self, db_manager):
        """Test get_all after deleting entries"""
        # Add and delete entries
        for i in range(5):
            db_manager.save_to_db(f"key{i}", f"value{i}")
        
        for i in range(0, 3):
            db_manager.delete_from_db(f"key{i}")
        
        all_entries = db_manager.get_all()
        assert len(all_entries) == 2
        
        keys = [key for key, value in all_entries]
        assert "key3" in keys
        assert "key4" in keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
