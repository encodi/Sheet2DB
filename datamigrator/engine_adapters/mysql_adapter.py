"""
MySQL adapter for DataMigrator

Implements MySQL database connectivity using SQLAlchemy and PyMySQL.
"""

import pandas as pd
import pymysql
from sqlalchemy import create_engine, MetaData, Table, Column, text
from sqlalchemy import Integer, String, Text, Boolean, Numeric, Date, DateTime
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
from .base_adapter import BaseAdapter
from ..schema_inference.inferrer import ColumnSchema


class MySQLAdapter(BaseAdapter):
    """
    MySQL database adapter using SQLAlchemy and PyMySQL.
    
    Features:
    - Automatic database creation
    - Schema inference and table creation
    - Batch data insertion
    - Connection pooling and error handling
    """
    
    def __init__(self, connection_string: str, db_name: str, options: Dict[str, Any] = None):
        """
        Initialize MySQL adapter.
        
        Args:
            connection_string: MySQL connection string (mysql+pymysql://user:pass@host:port)
            db_name: Target database name
            options: Additional options:
                - charset: Character set (default: utf8mb4)
                - use_load_data: Use LOAD DATA for bulk inserts (default: False)
        """
        super().__init__(connection_string, db_name, options)
        
        self.charset = options.get('charset', 'utf8mb4')
        self.use_load_data = options.get('use_load_data', False)
        
        # Build full connection string with database
        if '/' in connection_string:
            # Remove existing database from connection string
            base_connection = '/'.join(connection_string.split('/')[:-1])
        else:
            base_connection = connection_string
        
        self.full_connection_string = f"{base_connection}/{db_name}?charset={self.charset}"
        self.server_connection_string = f"{base_connection}?charset={self.charset}"
        
        # Initialize engine (will be set after database creation)
        self.engine = None
        self.metadata = MetaData()
    
    def _get_server_connection_info(self) -> Dict[str, str]:
        """Extract connection parameters for server-level operations."""
        # Parse connection string to get individual components
        # Format: mysql+pymysql://user:password@host:port/database
        import re
        
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)'
        match = re.match(pattern, self.connection_string)
        
        if not match:
            raise ValueError(f"Invalid MySQL connection string format")
        
        user, password, host, port = match.groups()
        
        return {
            'host': host,
            'port': int(port),
            'user': user,
            'password': password
        }
    
    def create_database_if_not_exists(self) -> None:
        """
        Create the database if it doesn't exist.
        Uses PyMySQL to connect to the server and create the database.
        """
        self.logger.info(f"Checking if database '{self.db_name}' exists")
        
        conn_info = self._get_server_connection_info()
        
        try:
            # Connect to MySQL server without specifying database
            conn = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['user'],
                password=conn_info['password'],
                charset=self.charset
            )
            
            cursor = conn.cursor()
            
            # Create database if it doesn't exist
            self.logger.info(f"Creating database '{self.db_name}' if it doesn't exist")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` CHARACTER SET {self.charset}")
            
            cursor.close()
            conn.close()
            
            # Now create the SQLAlchemy engine for the target database
            self.engine = create_engine(
                self.full_connection_string,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.logger.info(f"Successfully connected to database '{self.db_name}'")
            
        except pymysql.Error as e:
            self.logger.error(f"MySQL error: {e}")
            raise ConnectionError(f"Failed to create/connect to database '{self.db_name}': {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
    
    def _map_sql_type_to_sqlalchemy(self, column_schema: ColumnSchema):
        """Map generic SQL types to SQLAlchemy MySQL types."""
        sql_type = column_schema.sql_type.upper()
        
        if sql_type == 'INTEGER':
            return Integer
        elif sql_type == 'BOOLEAN':
            return Boolean
        elif sql_type == 'DATE':
            return Date
        elif sql_type == 'TIMESTAMP':
            return DateTime
        elif sql_type == 'NUMERIC':
            if column_schema.precision and column_schema.scale is not None:
                return Numeric(precision=column_schema.precision, scale=column_schema.scale)
            else:
                return Numeric(precision=10, scale=2)
        elif sql_type == 'VARCHAR':
            length = column_schema.max_length or 255
            # MySQL has a limit on VARCHAR length
            if length > 65535:
                return Text
            return String(length)
        elif sql_type == 'TEXT':
            return Text
        else:
            # Default to VARCHAR for unknown types
            return String(255)
    
    def create_table(self, table_name: str, schema: List[ColumnSchema]) -> None:
        """
        Create a table with the specified schema.
        """
        if not self.engine:
            raise RuntimeError("Database connection not established. Call create_database_if_not_exists() first.")
        
        # Validate and sanitize table name
        sanitized_table_name = self.validate_table_name(table_name)
        self.logger.info(f"Creating table '{sanitized_table_name}' with {len(schema)} columns")
        
        try:
            # Create table columns
            columns = []
            for col_schema in schema:
                sanitized_col_name = self.validate_column_name(col_schema.name)
                sqlalchemy_type = self._map_sql_type_to_sqlalchemy(col_schema)
                
                column = Column(
                    sanitized_col_name,
                    sqlalchemy_type,
                    nullable=col_schema.nullable
                )
                columns.append(column)
            
            # Create table object
            table = Table(
                sanitized_table_name,
                self.metadata,
                *columns
            )
            
            # Create the table in the database
            table.create(self.engine, checkfirst=True)
            
            self.logger.info(f"Table '{sanitized_table_name}' created successfully")
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error creating table '{sanitized_table_name}': {e}")
            raise
    
    def insert_dataframe(self, table_name: str, df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Insert DataFrame data into the specified table.
        """
        if not self.engine:
            raise RuntimeError("Database connection not established")
        
        sanitized_table_name = self.validate_table_name(table_name)
        
        if df.empty:
            self.logger.warning(f"DataFrame is empty, nothing to insert into '{sanitized_table_name}'")
            return 0
        
        # Sanitize column names to match table schema
        df_copy = df.copy()
        df_copy.columns = [self.validate_column_name(col) for col in df_copy.columns]
        
        self.logger.info(f"Inserting {len(df_copy)} rows into table '{sanitized_table_name}'")
        
        try:
            # Use pandas to_sql for MySQL
            df_copy.to_sql(
                name=sanitized_table_name,
                con=self.engine,
                if_exists='append',
                index=False,
                chunksize=batch_size,
                method='multi'
            )
            
            self.logger.info(f"Successfully inserted {len(df_copy)} rows into '{sanitized_table_name}'")
            return len(df_copy)
            
        except Exception as e:
            self.logger.error(f"Error inserting data into '{sanitized_table_name}': {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        if not self.engine:
            return False
        
        sanitized_table_name = self.validate_table_name(table_name)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :database AND table_name = :table"
                ), {'database': self.db_name, 'table': sanitized_table_name})
                
                return result.scalar() > 0
                
        except Exception as e:
            self.logger.error(f"Error checking if table '{sanitized_table_name}' exists: {e}")
            return False
    
    def drop_table(self, table_name: str) -> None:
        """Drop a table from the database."""
        if not self.engine:
            raise RuntimeError("Database connection not established")
        
        sanitized_table_name = self.validate_table_name(table_name)
        
        if not self.table_exists(sanitized_table_name):
            raise ValueError(f"Table '{sanitized_table_name}' does not exist")
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f'DROP TABLE `{sanitized_table_name}`'))
                conn.commit()
            
            self.logger.info(f"Table '{sanitized_table_name}' dropped successfully")
            
        except Exception as e:
            self.logger.error(f"Error dropping table '{sanitized_table_name}': {e}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        if not self.engine:
            raise RuntimeError("Database connection not established")
        
        sanitized_table_name = self.validate_table_name(table_name)
        
        if not self.table_exists(sanitized_table_name):
            raise ValueError(f"Table '{sanitized_table_name}' does not exist")
        
        try:
            with self.engine.connect() as conn:
                # Get column information
                columns_query = text("""
                    SELECT column_name, data_type, is_nullable, character_maximum_length,
                           numeric_precision, numeric_scale
                    FROM information_schema.columns 
                    WHERE table_schema = :database AND table_name = :table
                    ORDER BY ordinal_position
                """)
                
                result = conn.execute(columns_query, {
                    'database': self.db_name, 
                    'table': sanitized_table_name
                })
                
                columns = []
                for row in result:
                    columns.append({
                        'name': row[0],
                        'type': row[1],
                        'nullable': row[2] == 'YES',
                        'max_length': row[3],
                        'precision': row[4],
                        'scale': row[5]
                    })
                
                # Get row count
                count_result = conn.execute(text(f'SELECT COUNT(*) FROM `{sanitized_table_name}`'))
                row_count = count_result.scalar()
                
                return {
                    'table_name': sanitized_table_name,
                    'database': self.db_name,
                    'columns': columns,
                    'row_count': row_count
                }
                
        except Exception as e:
            self.logger.error(f"Error getting table info for '{sanitized_table_name}': {e}")
            raise
    
    def close_connection(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.logger.info("MySQL connection closed") 