"""
Tests for the main Migrator class
"""

import pytest
import tempfile
import os
from pathlib import Path
import pandas as pd

from datamigrator.migrator import Migrator


class TestMigrator:
    """Test cases for the Migrator class."""
    
    def test_migrator_initialization(self):
        """Test that Migrator initializes correctly."""
        migrator = Migrator(
            input_folder="./test_data",
            engine="postgres",
            connection_string="postgresql+psycopg2://user:pass@localhost:5432",
            db_name="test_db"
        )
        
        assert migrator.input_folder == "./test_data"
        assert migrator.engine_name == "postgres"
        assert migrator.db_name == "test_db"
        assert migrator.batch_size == 1000  # default
        assert migrator.infer_schema is True  # default
    
    def test_migrator_with_options(self):
        """Test Migrator initialization with custom options."""
        options = {
            'batch_size': 5000,
            'clean_data': False,
            'infer_schema': False,
            'log_level': 'DEBUG'
        }
        
        migrator = Migrator(
            input_folder="./test_data",
            engine="mysql",
            connection_string="mysql+pymysql://user:pass@localhost:3306",
            db_name="test_db",
            options=options
        )
        
        assert migrator.batch_size == 5000
        assert migrator.clean_data is False
        assert migrator.infer_schema is False
    
    def test_unsupported_engine(self):
        """Test that unsupported engine raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported engine"):
            Migrator(
                input_folder="./test_data",
                engine="unsupported_db",
                connection_string="some://connection",
                db_name="test_db"
            )
    
    def test_supported_engines(self):
        """Test that all supported engines are recognized."""
        # Test engines that should always be available
        always_supported = ['postgres', 'mysql', 'mongo']
        
        for engine in always_supported:
            migrator = Migrator(
                input_folder="./test_data",
                engine=engine,
                connection_string="test://connection",
                db_name="test_db"
            )
            assert migrator.engine_name == engine
        
        # Test SQL Server if available
        try:
            migrator = Migrator(
                input_folder="./test_data",
                engine='mssql',
                connection_string="test://connection",
                db_name="test_db"
            )
            assert migrator.engine_name == 'mssql'
        except ValueError as e:
            # SQL Server support may not be available on all systems
            assert ("SQL Server support requires" in str(e) or 
                    "Unsupported engine: mssql" in str(e))
    
    def test_discover_files_empty_folder(self):
        """Test file discovery with empty folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            migrator = Migrator(
                input_folder=temp_dir,
                engine="postgres",
                connection_string="postgresql+psycopg2://user:pass@localhost:5432",
                db_name="test_db"
            )
            
            files = migrator._discover_files()
            assert files == []
    
    def test_discover_files_with_supported_files(self):
        """Test file discovery with supported file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            csv_file = Path(temp_dir) / "test.csv"
            xlsx_file = Path(temp_dir) / "test.xlsx"
            txt_file = Path(temp_dir) / "test.txt"  # unsupported
            
            csv_file.touch()
            xlsx_file.touch()
            txt_file.touch()
            
            migrator = Migrator(
                input_folder=temp_dir,
                engine="postgres",
                connection_string="postgresql+psycopg2://user:pass@localhost:5432",
                db_name="test_db"
            )
            
            files = migrator._discover_files()
            
            # Should find CSV and XLSX, but not TXT
            assert len(files) == 2
            assert any(f.endswith('.csv') for f in files)
            assert any(f.endswith('.xlsx') for f in files)
            assert not any(f.endswith('.txt') for f in files)
    
    def test_nonexistent_input_folder(self):
        """Test that nonexistent input folder raises FileNotFoundError."""
        migrator = Migrator(
            input_folder="/nonexistent/folder",
            engine="postgres",
            connection_string="postgresql+psycopg2://user:pass@localhost:5432",
            db_name="test_db"
        )
        
        with pytest.raises(FileNotFoundError):
            migrator._discover_files()


# Integration tests would require actual database connections
# These would typically be run in a separate test suite with test databases

class TestMigratorIntegration:
    """Integration tests for Migrator (require test databases)."""
    
    @pytest.mark.skip(reason="Requires test database setup")
    def test_full_migration_postgres(self):
        """Test complete migration to PostgreSQL."""
        # This would require a test PostgreSQL database
        pass
    
    @pytest.mark.skip(reason="Requires test database setup")
    def test_full_migration_mysql(self):
        """Test complete migration to MySQL."""
        # This would require a test MySQL database
        pass
    
    @pytest.mark.skip(reason="Requires test database setup")
    def test_full_migration_mongo(self):
        """Test complete migration to MongoDB."""
        # This would require a test MongoDB database
        pass 