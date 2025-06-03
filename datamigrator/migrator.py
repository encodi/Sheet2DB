"""
Main Migrator class for DataMigrator

Orchestrates the entire data migration process from files to databases.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd

from .utils.logger import get_logger, setup_logger
from .utils.file_utils import list_input_files, calculate_file_hash, get_file_size
from .readers.csv_reader import CSVReader
from .readers.excel_reader import ExcelReader
from .schema_inference.inferrer import SchemaInferrer
from .transformers.data_cleaner import DataCleaner
from .metadata.metadata_store import MetadataStore
from .engine_adapters.postgres_adapter import PostgresAdapter
from .engine_adapters.mysql_adapter import MySQLAdapter
from .engine_adapters.mongo_adapter import MongoAdapter

# Import SQL Server adapter if available
try:
    from .engine_adapters.mssql_adapter import MSSQLAdapter
    HAS_MSSQL = True
except ImportError:
    MSSQLAdapter = None
    HAS_MSSQL = False


class Migrator:
    """
    Main migration orchestrator for DataMigrator.
    
    Handles the complete workflow:
    1. File discovery and hash checking
    2. Data reading and cleaning
    3. Schema inference
    4. Database connection and table creation
    5. Data insertion
    6. Metadata tracking
    """
    
    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls']
    
    def __init__(self, input_folder: str, engine: str, connection_string: str, 
                 db_name: str, options: Optional[Dict[str, Any]] = None):
        """
        Initialize the Migrator.
        
        Args:
            input_folder: Path to folder containing files to migrate
            engine: Database engine ('postgres', 'mysql', 'mssql', 'mongo')
            connection_string: Database connection string
            db_name: Target database name
            options: Configuration options:
                - infer_schema: Enable automatic schema inference (default: True)
                - batch_size: Batch size for data insertion (default: 1000)
                - overwrite_existing: Drop and recreate existing tables (default: False)
                - dry_run: Preview mode without actual execution (default: False)
                - preview: Show preview of data and schema only (default: False)
                - log_level: Logging level (default: INFO)
                - clean_data: Enable data cleaning (default: True)
                - use_metadata_store: Track imports with metadata (default: True)
        """
        self.input_folder = input_folder
        self.engine_name = engine.lower()
        self.connection_string = connection_string
        self.db_name = db_name
        self.options = options or {}
        
        # Build supported engines list based on available adapters
        self.SUPPORTED_ENGINES = {
            'postgres': PostgresAdapter,
            'mysql': MySQLAdapter,
            'mongo': MongoAdapter
        }
        
        if HAS_MSSQL:
            self.SUPPORTED_ENGINES['mssql'] = MSSQLAdapter
        
        # Validate engine
        if self.engine_name not in self.SUPPORTED_ENGINES:
            available_engines = list(self.SUPPORTED_ENGINES.keys())
            raise ValueError(f"Unsupported engine: {engine}. Available: {available_engines}")
        
        # Special check for SQL Server if not available
        if self.engine_name == 'mssql' and not HAS_MSSQL:
            raise ValueError("SQL Server support requires pyodbc and ODBC drivers to be installed")
        
        # Set up logging
        log_level = self.options.get('log_level', 'INFO')
        self.logger = setup_logger("datamigrator", log_level)
        
        # Configuration options
        self.infer_schema = self.options.get('infer_schema', True)
        self.batch_size = self.options.get('batch_size', 1000)
        self.overwrite_existing = self.options.get('overwrite_existing', False)
        self.dry_run = self.options.get('dry_run', False)
        self.preview = self.options.get('preview', False)
        self.clean_data = self.options.get('clean_data', True)
        self.use_metadata_store = self.options.get('use_metadata_store', True)
        
        # Initialize components
        self.adapter = None
        self.schema_inferrer = None
        self.data_cleaner = None
        self.metadata_store = None
        
        self.logger.info(f"Initialized DataMigrator for {self.engine_name} database '{self.db_name}'")
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the complete migration process.
        
        Returns:
            Dictionary with migration results and statistics
        """
        self.logger.info("Starting data migration process")
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Discover input files
            files = self._discover_files()
            if not files:
                self.logger.warning("No supported files found in input folder")
                return {'status': 'completed', 'files_processed': 0, 'total_rows': 0}
            
            # Process each file
            results = {
                'status': 'completed',
                'files_processed': 0,
                'files_skipped': 0,
                'total_rows': 0,
                'errors': [],
                'file_results': []
            }
            
            for file_path in files:
                try:
                    file_result = self._process_file(file_path)
                    results['file_results'].append(file_result)
                    
                    if file_result['status'] == 'success':
                        results['files_processed'] += 1
                        results['total_rows'] += file_result.get('rows_inserted', 0)
                    elif file_result['status'] == 'skipped':
                        results['files_skipped'] += 1
                    else:
                        results['errors'].append(file_result.get('error', 'Unknown error'))
                        
                except Exception as e:
                    error_msg = f"Error processing file {file_path}: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['file_results'].append({
                        'file': file_path,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Close connections
            if self.adapter:
                self.adapter.close_connection()
            
            self.logger.info(f"Migration completed. Processed {results['files_processed']} files, "
                           f"inserted {results['total_rows']} total rows")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            if self.adapter:
                self.adapter.close_connection()
            raise
    
    def _initialize_components(self) -> None:
        """Initialize all required components."""
        self.logger.info("Initializing migration components")
        
        # Initialize database adapter
        adapter_class = self.SUPPORTED_ENGINES[self.engine_name]
        self.adapter = adapter_class(
            connection_string=self.connection_string,
            db_name=self.db_name,
            options=self.options
        )
        
        # Connect to database
        if not self.dry_run:
            self.adapter.create_database_if_not_exists()
        
        # Initialize schema inferrer
        if self.infer_schema:
            self.schema_inferrer = SchemaInferrer(**self.options)
        
        # Initialize data cleaner
        if self.clean_data:
            self.data_cleaner = DataCleaner(**self.options)
        
        # Initialize metadata store
        if self.use_metadata_store and not self.dry_run:
            self.metadata_store = MetadataStore(
                adapter=self.adapter if self.engine_name != 'mongo' else None
            )
    
    def _discover_files(self) -> List[str]:
        """Discover supported files in the input folder."""
        self.logger.info(f"Discovering files in: {self.input_folder}")
        
        if not os.path.exists(self.input_folder):
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")
        
        files = list_input_files(self.input_folder, self.SUPPORTED_EXTENSIONS)
        self.logger.info(f"Found {len(files)} supported files")
        
        return files
    
    def _process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single file through the complete migration pipeline.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Dictionary with processing results
        """
        filename = os.path.basename(file_path)
        self.logger.info(f"Processing file: {filename}")
        
        try:
            # Calculate file hash for change detection
            file_hash = calculate_file_hash(file_path)
            file_size = get_file_size(file_path)
            
            # Check if file has changed (skip if not)
            if self.metadata_store and not self.overwrite_existing:
                last_hash = self.metadata_store.get_last_hash(filename)
                if last_hash == file_hash:
                    self.logger.info(f"Skipping {filename}, no changes detected")
                    return {
                        'file': filename,
                        'status': 'skipped',
                        'reason': 'no_changes'
                    }
            
            # Read file data
            data = self._read_file(file_path)
            
            # Handle multi-sheet files (Excel)
            if isinstance(data, dict):
                # Process each sheet separately
                total_rows = 0
                for sheet_name, df in data.items():
                    sheet_result = self._process_dataframe(
                        df, f"{filename}_{sheet_name}", file_path, file_hash, file_size
                    )
                    total_rows += sheet_result.get('rows_inserted', 0)
                
                return {
                    'file': filename,
                    'status': 'success',
                    'sheets_processed': len(data),
                    'rows_inserted': total_rows
                }
            else:
                # Process single DataFrame
                return self._process_dataframe(data, filename, file_path, file_hash, file_size)
                
        except Exception as e:
            error_msg = f"Error processing {filename}: {e}"
            self.logger.error(error_msg)
            
            # Record error in metadata store
            if self.metadata_store:
                try:
                    self.metadata_store.record_import(
                        filename=filename,
                        file_hash=file_hash if 'file_hash' in locals() else 'unknown',
                        row_count=0,
                        table_name='',
                        status='error',
                        error_message=str(e)
                    )
                except:
                    pass  # Don't fail if metadata recording fails
            
            return {
                'file': filename,
                'status': 'error',
                'error': str(e)
            }
    
    def _read_file(self, file_path: str) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Read data from a file using the appropriate reader."""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.csv':
            reader = CSVReader(file_path, **self.options)
            return reader.read()
        elif file_ext in ['.xlsx', '.xls']:
            reader = ExcelReader(file_path, **self.options)
            return reader.read()
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
    
    def _process_dataframe(self, df: pd.DataFrame, table_name: str, file_path: str,
                          file_hash: str, file_size: int) -> Dict[str, Any]:
        """Process a single DataFrame through the migration pipeline."""
        if df.empty:
            self.logger.warning(f"DataFrame is empty for {table_name}")
            return {
                'file': os.path.basename(file_path),
                'table': table_name,
                'status': 'skipped',
                'reason': 'empty_dataframe'
            }
        
        self.logger.info(f"Processing DataFrame: {len(df)} rows, {len(df.columns)} columns")
        
        # Clean data if enabled
        if self.data_cleaner:
            df = self.data_cleaner.clean(df)
            self.logger.info(f"After cleaning: {len(df)} rows, {len(df.columns)} columns")
        
        # Infer schema
        schema = None
        if self.schema_inferrer:
            schema = self.schema_inferrer.infer_schema(df)
            self.logger.info(f"Inferred schema with {len(schema)} columns")
            
            # Log schema for preview/dry-run
            if self.preview or self.dry_run:
                self.logger.info("Inferred schema:")
                for col_schema in schema:
                    self.logger.info(f"  {col_schema}")
        
        # Preview mode - show data sample and exit
        if self.preview:
            self.logger.info(f"Data preview for {table_name}:")
            self.logger.info(f"\n{df.head()}")
            return {
                'file': os.path.basename(file_path),
                'table': table_name,
                'status': 'preview',
                'rows': len(df),
                'columns': len(df.columns)
            }
        
        # Dry run mode - show what would be done
        if self.dry_run:
            sanitized_table_name = self.adapter.validate_table_name(table_name)
            self.logger.info(f"DRY RUN: Would create table '{sanitized_table_name}' and insert {len(df)} rows")
            return {
                'file': os.path.basename(file_path),
                'table': sanitized_table_name,
                'status': 'dry_run',
                'rows': len(df),
                'columns': len(df.columns)
            }
        
        # Actual migration
        sanitized_table_name = self.adapter.validate_table_name(table_name)
        
        # Drop table if overwrite is enabled
        if self.overwrite_existing and self.adapter.table_exists(sanitized_table_name):
            self.logger.info(f"Dropping existing table: {sanitized_table_name}")
            self.adapter.drop_table(sanitized_table_name)
        
        # Create table
        if schema and not self.adapter.table_exists(sanitized_table_name):
            self.logger.info(f"Creating table: {sanitized_table_name}")
            self.adapter.create_table(sanitized_table_name, schema)
        
        # Insert data
        self.logger.info(f"Inserting data into table: {sanitized_table_name}")
        rows_inserted = self.adapter.insert_dataframe(
            sanitized_table_name, df, self.batch_size
        )
        
        # Record in metadata store
        if self.metadata_store:
            self.metadata_store.record_import(
                filename=os.path.basename(file_path),
                file_hash=file_hash,
                row_count=rows_inserted,
                table_name=sanitized_table_name,
                file_size=file_size,
                status='success'
            )
        
        return {
            'file': os.path.basename(file_path),
            'table': sanitized_table_name,
            'status': 'success',
            'rows_inserted': rows_inserted,
            'columns': len(df.columns)
        }
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get a summary of the migration configuration."""
        return {
            'input_folder': self.input_folder,
            'engine': self.engine_name,
            'database': self.db_name,
            'options': {
                'infer_schema': self.infer_schema,
                'batch_size': self.batch_size,
                'overwrite_existing': self.overwrite_existing,
                'dry_run': self.dry_run,
                'preview': self.preview,
                'clean_data': self.clean_data,
                'use_metadata_store': self.use_metadata_store
            },
            'supported_extensions': self.SUPPORTED_EXTENSIONS
        } 