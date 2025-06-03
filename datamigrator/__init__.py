"""
DataMigrator - Automated CSV and Excel to Database Migration Tool

A Python library that automates the ingestion of CSV and Excel files 
into SQL and NoSQL databases (PostgreSQL, MySQL, SQL Server, MongoDB).
"""

__version__ = "0.1.0"
__author__ = "DataMigrator Team"

from .migrator import Migrator
from .readers.csv_reader import CSVReader
from .readers.excel_reader import ExcelReader
from .schema_inference.inferrer import SchemaInferrer
from .transformers.data_cleaner import DataCleaner

__all__ = [
    "Migrator",
    "CSVReader", 
    "ExcelReader",
    "SchemaInferrer",
    "DataCleaner",
] 