"""
CSV reader for DataMigrator

Implements CSV file reading with automatic delimiter and encoding detection.
"""

import pandas as pd
import chardet
from typing import Union, Iterator, Optional, List
from .base_reader import BaseReader
from ..utils.logger import get_logger


class CSVReader(BaseReader):
    """
    CSV file reader with automatic delimiter and encoding detection.
    
    Features:
    - Automatic delimiter detection (comma, semicolon, tab)
    - Automatic encoding detection (UTF-8, ISO-8859-1, etc.)
    - Chunked reading support for large files
    - Configurable data type handling
    """
    
    COMMON_DELIMITERS = [',', ';', '\t', '|']
    COMMON_ENCODINGS = ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']
    
    def __init__(self, filepath: str, **options):
        """
        Initialize CSV reader.
        
        Args:
            filepath: Path to the CSV file
            **options: Additional options:
                - delimiter: Force specific delimiter (auto-detect if None)
                - encoding: Force specific encoding (auto-detect if None)
                - chunksize: Number of rows to read at a time (None for all)
                - dtype: Data type specification (default: str for all columns)
                - na_values: Additional strings to recognize as NA/NaN
                - skip_rows: Number of rows to skip at the beginning
                - header: Row number to use as column headers (default: 0)
        """
        super().__init__(filepath, **options)
        self.logger = get_logger(self.__class__.__name__)
        
        # Set default options
        self.delimiter = options.get('delimiter', None)
        self.encoding = options.get('encoding', None)
        self.chunksize = options.get('chunksize', None)
        self.dtype = options.get('dtype', str)  # Default to string to avoid type inference issues
        self.na_values = options.get('na_values', [])
        self.skip_rows = options.get('skip_rows', 0)
        self.header = options.get('header', 0)
    
    def detect_delimiter(self, sample_size: int = 1024) -> str:
        """
        Detect the delimiter used in the CSV file.
        
        Args:
            sample_size: Number of characters to read for detection
            
        Returns:
            Detected delimiter character
        """
        if self.delimiter:
            return self.delimiter
        
        # Read a sample of the file for delimiter detection
        encoding = self.encoding or self.detect_encoding()
        
        try:
            with open(self.filepath, 'r', encoding=encoding) as f:
                sample = f.read(sample_size)
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(sample_size)
        
        # Count occurrences of each delimiter
        delimiter_counts = {}
        for delimiter in self.COMMON_DELIMITERS:
            delimiter_counts[delimiter] = sample.count(delimiter)
        
        # Return the delimiter with the highest count
        detected_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        
        if delimiter_counts[detected_delimiter] == 0:
            self.logger.warning(f"No common delimiters found, defaulting to comma")
            detected_delimiter = ','
        
        self.logger.info(f"Detected delimiter: '{detected_delimiter}' (count: {delimiter_counts[detected_delimiter]})")
        return detected_delimiter
    
    def detect_encoding(self, sample_size: int = 10000) -> str:
        """
        Detect the encoding of the CSV file.
        
        Args:
            sample_size: Number of bytes to read for detection
            
        Returns:
            Detected encoding name
        """
        if self.encoding:
            return self.encoding
        
        # Read a sample of bytes for encoding detection
        with open(self.filepath, 'rb') as f:
            sample = f.read(sample_size)
        
        # Use chardet to detect encoding
        detection_result = chardet.detect(sample)
        detected_encoding = detection_result['encoding']
        confidence = detection_result['confidence']
        
        # Fallback to utf-8 if confidence is too low
        if confidence < 0.7:
            self.logger.warning(f"Low confidence ({confidence:.2f}) for detected encoding '{detected_encoding}', using utf-8")
            detected_encoding = 'utf-8'
        
        self.logger.info(f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
        return detected_encoding
    
    def read(self) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
        """
        Read the CSV file.
        
        Returns:
            DataFrame if chunksize is None, Iterator of DataFrames if chunksize is specified
        """
        if not self.validate_file():
            raise FileNotFoundError(f"CSV file not found: {self.filepath}")
        
        # Auto-detect delimiter and encoding
        delimiter = self.detect_delimiter()
        encoding = self.detect_encoding()
        
        self.logger.info(f"Reading CSV file: {self.filepath}")
        self.logger.info(f"Using delimiter: '{delimiter}', encoding: {encoding}")
        
        try:
            # Prepare pandas read_csv parameters
            read_params = {
                'filepath_or_buffer': self.filepath,
                'sep': delimiter,
                'encoding': encoding,
                'dtype': self.dtype,
                'header': self.header,
                'skiprows': self.skip_rows,
                'keep_default_na': False,  # Avoid automatic NA inference
                'na_values': self.na_values,
                'infer_datetime_format': True,
                'low_memory': False
            }
            
            # Add chunksize if specified
            if self.chunksize:
                read_params['chunksize'] = self.chunksize
                self.logger.info(f"Reading in chunks of {self.chunksize} rows")
                return pd.read_csv(**read_params)
            else:
                df = pd.read_csv(**read_params)
                self.logger.info(f"Successfully read CSV with {len(df)} rows and {len(df.columns)} columns")
                return df
                
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {e}")
            raise IOError(f"Failed to read CSV file {self.filepath}: {e}")
    
    def preview(self, nrows: int = 5) -> pd.DataFrame:
        """
        Preview the first few rows of the CSV file without loading the entire file.
        
        Args:
            nrows: Number of rows to preview
            
        Returns:
            DataFrame with the first nrows
        """
        delimiter = self.detect_delimiter()
        encoding = self.detect_encoding()
        
        try:
            df_preview = pd.read_csv(
                self.filepath,
                sep=delimiter,
                encoding=encoding,
                nrows=nrows,
                dtype=str,
                header=self.header,
                skiprows=self.skip_rows
            )
            return df_preview
        except Exception as e:
            raise IOError(f"Failed to preview CSV file {self.filepath}: {e}")
    
    def get_column_names(self) -> List[str]:
        """
        Get the column names from the CSV file.
        
        Returns:
            List of column names
        """
        preview_df = self.preview(nrows=1)
        return list(preview_df.columns) 