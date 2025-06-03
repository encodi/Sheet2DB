"""
Metadata store for DataMigrator

Tracks file imports and hashes for incremental synchronization.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from ..utils.logger import get_logger
from ..engine_adapters.base_adapter import BaseAdapter


class MetadataStore:
    """
    Metadata store for tracking file imports and synchronization.
    
    Uses SQLite for local storage or the target database for centralized storage.
    Tracks file hashes, import timestamps, and row counts for incremental updates.
    """
    
    def __init__(self, adapter: Optional[BaseAdapter] = None, storage_path: Optional[str] = None):
        """
        Initialize metadata store.
        
        Args:
            adapter: Database adapter to use for storage (if None, uses SQLite)
            storage_path: Path for SQLite database (default: .datamigrator_metadata.db)
        """
        self.logger = get_logger(self.__class__.__name__)
        self.adapter = adapter
        self.storage_path = storage_path or ".datamigrator_metadata.db"
        self.use_sqlite = adapter is None
        
        # Initialize storage
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize the metadata storage (SQLite or target database)."""
        if self.use_sqlite:
            self._initialize_sqlite()
        else:
            self._initialize_database_table()
    
    def _initialize_sqlite(self) -> None:
        """Initialize SQLite metadata database."""
        self.logger.info(f"Initializing SQLite metadata store: {self.storage_path}")
        
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    filename TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER,
                    imported_at TIMESTAMP NOT NULL,
                    row_count INTEGER,
                    table_name TEXT,
                    status TEXT DEFAULT 'success',
                    error_message TEXT
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_filename_hash 
                ON file_metadata(filename, file_hash)
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.info("SQLite metadata store initialized successfully")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing SQLite metadata store: {e}")
            raise
    
    def _initialize_database_table(self) -> None:
        """Initialize metadata table in the target database."""
        if not self.adapter or not self.adapter.engine:
            raise RuntimeError("Database adapter not properly initialized")
        
        self.logger.info("Initializing metadata table in target database")
        
        try:
            # Create metadata table using raw SQL (since it's a system table)
            with self.adapter.engine.connect() as conn:
                # Check if table exists first
                if hasattr(self.adapter, 'table_exists') and self.adapter.table_exists('datamigrator_metadata'):
                    self.logger.info("Metadata table already exists")
                    return
                
                # Create table with database-specific syntax
                if 'postgresql' in str(self.adapter.engine.url):
                    create_sql = """
                        CREATE TABLE IF NOT EXISTS datamigrator_metadata (
                            filename VARCHAR(500) PRIMARY KEY,
                            file_hash VARCHAR(64) NOT NULL,
                            file_size BIGINT,
                            imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            row_count INTEGER,
                            table_name VARCHAR(255),
                            status VARCHAR(50) DEFAULT 'success',
                            error_message TEXT
                        )
                    """
                elif 'mysql' in str(self.adapter.engine.url):
                    create_sql = """
                        CREATE TABLE IF NOT EXISTS datamigrator_metadata (
                            filename VARCHAR(500) PRIMARY KEY,
                            file_hash VARCHAR(64) NOT NULL,
                            file_size BIGINT,
                            imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            row_count INTEGER,
                            table_name VARCHAR(255),
                            status VARCHAR(50) DEFAULT 'success',
                            error_message TEXT
                        )
                    """
                elif 'mssql' in str(self.adapter.engine.url):
                    create_sql = """
                        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'datamigrator_metadata')
                        CREATE TABLE datamigrator_metadata (
                            filename NVARCHAR(500) PRIMARY KEY,
                            file_hash NVARCHAR(64) NOT NULL,
                            file_size BIGINT,
                            imported_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                            row_count INTEGER,
                            table_name NVARCHAR(255),
                            status NVARCHAR(50) DEFAULT 'success',
                            error_message NVARCHAR(MAX)
                        )
                    """
                else:
                    # Generic SQL
                    create_sql = """
                        CREATE TABLE IF NOT EXISTS datamigrator_metadata (
                            filename VARCHAR(500) PRIMARY KEY,
                            file_hash VARCHAR(64) NOT NULL,
                            file_size INTEGER,
                            imported_at TIMESTAMP NOT NULL,
                            row_count INTEGER,
                            table_name VARCHAR(255),
                            status VARCHAR(50) DEFAULT 'success',
                            error_message TEXT
                        )
                    """
                
                conn.execute(create_sql)
                conn.commit()
            
            self.logger.info("Metadata table initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing metadata table: {e}")
            raise
    
    def record_import(self, filename: str, file_hash: str, row_count: int, 
                     table_name: str, file_size: Optional[int] = None,
                     status: str = 'success', error_message: Optional[str] = None) -> None:
        """
        Record a file import in the metadata store.
        
        Args:
            filename: Name of the imported file
            file_hash: SHA-256 hash of the file
            row_count: Number of rows imported
            table_name: Name of the target table
            file_size: Size of the file in bytes
            status: Import status ('success', 'error', 'partial')
            error_message: Error message if status is 'error'
        """
        self.logger.debug(f"Recording import for file: {filename}")
        
        if self.use_sqlite:
            self._record_import_sqlite(filename, file_hash, row_count, table_name, 
                                     file_size, status, error_message)
        else:
            self._record_import_database(filename, file_hash, row_count, table_name,
                                       file_size, status, error_message)
    
    def _record_import_sqlite(self, filename: str, file_hash: str, row_count: int,
                            table_name: str, file_size: Optional[int],
                            status: str, error_message: Optional[str]) -> None:
        """Record import in SQLite database."""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO file_metadata 
                (filename, file_hash, file_size, imported_at, row_count, table_name, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, file_hash, file_size, datetime.now(), row_count, table_name, status, error_message))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Recorded import for {filename} in SQLite")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error recording import in SQLite: {e}")
            raise
    
    def _record_import_database(self, filename: str, file_hash: str, row_count: int,
                              table_name: str, file_size: Optional[int],
                              status: str, error_message: Optional[str]) -> None:
        """Record import in target database."""
        try:
            with self.adapter.engine.connect() as conn:
                # Use database-specific upsert syntax
                if 'postgresql' in str(self.adapter.engine.url):
                    sql = """
                        INSERT INTO datamigrator_metadata 
                        (filename, file_hash, file_size, imported_at, row_count, table_name, status, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (filename) DO UPDATE SET
                        file_hash = EXCLUDED.file_hash,
                        file_size = EXCLUDED.file_size,
                        imported_at = EXCLUDED.imported_at,
                        row_count = EXCLUDED.row_count,
                        table_name = EXCLUDED.table_name,
                        status = EXCLUDED.status,
                        error_message = EXCLUDED.error_message
                    """
                elif 'mysql' in str(self.adapter.engine.url):
                    sql = """
                        INSERT INTO datamigrator_metadata 
                        (filename, file_hash, file_size, imported_at, row_count, table_name, status, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        file_hash = VALUES(file_hash),
                        file_size = VALUES(file_size),
                        imported_at = VALUES(imported_at),
                        row_count = VALUES(row_count),
                        table_name = VALUES(table_name),
                        status = VALUES(status),
                        error_message = VALUES(error_message)
                    """
                else:
                    # For SQL Server and others, use MERGE or separate INSERT/UPDATE
                    sql = """
                        INSERT INTO datamigrator_metadata 
                        (filename, file_hash, file_size, imported_at, row_count, table_name, status, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                
                conn.execute(sql, (filename, file_hash, file_size, datetime.now(), 
                                 row_count, table_name, status, error_message))
                conn.commit()
            
            self.logger.debug(f"Recorded import for {filename} in database")
            
        except Exception as e:
            self.logger.error(f"Error recording import in database: {e}")
            raise
    
    def get_last_hash(self, filename: str) -> Optional[str]:
        """
        Get the last recorded hash for a file.
        
        Args:
            filename: Name of the file
            
        Returns:
            Last recorded hash or None if file not found
        """
        if self.use_sqlite:
            return self._get_last_hash_sqlite(filename)
        else:
            return self._get_last_hash_database(filename)
    
    def _get_last_hash_sqlite(self, filename: str) -> Optional[str]:
        """Get last hash from SQLite database."""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT file_hash FROM file_metadata WHERE filename = ?", (filename,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else None
            
        except sqlite3.Error as e:
            self.logger.error(f"Error getting last hash from SQLite: {e}")
            return None
    
    def _get_last_hash_database(self, filename: str) -> Optional[str]:
        """Get last hash from target database."""
        try:
            from sqlalchemy import text

            with self.adapter.engine.connect() as conn:
                query = text(
                    "SELECT file_hash FROM datamigrator_metadata WHERE filename = :filename"
                )
                result = conn.execute(query, {"filename": filename}).fetchone()
                
                return result[0] if result else None
                
        except Exception as e:
            self.logger.error(f"Error getting last hash from database: {e}")
            return None
    
    def get_import_history(self, filename: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get import history for all files or a specific file.
        
        Args:
            filename: Specific filename to query (None for all files)
            
        Returns:
            List of import records
        """
        if self.use_sqlite:
            return self._get_import_history_sqlite(filename)
        else:
            return self._get_import_history_database(filename)
    
    def _get_import_history_sqlite(self, filename: Optional[str]) -> List[Dict[str, Any]]:
        """Get import history from SQLite database."""
        try:
            conn = sqlite3.connect(self.storage_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            if filename:
                cursor.execute(
                    "SELECT * FROM file_metadata WHERE filename = ? ORDER BY imported_at DESC",
                    (filename,)
                )
            else:
                cursor.execute("SELECT * FROM file_metadata ORDER BY imported_at DESC")
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
            
        except sqlite3.Error as e:
            self.logger.error(f"Error getting import history from SQLite: {e}")
            return []
    
    def _get_import_history_database(self, filename: Optional[str]) -> List[Dict[str, Any]]:
        """Get import history from target database."""
        try:
            from sqlalchemy import text

            with self.adapter.engine.connect() as conn:
                if filename:
                    query = text(
                        "SELECT * FROM datamigrator_metadata WHERE filename = :filename ORDER BY imported_at DESC"
                    )
                    result = conn.execute(query, {"filename": filename})
                else:
                    query = text("SELECT * FROM datamigrator_metadata ORDER BY imported_at DESC")
                    result = conn.execute(query)
                
                # Convert to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting import history from database: {e}")
            return []
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Clean up old metadata records.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        if self.use_sqlite:
            return self._cleanup_old_records_sqlite(cutoff_date)
        else:
            return self._cleanup_old_records_database(cutoff_date)
    
    def _cleanup_old_records_sqlite(self, cutoff_date: datetime) -> int:
        """Clean up old records from SQLite database."""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM file_metadata WHERE imported_at < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleaned up {deleted_count} old metadata records")
            return deleted_count
            
        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up old records from SQLite: {e}")
            return 0
    
    def _cleanup_old_records_database(self, cutoff_date: datetime) -> int:
        """Clean up old records from target database."""
        try:
            from sqlalchemy import text

            with self.adapter.engine.connect() as conn:
                query = text(
                    "DELETE FROM datamigrator_metadata WHERE imported_at < :cutoff"
                )
                result = conn.execute(query, {"cutoff": cutoff_date})
                deleted_count = result.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old metadata records")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old records from database: {e}")
            return 0 