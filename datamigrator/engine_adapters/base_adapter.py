"""
Base adapter for DataMigrator database engines

Defines the abstract interface that all database adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from ..schema_inference.inferrer import ColumnSchema
from ..utils.logger import get_logger


class BaseAdapter(ABC):
    """
    Abstract base class for database adapters.
    
    All database adapters must inherit from this class and implement the required methods.
    """
    
    def __init__(self, connection_string: str, db_name: str, options: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter.
        
        Args:
            connection_string: Database connection string
            db_name: Name of the database
            options: Additional options specific to the adapter
        """
        self.connection_string = connection_string
        self.db_name = db_name
        self.options = options or {}
        self.logger = get_logger(self.__class__.__name__)
        
        # Connection and engine will be set by subclasses
        self.engine = None
        self.connection = None
    
    @abstractmethod
    def create_database_if_not_exists(self) -> None:
        """
        Create the database if it doesn't exist.
        
        Raises:
            ConnectionError: If unable to connect to database server
            PermissionError: If insufficient permissions to create database  
            Exception: For other database-specific errors
        """
        pass
    
    @abstractmethod
    def create_table(self, table_name: str, schema: List[ColumnSchema]) -> None:
        """
        Create a table with the specified schema.
        
        Args:
            table_name: Name of the table to create
            schema: List of ColumnSchema objects defining the table structure
            
        Raises:
            ValueError: If schema is invalid
            Exception: For database-specific errors
        """
        pass
    
    @abstractmethod
    def insert_dataframe(self, table_name: str, df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Insert DataFrame data into the specified table.
        
        Args:
            table_name: Name of the target table
            df: DataFrame containing the data to insert
            batch_size: Number of rows to insert in each batch
            
        Returns:
            Number of rows inserted
            
        Raises:
            ValueError: If table doesn't exist or DataFrame is incompatible
            Exception: For database-specific errors
        """
        pass
    
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
            
        Raises:
            Exception: For database-specific errors
        """
        pass
    
    @abstractmethod
    def drop_table(self, table_name: str) -> None:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of the table to drop
            
        Raises:
            ValueError: If table doesn't exist
            Exception: For database-specific errors
        """
        pass
    
    @abstractmethod
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a table (columns, types, etc.).
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
            
        Raises:
            ValueError: If table doesn't exist
            Exception: For database-specific errors
        """
        pass
    
    @abstractmethod
    def close_connection(self) -> None:
        """
        Close the database connection.
        """
        pass
    
    def validate_table_name(self, table_name: str) -> str:
        """
        Validate and sanitize table name.
        
        Args:
            table_name: Original table name
            
        Returns:
            Sanitized table name
        """
        # Remove file extensions and clean up
        if '.' in table_name:
            table_name = table_name.split('.')[0]
        
        # Replace spaces and special characters with underscores
        import re
        table_name = re.sub(r'[^\w]', '_', table_name)
        
        # Ensure it starts with a letter or underscore
        if table_name and not table_name[0].isalpha() and table_name[0] != '_':
            table_name = f"table_{table_name}"
        
        # Limit length (most databases have limits)
        if len(table_name) > 63:  # PostgreSQL limit
            table_name = table_name[:63]
        
        return table_name.lower()
    
    def validate_column_name(self, column_name: str) -> str:
        """
        Validate and sanitize column name.
        
        Args:
            column_name: Original column name
            
        Returns:
            Sanitized column name
        """
        # Replace spaces and special characters with underscores
        import re
        column_name = re.sub(r'[^\w]', '_', column_name)
        
        # Ensure it starts with a letter or underscore
        if column_name and not column_name[0].isalpha() and column_name[0] != '_':
            column_name = f"col_{column_name}"
        
        # Limit length
        if len(column_name) > 63:
            column_name = column_name[:63]
        
        return column_name.lower()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information (for debugging/logging).
        
        Returns:
            Dictionary with connection details
        """
        return {
            'connection_string': self.connection_string,
            'database_name': self.db_name,
            'adapter_type': self.__class__.__name__,
            'options': self.options
        }
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # This should be implemented by subclasses for specific testing
            return self.engine is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False 