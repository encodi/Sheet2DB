"""
Excel reader for DataMigrator

Implements Excel file reading with multi-sheet support for XLS and XLSX files.
"""

import pandas as pd
from typing import Union, Dict, List, Optional
from .base_reader import BaseReader
from ..utils.logger import get_logger


class ExcelReader(BaseReader):
    """
    Excel file reader with multi-sheet support.
    
    Features:
    - Support for both XLS and XLSX formats
    - Multi-sheet reading capabilities
    - Configurable sheet selection
    - Header row configuration
    - Data type handling
    """
    
    def __init__(self, filepath: str, **options):
        """
        Initialize Excel reader.
        
        Args:
            filepath: Path to the Excel file
            **options: Additional options:
                - sheet_name: Sheet name or list of sheets to read (None for all sheets)
                - engine: Excel engine to use ('openpyxl' for xlsx, 'xlrd' for xls)
                - header: Row number to use as column headers (default: 0)
                - skiprows: Number of rows to skip at the beginning
                - dtype: Data type specification (default: str for all columns)
                - na_values: Additional strings to recognize as NA/NaN
                - usecols: Columns to read (None for all columns)
        """
        super().__init__(filepath, **options)
        self.logger = get_logger(self.__class__.__name__)
        
        # Set default options
        self.sheet_name = options.get('sheet_name', None)  # None means all sheets
        self.engine = options.get('engine', None)  # Auto-detect if None
        self.header = options.get('header', 0)
        self.skiprows = options.get('skiprows', 0)
        self.dtype = options.get('dtype', str)  # Default to string
        self.na_values = options.get('na_values', [])
        self.usecols = options.get('usecols', None)
    
    def detect_engine(self) -> str:
        """
        Detect the appropriate engine based on file extension.
        
        Returns:
            Engine name ('openpyxl' or 'xlrd')
        """
        if self.engine:
            return self.engine
        
        file_info = self.get_file_info()
        extension = file_info['extension']
        
        if extension in ['.xlsx', '.xlsm']:
            return 'openpyxl'
        elif extension in ['.xls']:
            return 'xlrd'
        else:
            # Default to openpyxl for unknown extensions
            self.logger.warning(f"Unknown Excel extension {extension}, defaulting to openpyxl")
            return 'openpyxl'
    
    def get_sheet_names(self) -> List[str]:
        """
        Get all sheet names from the Excel file.
        
        Returns:
            List of sheet names
        """
        if not self.validate_file():
            raise FileNotFoundError(f"Excel file not found: {self.filepath}")
        
        engine = self.detect_engine()
        
        try:
            # Use ExcelFile to get sheet names without reading data
            with pd.ExcelFile(self.filepath, engine=engine) as excel_file:
                sheet_names = excel_file.sheet_names
            
            self.logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")
            return sheet_names
            
        except Exception as e:
            self.logger.error(f"Error reading Excel file sheet names: {e}")
            raise IOError(f"Failed to read sheet names from {self.filepath}: {e}")
    
    def read(self) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Read the Excel file.
        
        Returns:
            - Single DataFrame if only one sheet is read
            - Dictionary of DataFrames if multiple sheets are read
        """
        if not self.validate_file():
            raise FileNotFoundError(f"Excel file not found: {self.filepath}")
        
        engine = self.detect_engine()
        
        self.logger.info(f"Reading Excel file: {self.filepath}")
        self.logger.info(f"Using engine: {engine}")
        
        try:
            # Prepare pandas read_excel parameters
            read_params = {
                'io': self.filepath,
                'sheet_name': self.sheet_name,
                'engine': engine,
                'header': self.header,
                'skiprows': self.skiprows,
                'dtype': self.dtype,
                'na_values': self.na_values,
                'keep_default_na': False,
                'usecols': self.usecols
            }
            
            # Read the Excel file
            data = pd.read_excel(**read_params)
            
            if isinstance(data, dict):
                # Multiple sheets read
                self.logger.info(f"Successfully read {len(data)} sheets")
                for sheet_name, df in data.items():
                    self.logger.info(f"Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
                return data
            else:
                # Single sheet read
                self.logger.info(f"Successfully read Excel with {len(data)} rows and {len(data.columns)} columns")
                return data
                
        except Exception as e:
            self.logger.error(f"Error reading Excel file: {e}")
            raise IOError(f"Failed to read Excel file {self.filepath}: {e}")
    
    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        """
        Read a specific sheet from the Excel file.
        
        Args:
            sheet_name: Name of the sheet to read
            
        Returns:
            DataFrame containing the sheet data
        """
        if not self.validate_file():
            raise FileNotFoundError(f"Excel file not found: {self.filepath}")
        
        # Check if sheet exists
        available_sheets = self.get_sheet_names()
        if sheet_name not in available_sheets:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {available_sheets}")
        
        engine = self.detect_engine()
        
        try:
            df = pd.read_excel(
                io=self.filepath,
                sheet_name=sheet_name,
                engine=engine,
                header=self.header,
                skiprows=self.skiprows,
                dtype=self.dtype,
                na_values=self.na_values,
                keep_default_na=False,
                usecols=self.usecols
            )
            
            self.logger.info(f"Successfully read sheet '{sheet_name}' with {len(df)} rows and {len(df.columns)} columns")
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading sheet '{sheet_name}': {e}")
            raise IOError(f"Failed to read sheet '{sheet_name}' from {self.filepath}: {e}")
    
    def preview_sheet(self, sheet_name: str, nrows: int = 5) -> pd.DataFrame:
        """
        Preview the first few rows of a specific sheet.
        
        Args:
            sheet_name: Name of the sheet to preview
            nrows: Number of rows to preview
            
        Returns:
            DataFrame with the first nrows of the sheet
        """
        engine = self.detect_engine()
        
        try:
            df_preview = pd.read_excel(
                io=self.filepath,
                sheet_name=sheet_name,
                engine=engine,
                header=self.header,
                skiprows=self.skiprows,
                nrows=nrows,
                dtype=str,
                usecols=self.usecols
            )
            return df_preview
        except Exception as e:
            raise IOError(f"Failed to preview sheet '{sheet_name}' from {self.filepath}: {e}")
    
    def get_column_names(self, sheet_name: Optional[str] = None) -> Union[List[str], Dict[str, List[str]]]:
        """
        Get column names from Excel file.
        
        Args:
            sheet_name: Specific sheet name (None for all sheets)
            
        Returns:
            List of column names if sheet_name specified, 
            Dict of sheet_name -> column names if sheet_name is None
        """
        if sheet_name:
            preview_df = self.preview_sheet(sheet_name, nrows=1)
            return list(preview_df.columns)
        else:
            # Get columns for all sheets
            sheet_names = self.get_sheet_names()
            columns_dict = {}
            for sheet in sheet_names:
                try:
                    preview_df = self.preview_sheet(sheet, nrows=1)
                    columns_dict[sheet] = list(preview_df.columns)
                except Exception as e:
                    self.logger.warning(f"Could not get columns for sheet '{sheet}': {e}")
                    columns_dict[sheet] = []
            return columns_dict
    
    def get_sheet_info(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """
        Get information about all sheets in the Excel file.
        
        Returns:
            Dictionary with sheet information
        """
        sheet_names = self.get_sheet_names()
        sheet_info = {}
        
        for sheet_name in sheet_names:
            try:
                # Read just the first row to get basic info
                df = self.preview_sheet(sheet_name, nrows=1)
                sheet_info[sheet_name] = {
                    'columns': len(df.columns),
                    'column_names': list(df.columns)
                }
            except Exception as e:
                self.logger.warning(f"Could not get info for sheet '{sheet_name}': {e}")
                sheet_info[sheet_name] = {
                    'columns': 0,
                    'column_names': [],
                    'error': str(e)
                }
        
        return sheet_info 