"""
Engine Adapters package - Database connectivity for DataMigrator

Contains adapters for different database systems:
- PostgreSQL
- MySQL
- SQL Server  
- MongoDB
"""

from .base_adapter import BaseAdapter
from .postgres_adapter import PostgresAdapter
from .mysql_adapter import MySQLAdapter
from .mongo_adapter import MongoAdapter

# Import SQL Server adapter with error handling for missing dependencies
try:
    from .mssql_adapter import MSSQLAdapter
    HAS_MSSQL = True
except ImportError:
    MSSQLAdapter = None
    HAS_MSSQL = False

__all__ = [
    "BaseAdapter",
    "PostgresAdapter", 
    "MySQLAdapter",
    "MongoAdapter"
]

if HAS_MSSQL:
    __all__.append("MSSQLAdapter") 