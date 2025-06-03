"""
MongoDB adapter for DataMigrator

Implements MongoDB database connectivity using pymongo.
"""

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import List, Dict, Any
from .base_adapter import BaseAdapter
from ..schema_inference.inferrer import ColumnSchema


class MongoAdapter(BaseAdapter):
    """
    MongoDB database adapter using pymongo.
    
    Features:
    - Automatic database and collection creation
    - Document insertion from DataFrames
    - Index creation support
    - Connection pooling and error handling
    
    Note: MongoDB is schema-less, so schema inference is used mainly for logging
    and potential index creation.
    """
    
    def __init__(self, connection_string: str, db_name: str, options: Dict[str, Any] = None):
        """
        Initialize MongoDB adapter.
        
        Args:
            connection_string: MongoDB connection string (mongodb://user:pass@host:port)
            db_name: Target database name
            options: Additional options:
                - create_indexes: Create indexes on inferred columns (default: False)
                - batch_size: Batch size for bulk inserts (default: 1000)
        """
        super().__init__(connection_string, db_name, options)
        
        self.create_indexes = options.get('create_indexes', False)
        self.default_batch_size = options.get('batch_size', 1000)
        
        # MongoDB client and database
        self.client = None
        self.db = None
    
    def create_database_if_not_exists(self) -> None:
        """
        Create the database if it doesn't exist.
        In MongoDB, databases are created automatically when first accessed.
        """
        self.logger.info(f"Connecting to MongoDB database '{self.db_name}'")
        
        try:
            # Create MongoDB client
            self.client = MongoClient(self.connection_string)
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get database reference (creates it if it doesn't exist)
            self.db = self.client[self.db_name]
            
            self.logger.info(f"Successfully connected to MongoDB database '{self.db_name}'")
            
        except PyMongoError as e:
            self.logger.error(f"MongoDB error: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB database '{self.db_name}': {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
    
    def create_table(self, table_name: str, schema: List[ColumnSchema]) -> None:
        """
        Create a collection with the specified schema.
        In MongoDB, collections are created automatically when first accessed.
        Optionally creates indexes based on schema.
        """
        if not self.db:
            raise RuntimeError("Database connection not established. Call create_database_if_not_exists() first.")
        
        # Validate and sanitize collection name
        sanitized_collection_name = self.validate_table_name(table_name)
        self.logger.info(f"Creating collection '{sanitized_collection_name}' with {len(schema)} fields")
        
        try:
            # Create collection (MongoDB creates it automatically on first insert)
            collection = self.db[sanitized_collection_name]
            
            # Optionally create indexes based on schema
            if self.create_indexes:
                self._create_indexes(collection, schema)
            
            self.logger.info(f"Collection '{sanitized_collection_name}' ready")
            
        except PyMongoError as e:
            self.logger.error(f"Error creating collection '{sanitized_collection_name}': {e}")
            raise
    
    def _create_indexes(self, collection, schema: List[ColumnSchema]) -> None:
        """Create indexes on collection based on schema."""
        for col_schema in schema:
            sanitized_col_name = self.validate_column_name(col_schema.name)
            
            # Create index for certain types that might benefit from indexing
            if col_schema.sql_type in ['INTEGER', 'DATE', 'TIMESTAMP']:
                try:
                    collection.create_index(sanitized_col_name)
                    self.logger.debug(f"Created index on field '{sanitized_col_name}'")
                except PyMongoError as e:
                    self.logger.warning(f"Could not create index on '{sanitized_col_name}': {e}")
    
    def insert_dataframe(self, table_name: str, df: pd.DataFrame, batch_size: int = 1000) -> int:
        """
        Insert DataFrame data into the specified collection.
        """
        if not self.db:
            raise RuntimeError("Database connection not established")
        
        sanitized_collection_name = self.validate_table_name(table_name)
        
        if df.empty:
            self.logger.warning(f"DataFrame is empty, nothing to insert into '{sanitized_collection_name}'")
            return 0
        
        # Sanitize column names
        df_copy = df.copy()
        df_copy.columns = [self.validate_column_name(col) for col in df_copy.columns]
        
        self.logger.info(f"Inserting {len(df_copy)} documents into collection '{sanitized_collection_name}'")
        
        try:
            collection = self.db[sanitized_collection_name]
            
            # Convert DataFrame to list of dictionaries
            documents = df_copy.to_dict(orient='records')
            
            # Insert in batches
            total_inserted = 0
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                result = collection.insert_many(batch, ordered=False)
                total_inserted += len(result.inserted_ids)
                
                self.logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} documents")
            
            self.logger.info(f"Successfully inserted {total_inserted} documents into '{sanitized_collection_name}'")
            return total_inserted
            
        except PyMongoError as e:
            self.logger.error(f"Error inserting data into '{sanitized_collection_name}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error inserting data: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a collection exists in the database."""
        if not self.db:
            return False
        
        sanitized_collection_name = self.validate_table_name(table_name)
        
        try:
            collection_names = self.db.list_collection_names()
            return sanitized_collection_name in collection_names
            
        except PyMongoError as e:
            self.logger.error(f"Error checking if collection '{sanitized_collection_name}' exists: {e}")
            return False
    
    def drop_table(self, table_name: str) -> None:
        """Drop a collection from the database."""
        if not self.db:
            raise RuntimeError("Database connection not established")
        
        sanitized_collection_name = self.validate_table_name(table_name)
        
        if not self.table_exists(sanitized_collection_name):
            raise ValueError(f"Collection '{sanitized_collection_name}' does not exist")
        
        try:
            self.db[sanitized_collection_name].drop()
            self.logger.info(f"Collection '{sanitized_collection_name}' dropped successfully")
            
        except PyMongoError as e:
            self.logger.error(f"Error dropping collection '{sanitized_collection_name}': {e}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a collection."""
        if not self.db:
            raise RuntimeError("Database connection not established")
        
        sanitized_collection_name = self.validate_table_name(table_name)
        
        if not self.table_exists(sanitized_collection_name):
            raise ValueError(f"Collection '{sanitized_collection_name}' does not exist")
        
        try:
            collection = self.db[sanitized_collection_name]
            
            # Get document count
            doc_count = collection.count_documents({})
            
            # Get collection stats
            stats = self.db.command("collStats", sanitized_collection_name)
            
            # Sample a few documents to get field information
            sample_docs = list(collection.find().limit(100))
            
            # Analyze fields from sample documents
            all_fields = set()
            for doc in sample_docs:
                all_fields.update(doc.keys())
            
            # Remove MongoDB's _id field from analysis
            all_fields.discard('_id')
            
            # Get indexes
            indexes = list(collection.list_indexes())
            index_info = []
            for idx in indexes:
                index_info.append({
                    'name': idx.get('name'),
                    'keys': list(idx.get('key', {}).keys())
                })
            
            return {
                'collection_name': sanitized_collection_name,
                'database': self.db_name,
                'document_count': doc_count,
                'size_bytes': stats.get('size', 0),
                'storage_size_bytes': stats.get('storageSize', 0),
                'fields': sorted(list(all_fields)),
                'indexes': index_info
            }
            
        except PyMongoError as e:
            self.logger.error(f"Error getting collection info for '{sanitized_collection_name}': {e}")
            raise
    
    def close_connection(self) -> None:
        """Close the database connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.logger.info("MongoDB connection closed") 