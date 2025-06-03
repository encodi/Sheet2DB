"""
Base reader class for DataMigrator

Defines the abstract interface that all file readers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Union, Iterator
import pandas as pd


class BaseReader(ABC):
    """
    Abstract base class for file readers.
    
    All file readers must inherit from this class and implement the read() method.
    """
    
    def __init__(self, filepath: str, **options):
        """
        Initialize the reader.
        
        Args:
            filepath: Path to the file to read
            **options: Additional options specific to the reader implementation
        """
        self.filepath = filepath
        self.options = options
    
    @abstractmethod
    def read(self) -> Union[pd.DataFrame, Dict[str, pd.DataFrame], Iterator[pd.DataFrame]]:
        """
        Read the file and return the data.
        
        Returns:
            - Single DataFrame for simple files
            - Dict of DataFrames for multi-sheet files (Excel)
            - Iterator of DataFrames for chunked reading
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid or unsupported
            IOError: If there's an error reading the file
        """
        pass
    
    def validate_file(self) -> bool:
        """
        Validate that the file exists and is readable.
        
        Returns:
            True if file is valid, False otherwise
        """
        import os
        return os.path.exists(self.filepath) and os.path.isfile(self.filepath)
    
    def get_file_info(self) -> Dict[str, Union[str, int]]:
        """
        Get basic information about the file.
        
        Returns:
            Dictionary with file information (name, size, etc.)
        """
        import os
        from pathlib import Path
        
        if not self.validate_file():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        file_path = Path(self.filepath)
        file_size = os.path.getsize(self.filepath)
        
        return {
            'filename': file_path.name,
            'filepath': str(file_path.absolute()),
            'size_bytes': file_size,
            'extension': file_path.suffix.lower()
        } 