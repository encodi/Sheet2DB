"""
Schema Inference package - Automatic schema detection for DataMigrator

Contains tools for inferring database schemas from pandas DataFrames.
"""

from .inferrer import SchemaInferrer, ColumnSchema

__all__ = ["SchemaInferrer", "ColumnSchema"] 