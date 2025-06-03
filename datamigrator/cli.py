"""
Command-line interface for DataMigrator

Provides a CLI for running data migrations from the command line.
"""

import click
import sys
import json
from pathlib import Path
from typing import Dict, Any

from .migrator import Migrator
from .utils.logger import setup_logger


@click.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True),
              help='Folder containing CSV/Excel files to migrate')
@click.option('--engine', '-e', required=True, 
              type=click.Choice(['postgres', 'mysql', 'mssql', 'mongo'], case_sensitive=False),
              help='Target database engine')
@click.option('--connection', '-c', required=True,
              help='Database connection string')
@click.option('--db-name', '-d', required=True,
              help='Target database name')
@click.option('--infer-schema/--no-infer-schema', default=True,
              help='Enable automatic schema inference (default: enabled)')
@click.option('--batch-size', '-b', default=1000, type=int,
              help='Batch size for data insertion (default: 1000)')
@click.option('--overwrite-existing/--no-overwrite-existing', default=False,
              help='Drop and recreate existing tables (default: disabled)')
@click.option('--dry-run/--no-dry-run', default=False,
              help='Preview mode without actual execution (default: disabled)')
@click.option('--preview/--no-preview', default=False,
              help='Show data preview and schema only (default: disabled)')
@click.option('--log-level', '-l', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              help='Logging level (default: INFO)')
@click.option('--clean-data/--no-clean-data', default=True,
              help='Enable data cleaning (default: enabled)')
@click.option('--use-metadata-store/--no-use-metadata-store', default=True,
              help='Track imports with metadata store (default: enabled)')
@click.option('--config-file', type=click.Path(exists=True),
              help='JSON configuration file (overrides command line options)')
@click.option('--output-format', default='text',
              type=click.Choice(['text', 'json'], case_sensitive=False),
              help='Output format for results (default: text)')
def migrate(input_folder: str, engine: str, connection: str, db_name: str,
         infer_schema: bool, batch_size: int, overwrite_existing: bool,
         dry_run: bool, preview: bool, log_level: str, clean_data: bool,
         use_metadata_store: bool, config_file: str, output_format: str):
    """
    DataMigrator - Automated CSV and Excel to Database Migration Tool
    
    Migrates CSV and Excel files to SQL and NoSQL databases with automatic
    schema inference, data cleaning, and incremental synchronization.
    
    Examples:
    
    \b
    # Migrate CSV files to PostgreSQL
    migrate-data -i ./data -e postgres -c "postgresql+psycopg2://user:pass@localhost:5432" -d mydb
    
    \b
    # Dry run with preview
    migrate-data -i ./data -e mysql -c "mysql+pymysql://user:pass@localhost:3306" -d mydb --dry-run
    
    \b
    # MongoDB migration with custom batch size
    migrate-data -i ./data -e mongo -c "mongodb://localhost:27017" -d mydb -b 500
    """
    try:
        # Load configuration from file if provided
        config = {}
        if config_file:
            config = load_config_file(config_file)
        
        # Build options dictionary (command line overrides config file)
        options = {
            'infer_schema': config.get('infer_schema', infer_schema),
            'batch_size': config.get('batch_size', batch_size),
            'overwrite_existing': config.get('overwrite_existing', overwrite_existing),
            'dry_run': config.get('dry_run', dry_run),
            'preview': config.get('preview', preview),
            'log_level': config.get('log_level', log_level),
            'clean_data': config.get('clean_data', clean_data),
            'use_metadata_store': config.get('use_metadata_store', use_metadata_store)
        }
        
        # Add any additional options from config file
        for key, value in config.items():
            if key not in options:
                options[key] = value
        
        # Override with command line values if provided in config
        input_folder = config.get('input_folder', input_folder)
        engine = config.get('engine', engine)
        connection = config.get('connection', connection)
        db_name = config.get('db_name', db_name)
        
        # Set up logging
        setup_logger("datamigrator", options['log_level'])
        
        # Display configuration
        if not options['preview'] and not options['dry_run']:
            click.echo("DataMigrator Configuration:")
            click.echo(f"  Input folder: {input_folder}")
            click.echo(f"  Engine: {engine}")
            click.echo(f"  Database: {db_name}")
            click.echo(f"  Batch size: {options['batch_size']}")
            click.echo(f"  Schema inference: {'enabled' if options['infer_schema'] else 'disabled'}")
            click.echo(f"  Data cleaning: {'enabled' if options['clean_data'] else 'disabled'}")
            click.echo(f"  Overwrite existing: {'enabled' if options['overwrite_existing'] else 'disabled'}")
            click.echo("")
        
        # Create and run migrator
        migrator = Migrator(
            input_folder=input_folder,
            engine=engine,
            connection_string=connection,
            db_name=db_name,
            options=options
        )
        
        # Execute migration
        results = migrator.run()
        
        # Display results
        display_results(results, output_format)
        
        # Exit with appropriate code
        if results.get('errors'):
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        click.echo(f"Loaded configuration from: {config_path}")
        return config
    except Exception as e:
        raise click.ClickException(f"Error loading config file {config_path}: {e}")


def display_results(results: Dict[str, Any], output_format: str) -> None:
    """Display migration results in the specified format."""
    if output_format == 'json':
        click.echo(json.dumps(results, indent=2, default=str))
    else:
        # Text format
        status = results.get('status', 'unknown')
        files_processed = results.get('files_processed', 0)
        files_skipped = results.get('files_skipped', 0)
        total_rows = results.get('total_rows', 0)
        errors = results.get('errors', [])
        
        click.echo("\nMigration Results:")
        click.echo(f"  Status: {status}")
        click.echo(f"  Files processed: {files_processed}")
        click.echo(f"  Files skipped: {files_skipped}")
        click.echo(f"  Total rows migrated: {total_rows}")
        
        if errors:
            click.echo(f"  Errors: {len(errors)}")
            for error in errors:
                click.echo(f"    - {error}")
        
        # Show file-level results
        file_results = results.get('file_results', [])
        if file_results:
            click.echo("\nFile Details:")
            for file_result in file_results:
                file_name = file_result.get('file', 'unknown')
                file_status = file_result.get('status', 'unknown')
                rows = file_result.get('rows_inserted', 0)
                
                if file_status == 'success':
                    click.echo(f"  ✓ {file_name}: {rows} rows")
                elif file_status == 'skipped':
                    reason = file_result.get('reason', 'unknown')
                    click.echo(f"  - {file_name}: skipped ({reason})")
                elif file_status == 'error':
                    error = file_result.get('error', 'unknown error')
                    click.echo(f"  ✗ {file_name}: error - {error}")
                elif file_status in ['preview', 'dry_run']:
                    rows = file_result.get('rows', 0)
                    cols = file_result.get('columns', 0)
                    click.echo(f"  → {file_name}: {rows} rows, {cols} columns")


@click.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True),
              help='Folder to analyze')
@click.option('--output-format', default='text',
              type=click.Choice(['text', 'json'], case_sensitive=False),
              help='Output format (default: text)')
def analyze(input_folder: str, output_format: str):
    """
    Analyze files in a folder and show what would be migrated.
    
    This command scans the input folder and provides information about
    the files that would be processed, including file types, sizes,
    and estimated schemas.
    """
    try:
        from datamigrator.utils.file_utils import list_input_files, get_file_size
        from datamigrator.readers.csv_reader import CSVReader
        from datamigrator.readers.excel_reader import ExcelReader
        from datamigrator.schema_inference.inferrer import SchemaInferrer
        
        # Discover files
        extensions = ['.csv', '.xlsx', '.xls']
        files = list_input_files(input_folder, extensions)
        
        if not files:
            click.echo("No supported files found in the input folder.")
            return
        
        # Analyze each file
        analysis_results = []
        schema_inferrer = SchemaInferrer()
        
        for file_path in files:
            try:
                file_info = analyze_file(file_path, schema_inferrer)
                analysis_results.append(file_info)
            except Exception as e:
                analysis_results.append({
                    'file': Path(file_path).name,
                    'error': str(e),
                    'status': 'error'
                })
        
        # Display results
        if output_format == 'json':
            click.echo(json.dumps(analysis_results, indent=2, default=str))
        else:
            display_analysis_results(analysis_results)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def analyze_file(file_path: str, schema_inferrer) -> Dict[str, Any]:
    """Analyze a single file and return information about it."""
    from datamigrator.utils.file_utils import get_file_size
    from datamigrator.readers.csv_reader import CSVReader
    from datamigrator.readers.excel_reader import ExcelReader
    
    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix.lower()
    file_size = get_file_size(file_path)
    
    # Read file
    if file_ext == '.csv':
        reader = CSVReader(file_path)
        data = reader.read()
    elif file_ext in ['.xlsx', '.xls']:
        reader = ExcelReader(file_path)
        data = reader.read()
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Analyze data
    if isinstance(data, dict):
        # Multi-sheet Excel file
        sheets_info = []
        total_rows = 0
        for sheet_name, df in data.items():
            schema = schema_inferrer.infer_schema(df)
            sheets_info.append({
                'sheet_name': sheet_name,
                'rows': len(df),
                'columns': len(df.columns),
                'schema': [str(col) for col in schema]
            })
            total_rows += len(df)
        
        return {
            'file': file_name,
            'type': 'excel_multi_sheet',
            'size_bytes': file_size,
            'sheets': len(data),
            'total_rows': total_rows,
            'sheets_info': sheets_info,
            'status': 'success'
        }
    else:
        # Single DataFrame (CSV or single-sheet Excel)
        schema = schema_inferrer.infer_schema(data)
        return {
            'file': file_name,
            'type': 'single_table',
            'size_bytes': file_size,
            'rows': len(data),
            'columns': len(data.columns),
            'schema': [str(col) for col in schema],
            'status': 'success'
        }


def display_analysis_results(results: list) -> None:
    """Display file analysis results in text format."""
    click.echo(f"\nFile Analysis Results ({len(results)} files):")
    click.echo("=" * 60)
    
    total_files = len(results)
    total_rows = 0
    error_count = 0
    
    for result in results:
        file_name = result.get('file', 'unknown')
        status = result.get('status', 'unknown')
        
        if status == 'error':
            error_count += 1
            error = result.get('error', 'unknown error')
            click.echo(f"✗ {file_name}: ERROR - {error}")
            continue
        
        file_type = result.get('type', 'unknown')
        size_bytes = result.get('size_bytes', 0)
        size_mb = size_bytes / (1024 * 1024)
        
        if file_type == 'excel_multi_sheet':
            sheets = result.get('sheets', 0)
            rows = result.get('total_rows', 0)
            total_rows += rows
            click.echo(f"📊 {file_name} ({size_mb:.1f} MB)")
            click.echo(f"   Type: Excel with {sheets} sheets")
            click.echo(f"   Total rows: {rows:,}")
            
            for sheet_info in result.get('sheets_info', []):
                sheet_name = sheet_info.get('sheet_name', 'unknown')
                sheet_rows = sheet_info.get('rows', 0)
                sheet_cols = sheet_info.get('columns', 0)
                click.echo(f"   - {sheet_name}: {sheet_rows:,} rows, {sheet_cols} columns")
        else:
            rows = result.get('rows', 0)
            columns = result.get('columns', 0)
            total_rows += rows
            click.echo(f"📄 {file_name} ({size_mb:.1f} MB)")
            click.echo(f"   Rows: {rows:,}, Columns: {columns}")
            
            # Show first few schema columns
            schema = result.get('schema', [])
            if schema:
                click.echo("   Schema preview:")
                for col_schema in schema[:3]:  # Show first 3 columns
                    click.echo(f"     {col_schema}")
                if len(schema) > 3:
                    click.echo(f"     ... and {len(schema) - 3} more columns")
        
        click.echo("")
    
    # Summary
    click.echo("Summary:")
    click.echo(f"  Total files: {total_files}")
    click.echo(f"  Successful: {total_files - error_count}")
    click.echo(f"  Errors: {error_count}")
    click.echo(f"  Total rows: {total_rows:,}")


# Create a group to hold multiple commands
@click.group()
def cli():
    """DataMigrator - Automated CSV and Excel to Database Migration Tool"""
    pass


# Add commands to the group
cli.add_command(migrate, name='migrate')
cli.add_command(analyze)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main() 