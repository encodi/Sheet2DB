"""
Data cleaner for DataMigrator

Provides data cleaning and transformation functionality before database insertion.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from ..utils.logger import get_logger


class DataCleaner:
    """
    Data cleaning and transformation engine.
    
    Features:
    - Remove empty columns and rows
    - Clean string data (trim whitespace, handle empty strings)
    - Date parsing and standardization
    - Numeric data cleaning
    - Custom transformation hooks
    """
    
    def __init__(self, **options):
        """
        Initialize data cleaner.
        
        Args:
            **options: Configuration options:
                - remove_empty_columns: Remove columns with all null values (default: True)
                - remove_empty_rows: Remove rows with all null values (default: True)
                - trim_strings: Trim whitespace from string columns (default: True)
                - empty_string_to_null: Convert empty strings to None (default: True)
                - parse_dates: Attempt to parse date columns (default: True)
                - date_formats: List of date formats to try (default: common formats)
                - custom_transformations: Dict of column_name -> transformation_function
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Configuration options
        self.remove_empty_columns = options.get('remove_empty_columns', True)
        self.remove_empty_rows = options.get('remove_empty_rows', True)
        self.trim_strings = options.get('trim_strings', True)
        self.empty_string_to_null = options.get('empty_string_to_null', True)
        self.parse_dates = options.get('parse_dates', True)
        self.date_formats = options.get('date_formats', [
            '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d/%m/%Y',
            '%m/%d/%Y', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'
        ])
        self.custom_transformations = options.get('custom_transformations', {})
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the DataFrame using configured cleaning rules.
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            self.logger.warning("DataFrame is empty, nothing to clean")
            return df
        
        self.logger.info(f"Cleaning DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Make a copy to avoid modifying the original
        cleaned_df = df.copy()
        
        # Apply cleaning steps in order
        cleaned_df = self._remove_empty_columns(cleaned_df)
        cleaned_df = self._remove_empty_rows(cleaned_df)
        cleaned_df = self._clean_string_columns(cleaned_df)
        cleaned_df = self._parse_date_columns(cleaned_df)
        cleaned_df = self._apply_custom_transformations(cleaned_df)
        
        self.logger.info(f"Cleaning complete. Result: {len(cleaned_df)} rows and {len(cleaned_df.columns)} columns")
        
        return cleaned_df
    
    def _remove_empty_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove columns that are entirely empty."""
        if not self.remove_empty_columns:
            return df
        
        initial_columns = len(df.columns)
        
        # Find columns with all null values
        empty_columns = df.columns[df.isnull().all()].tolist()
        
        if empty_columns:
            self.logger.info(f"Removing {len(empty_columns)} empty columns: {empty_columns}")
            df = df.drop(columns=empty_columns)
        
        removed_count = initial_columns - len(df.columns)
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} empty columns")
        
        return df
    
    def _remove_empty_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows that are entirely empty."""
        if not self.remove_empty_rows:
            return df
        
        initial_rows = len(df)
        
        # Remove rows where all values are null
        df = df.dropna(how='all')
        
        removed_count = initial_rows - len(df)
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} empty rows")
        
        return df
    
    def _clean_string_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean string columns by trimming whitespace and handling empty strings."""
        if not (self.trim_strings or self.empty_string_to_null):
            return df
        
        string_columns = df.select_dtypes(include=['object']).columns
        
        for col in string_columns:
            if self.trim_strings:
                # Trim whitespace from string values
                df[col] = df[col].astype(str).str.strip()
            
            if self.empty_string_to_null:
                # Convert empty strings to None
                df[col] = df[col].replace(['', 'nan', 'NaN', 'null', 'NULL'], None)
        
        if len(string_columns) > 0:
            self.logger.debug(f"Cleaned {len(string_columns)} string columns")
        
        return df
    
    def _parse_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attempt to parse date columns."""
        if not self.parse_dates:
            return df
        
        # Try to identify potential date columns
        potential_date_columns = []
        
        for col in df.columns:
            # Skip if column is already datetime
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            
            # Check if column name suggests it's a date
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'time', 'created', 'updated', 'modified']):
                potential_date_columns.append(col)
                continue
            
            # Sample some values to see if they look like dates
            sample_values = df[col].dropna().astype(str).head(10)
            if len(sample_values) > 0:
                # Simple heuristic: check if values contain date-like patterns
                date_like_count = 0
                for value in sample_values:
                    if any(char in value for char in ['-', '/', ':']):
                        # Try to parse with pandas
                        try:
                            pd.to_datetime(value, errors='raise')
                            date_like_count += 1
                        except:
                            pass
                
                # If most values look like dates, consider it a date column
                if date_like_count / len(sample_values) > 0.7:
                    potential_date_columns.append(col)
        
        # Parse identified date columns
        for col in potential_date_columns:
            try:
                # Try pandas auto-parsing first
                parsed_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
                
                # If auto-parsing didn't work well, try specific formats
                if parsed_series.isna().sum() / len(parsed_series) > 0.5:
                    for date_format in self.date_formats:
                        try:
                            parsed_series = pd.to_datetime(df[col], format=date_format, errors='coerce')
                            if parsed_series.isna().sum() / len(parsed_series) <= 0.5:
                                break
                        except:
                            continue
                
                # Only replace if parsing was successful for most values
                if parsed_series.isna().sum() / len(parsed_series) <= 0.5:
                    df[col] = parsed_series
                    self.logger.debug(f"Parsed date column: {col}")
                
            except Exception as e:
                self.logger.warning(f"Could not parse date column '{col}': {e}")
        
        if potential_date_columns:
            self.logger.info(f"Processed {len(potential_date_columns)} potential date columns")
        
        return df
    
    def _apply_custom_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply custom transformations defined by the user."""
        if not self.custom_transformations:
            return df
        
        for col_name, transformation_func in self.custom_transformations.items():
            if col_name in df.columns:
                try:
                    df[col_name] = transformation_func(df[col_name])
                    self.logger.debug(f"Applied custom transformation to column: {col_name}")
                except Exception as e:
                    self.logger.warning(f"Custom transformation failed for column '{col_name}': {e}")
        
        return df
    
    def add_custom_transformation(self, column_name: str, transformation_func: Callable) -> None:
        """
        Add a custom transformation for a specific column.
        
        Args:
            column_name: Name of the column to transform
            transformation_func: Function that takes a pandas Series and returns a transformed Series
        """
        self.custom_transformations[column_name] = transformation_func
        self.logger.info(f"Added custom transformation for column: {column_name}")
    
    def get_cleaning_summary(self, original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get a summary of the cleaning operations performed.
        
        Args:
            original_df: Original DataFrame before cleaning
            cleaned_df: DataFrame after cleaning
            
        Returns:
            Dictionary with cleaning summary statistics
        """
        return {
            'original_shape': original_df.shape,
            'cleaned_shape': cleaned_df.shape,
            'rows_removed': len(original_df) - len(cleaned_df),
            'columns_removed': len(original_df.columns) - len(cleaned_df.columns),
            'null_values_before': original_df.isnull().sum().sum(),
            'null_values_after': cleaned_df.isnull().sum().sum(),
            'memory_usage_before': original_df.memory_usage(deep=True).sum(),
            'memory_usage_after': cleaned_df.memory_usage(deep=True).sum()
        } 