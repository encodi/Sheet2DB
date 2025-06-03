"""
File utilities for DataMigrator

Provides file operation utilities like hash calculation and file discovery.
"""

import hashlib
import os
from pathlib import Path
from typing import List


def calculate_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """
    Calculate SHA-256 hash of a file.
    
    Args:
        filepath: Path to the file
        chunk_size: Size of chunks to read at a time (for large files)
        
    Returns:
        Hexadecimal hash string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there's an error reading the file
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    hash_obj = hashlib.sha256()
    
    try:
        with open(filepath, 'rb') as f:
            # Read the file in chunks to handle large files efficiently
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
    except IOError as e:
        raise IOError(f"Error reading file {filepath}: {e}")
    
    return hash_obj.hexdigest()


def list_input_files(folder: str, extensions: List[str]) -> List[str]:
    """
    List all files in a folder with specified extensions.
    
    Args:
        folder: Path to the folder to search
        extensions: List of file extensions to include (e.g., ['.csv', '.xlsx'])
        
    Returns:
        List of file paths
        
    Raises:
        FileNotFoundError: If the folder doesn't exist
    """
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")
    
    if not os.path.isdir(folder):
        raise ValueError(f"Path is not a directory: {folder}")
    
    # Normalize extensions to lowercase
    extensions = [ext.lower() for ext in extensions]
    
    files = []
    folder_path = Path(folder)
    
    # Walk through all files in the directory and subdirectories
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            # Check if file extension matches any of the target extensions
            file_ext = file_path.suffix.lower()
            if file_ext in extensions:
                files.append(str(file_path.absolute()))
    
    # Sort files for consistent ordering
    files.sort()
    
    return files


def get_file_size(filepath: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        filepath: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    return os.path.getsize(filepath)


def ensure_directory(directory: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
    """
    Path(directory).mkdir(parents=True, exist_ok=True) 