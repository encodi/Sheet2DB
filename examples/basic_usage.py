#!/usr/bin/env python3
"""
Basic usage example for DataMigrator

This script demonstrates how to use DataMigrator programmatically
to migrate CSV and Excel files to a PostgreSQL database.
"""

from datamigrator import Migrator
import logging

def main():
    """Basic migration example."""
    
    # Configure logging to see what's happening
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the migrator
    migrator = Migrator(
        input_folder="./sample_data",  # Folder containing CSV/Excel files
        engine="postgres",             # Database engine
        connection_string="postgresql+psycopg2://user:password@localhost:5432",
        db_name="sample_db",          # Target database name
        options={
            'batch_size': 1000,       # Process 1000 rows at a time
            'clean_data': True,       # Enable data cleaning
            'infer_schema': True,     # Automatically infer column types
            'overwrite_existing': False,  # Don't drop existing tables
            'log_level': 'INFO'       # Logging level
        }
    )
    
    try:
        # Run the migration
        print("Starting migration...")
        results = migrator.run()
        
        # Display results
        print(f"\nMigration completed!")
        print(f"Status: {results['status']}")
        print(f"Files processed: {results['files_processed']}")
        print(f"Files skipped: {results['files_skipped']}")
        print(f"Total rows migrated: {results['total_rows']}")
        
        if results['errors']:
            print(f"Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        # Show file-level details
        if results['file_results']:
            print("\nFile Details:")
            for file_result in results['file_results']:
                file_name = file_result['file']
                status = file_result['status']
                if status == 'success':
                    rows = file_result.get('rows_inserted', 0)
                    print(f"  ✓ {file_name}: {rows} rows inserted")
                elif status == 'skipped':
                    reason = file_result.get('reason', 'unknown')
                    print(f"  - {file_name}: skipped ({reason})")
                elif status == 'error':
                    error = file_result.get('error', 'unknown error')
                    print(f"  ✗ {file_name}: error - {error}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 