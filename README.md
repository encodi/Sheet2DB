# DataMigrator

**Automated CSV and Excel to Database Migration Tool**

DataMigrator is a powerful Python library that automates the process of migrating data from CSV and Excel files to various database systems. It provides intelligent schema inference, data cleaning, and supports multiple database engines including PostgreSQL, MySQL, SQL Server, and MongoDB.

## Features

- 🚀 **Multi-Database Support**: PostgreSQL, MySQL, SQL Server, MongoDB
- 📊 **Smart Schema Inference**: Automatically detects column types and constraints
- 🧹 **Data Cleaning**: Removes empty rows/columns, trims whitespace, handles dates
- 📈 **Batch Processing**: Efficient handling of large datasets
- 🔄 **Incremental Sync**: Tracks file changes to avoid duplicate imports
- 🎯 **Flexible Input**: Supports CSV, Excel (.xlsx, .xls) with multi-sheet processing
- 🛠️ **CLI Interface**: Easy-to-use command-line tool
- 📝 **Comprehensive Logging**: Detailed operation tracking and error reporting
- ⚙️ **Configurable**: Extensive customization options

## Installation

### From PyPI (when published)
```bash
pip install datamigrator
```

### From Source
```bash
git clone https://github.com/yourusername/datamigrator.git
cd datamigrator
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/yourusername/datamigrator.git
cd datamigrator
pip install -e ".[dev]"
```

## Quick Start

### Command Line Usage

```bash
# Migrate CSV files to PostgreSQL
migrate-data -i ./data -e postgres -c "postgresql+psycopg2://user:pass@localhost:5432" -d mydb

# Dry run with preview
migrate-data -i ./data -e mysql -c "mysql+pymysql://user:pass@localhost:3306" -d mydb --dry-run

# MongoDB migration with custom batch size
migrate-data -i ./data -e mongo -c "mongodb://localhost:27017" -d mydb -b 500

# Analyze files before migration
migrate-data analyze -i ./data
```

### Python API Usage

```python
from datamigrator import Migrator

# Initialize migrator
migrator = Migrator(
    input_folder="./data",
    engine="postgres",
    connection_string="postgresql+psycopg2://user:pass@localhost:5432",
    db_name="mydb",
    options={
        'batch_size': 1000,
        'clean_data': True,
        'infer_schema': True
    }
)

# Run migration
results = migrator.run()
print(f"Processed {results['files_processed']} files")
```

## Supported Databases

| Database | Engine Name | Connection String Format |
|----------|-------------|-------------------------|
| PostgreSQL | `postgres` | `postgresql+psycopg2://user:pass@host:port` |
| MySQL | `mysql` | `mysql+pymysql://user:pass@host:port` |
| SQL Server | `mssql` | `mssql+pyodbc://user:pass@host:port/db?driver=...` |
| MongoDB | `mongo` | `mongodb://user:pass@host:port` |

## Configuration Options

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input-folder, -i` | Folder containing files to migrate | Required |
| `--engine, -e` | Database engine (postgres/mysql/mssql/mongo) | Required |
| `--connection, -c` | Database connection string | Required |
| `--db-name, -d` | Target database name | Required |
| `--batch-size, -b` | Batch size for data insertion | 1000 |
| `--overwrite-existing` | Drop and recreate existing tables | False |
| `--dry-run` | Preview mode without execution | False |
| `--preview` | Show data preview and schema only | False |
| `--log-level, -l` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `--clean-data` | Enable data cleaning | True |
| `--use-metadata-store` | Track imports with metadata | True |
| `--config-file` | JSON configuration file | None |
| `--output-format` | Output format (text/json) | text |

### Configuration File

Create a JSON configuration file to avoid repeating command line options:

```json
{
  "input_folder": "./data",
  "engine": "postgres",
  "connection": "postgresql+psycopg2://user:pass@localhost:5432",
  "db_name": "mydb",
  "batch_size": 2000,
  "clean_data": true,
  "infer_schema": true,
  "log_level": "INFO"
}
```

Use with: `migrate-data --config-file config.json`

## Schema Inference

DataMigrator automatically infers database schemas from your data:

- **INTEGER**: Whole numbers
- **NUMERIC**: Decimal numbers
- **VARCHAR**: Short text (< 255 chars)
- **TEXT**: Long text (≥ 255 chars)
- **BOOLEAN**: True/False values
- **DATE**: Date values (YYYY-MM-DD)
- **TIMESTAMP**: DateTime values

## Data Cleaning

Automatic data cleaning includes:

- Remove completely empty rows and columns
- Trim whitespace from string values
- Parse common date formats
- Handle missing values appropriately
- Custom transformation hooks

## Examples

### Basic Migration
```bash
migrate-data -i ./sales_data -e postgres \
  -c "postgresql+psycopg2://admin:secret@localhost:5432" \
  -d sales_db
```

### Advanced Migration with Options
```bash
migrate-data -i ./customer_data -e mysql \
  -c "mysql+pymysql://root:password@localhost:3306" \
  -d crm_db \
  --batch-size 5000 \
  --overwrite-existing \
  --log-level DEBUG
```

### MongoDB Migration
```bash
migrate-data -i ./analytics -e mongo \
  -c "mongodb://localhost:27017" \
  -d analytics_db \
  --batch-size 1000
```

### Preview Before Migration
```bash
# Analyze files first
migrate-data analyze -i ./data --output-format json

# Preview migration
migrate-data -i ./data -e postgres \
  -c "postgresql+psycopg2://user:pass@localhost:5432" \
  -d testdb --preview
```

## File Support

### CSV Files
- Automatic delimiter detection (comma, semicolon, tab, pipe)
- Encoding detection (UTF-8, ISO-8859-1, Windows-1252)
- Header row detection
- Large file support with chunked reading

### Excel Files
- Support for .xlsx and .xls formats
- Multi-sheet processing
- Automatic sheet naming for database tables
- Header row detection

## Error Handling

DataMigrator provides comprehensive error handling:

- File-level error isolation (one bad file doesn't stop the process)
- Detailed error logging with context
- Graceful handling of connection issues
- Data validation before insertion

## Performance

- **Batch Processing**: Configurable batch sizes for optimal performance
- **Connection Pooling**: Efficient database connection management
- **Memory Management**: Chunked reading for large files
- **Parallel Processing**: Multi-file processing capabilities

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black datamigrator/
flake8 datamigrator/
```

### Type Checking
```bash
mypy datamigrator/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@datamigrator.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/datamigrator/issues)
- 📖 Documentation: [Full Documentation](https://datamigrator.readthedocs.io)

## Changelog

### v0.1.0
- Initial release
- Support for PostgreSQL, MySQL, SQL Server, MongoDB
- Automatic schema inference
- Data cleaning capabilities
- CLI interface
- Batch processing
- Incremental synchronization 