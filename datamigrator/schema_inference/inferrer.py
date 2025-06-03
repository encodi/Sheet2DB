"""
Schema inference for DataMigrator

Automatically infers database schemas from pandas DataFrames.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Any
from ..utils.logger import get_logger


@dataclass
class ColumnSchema:
    """
    Represents the schema information for a single column.
    """
    name: str
    sql_type: str
    nullable: bool = True
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    unique: bool = False
    
    def __str__(self) -> str:
        type_str = self.sql_type
        if self.max_length:
            type_str = f"{self.sql_type}({self.max_length})"
        elif self.precision and self.scale is not None:
            type_str = f"{self.sql_type}({self.precision},{self.scale})"
        elif self.precision:
            type_str = f"{self.sql_type}({self.precision})"
        
        nullable_str = "NULL" if self.nullable else "NOT NULL"
        return f"{self.name} {type_str} {nullable_str}"


class SchemaInferrer:
    """
    Schema inference engine that analyzes pandas DataFrames and infers SQL types.
    
    Features:
    - Type inference for common SQL types
    - Nullable column detection
    - String length analysis
    - Numeric precision and scale detection
    - Date/timestamp detection
    - Boolean type detection
    """
    
    def __init__(self, **options):
        """
        Initialize schema inferrer.
        
        Args:
            **options: Configuration options:
                - sample_size: Number of rows to sample for analysis (None for all)
                - varchar_threshold: Threshold for VARCHAR vs TEXT (default: 255)
                - decimal_precision: Default decimal precision (default: 10)
                - decimal_scale: Default decimal scale (default: 2)
                - date_formats: List of date formats to try parsing
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Configuration options
        self.sample_size = options.get('sample_size', None)
        self.varchar_threshold = options.get('varchar_threshold', 255)
        self.decimal_precision = options.get('decimal_precision', 10)
        self.decimal_scale = options.get('decimal_scale', 2)
        self.date_formats = options.get('date_formats', [
            '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d/%m/%Y',
            '%m/%d/%Y', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'
        ])
    
    def _sample_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sample the DataFrame if sample_size is specified.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Sampled DataFrame
        """
        if self.sample_size and len(df) > self.sample_size:
            return df.sample(n=self.sample_size, random_state=42)
        return df
    
    def _infer_column_type(self, series: pd.Series) -> ColumnSchema:
        """
        Infer the SQL type for a single column.
        
        Args:
            series: Pandas Series to analyze
            
        Returns:
            ColumnSchema with inferred type information
        """
        column_name = series.name
        self.logger.debug(f"Inferring type for column: {column_name}")
        
        # Remove null values for analysis
        non_null_series = series.dropna()
        
        # Check if column is entirely null
        if len(non_null_series) == 0:
            return ColumnSchema(
                name=column_name,
                sql_type="VARCHAR",
                max_length=255,
                nullable=True
            )
        
        # Check nullable
        nullable = len(non_null_series) < len(series)
        
        # Try to infer type based on data
        schema = self._analyze_column_data(column_name, non_null_series, nullable)
        
        self.logger.debug(f"Inferred type for {column_name}: {schema.sql_type}")
        return schema
    
    def _analyze_column_data(self, column_name: str, series: pd.Series, nullable: bool) -> ColumnSchema:
        """
        Analyze the actual data to infer the best SQL type.
        
        Args:
            column_name: Name of the column
            series: Non-null pandas Series
            nullable: Whether the column contains null values
            
        Returns:
            ColumnSchema with inferred information
        """
        # Convert all values to string for initial analysis
        str_series = series.astype(str)
        
        # Check for boolean values
        if self._is_boolean_column(str_series):
            return ColumnSchema(
                name=column_name,
                sql_type="BOOLEAN",
                nullable=nullable
            )
        
        # Check for integer values
        if self._is_integer_column(str_series):
            return ColumnSchema(
                name=column_name,
                sql_type="INTEGER",
                nullable=nullable
            )
        
        # Check for numeric values (decimal)
        numeric_info = self._analyze_numeric_column(str_series)
        if numeric_info:
            return ColumnSchema(
                name=column_name,
                sql_type="NUMERIC",
                precision=numeric_info['precision'],
                scale=numeric_info['scale'],
                nullable=nullable
            )
        
        # Check for date/timestamp values
        date_type = self._analyze_date_column(str_series)
        if date_type:
            return ColumnSchema(
                name=column_name,
                sql_type=date_type,
                nullable=nullable
            )
        
        # Default to string type (VARCHAR or TEXT)
        max_length = str_series.str.len().max()
        
        if max_length <= self.varchar_threshold:
            return ColumnSchema(
                name=column_name,
                sql_type="VARCHAR",
                max_length=max(max_length, 1),  # At least 1 character
                nullable=nullable
            )
        else:
            return ColumnSchema(
                name=column_name,
                sql_type="TEXT",
                nullable=nullable
            )
    
    def _is_boolean_column(self, series: pd.Series) -> bool:
        """Check if a column contains boolean values."""
        unique_values = set(series.str.lower().unique())
        boolean_values = {
            'true', 'false', '1', '0', 'yes', 'no', 'y', 'n',
            't', 'f', 'on', 'off', 'enabled', 'disabled'
        }
        return unique_values.issubset(boolean_values)
    
    def _is_integer_column(self, series: pd.Series) -> bool:
        """Check if a column contains integer values."""
        try:
            # Try to convert to numeric
            numeric_series = pd.to_numeric(series, errors='coerce')
            
            # Check if all values were successfully converted
            if numeric_series.isna().any():
                return False
            
            # Check if all values are integers (no decimal part)
            return all(float(x).is_integer() for x in numeric_series if not pd.isna(x))
        except:
            return False
    
    def _analyze_numeric_column(self, series: pd.Series) -> Optional[Dict[str, int]]:
        """Analyze numeric column to determine precision and scale."""
        try:
            numeric_series = pd.to_numeric(series, errors='coerce')
            
            # Check if all values were successfully converted
            if numeric_series.isna().any():
                return None
            
            # Calculate precision and scale
            max_precision = 0
            max_scale = 0
            
            for value in numeric_series:
                if pd.isna(value):
                    continue
                
                # Convert to string to analyze decimal places
                str_value = str(float(value))
                
                if 'e' in str_value.lower():
                    # Scientific notation - skip for now
                    continue
                
                if '.' in str_value:
                    integer_part, decimal_part = str_value.split('.')
                    precision = len(integer_part.lstrip('-')) + len(decimal_part.rstrip('0'))
                    scale = len(decimal_part.rstrip('0'))
                else:
                    precision = len(str_value.lstrip('-'))
                    scale = 0
                
                max_precision = max(max_precision, precision)
                max_scale = max(max_scale, scale)
            
            # Use default values if calculated values are too small
            max_precision = max(max_precision, self.decimal_precision)
            max_scale = max(max_scale, 0)  # Scale can be 0
            
            return {'precision': max_precision, 'scale': max_scale}
            
        except:
            return None
    
    def _analyze_date_column(self, series: pd.Series) -> Optional[str]:
        """Analyze if column contains date/datetime values."""
        # Try to parse dates with various formats
        for date_format in self.date_formats:
            try:
                parsed_dates = pd.to_datetime(series, format=date_format, errors='coerce')
                
                # If most values parsed successfully, it's likely a date column
                success_rate = (len(parsed_dates.dropna()) / len(series))
                if success_rate > 0.8:  # 80% success rate threshold
                    # Determine if it's DATE or TIMESTAMP based on time component
                    sample_dates = parsed_dates.dropna().head(10)
                    has_time = any(d.time() != pd.Timestamp('00:00:00').time() for d in sample_dates)
                    
                    return "TIMESTAMP" if has_time else "DATE"
            except:
                continue
        
        # Try pandas auto-parsing as last resort
        try:
            parsed_dates = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
            success_rate = (len(parsed_dates.dropna()) / len(series))
            
            if success_rate > 0.8:
                sample_dates = parsed_dates.dropna().head(10)
                has_time = any(d.time() != pd.Timestamp('00:00:00').time() for d in sample_dates)
                return "TIMESTAMP" if has_time else "DATE"
        except:
            pass
        
        return None
    
    def infer_schema(self, df: pd.DataFrame) -> List[ColumnSchema]:
        """
        Infer schema for a single DataFrame.
        
        Args:
            df: pandas DataFrame to analyze
            
        Returns:
            List of ColumnSchema objects
        """
        self.logger.info(f"Inferring schema for DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Sample the DataFrame if needed
        sample_df = self._sample_dataframe(df)
        
        schemas = []
        for column in df.columns:
            try:
                column_schema = self._infer_column_type(sample_df[column])
                schemas.append(column_schema)
            except Exception as e:
                self.logger.warning(f"Error inferring type for column '{column}': {e}")
                # Default to VARCHAR for problematic columns
                schemas.append(ColumnSchema(
                    name=column,
                    sql_type="VARCHAR",
                    max_length=255,
                    nullable=True
                ))
        
        self.logger.info(f"Successfully inferred schema for {len(schemas)} columns")
        return schemas
    
    def infer_schemas_all(self, sheets: Dict[str, pd.DataFrame]) -> Dict[str, List[ColumnSchema]]:
        """
        Infer schemas for multiple DataFrames (e.g., Excel sheets).
        
        Args:
            sheets: Dictionary of sheet_name -> DataFrame
            
        Returns:
            Dictionary of sheet_name -> List[ColumnSchema]
        """
        self.logger.info(f"Inferring schemas for {len(sheets)} sheets/tables")
        
        all_schemas = {}
        for sheet_name, df in sheets.items():
            try:
                self.logger.info(f"Processing sheet: {sheet_name}")
                schema = self.infer_schema(df)
                all_schemas[sheet_name] = schema
            except Exception as e:
                self.logger.error(f"Error inferring schema for sheet '{sheet_name}': {e}")
                all_schemas[sheet_name] = []
        
        return all_schemas 