"""
Data Loader Module
Handles loading and initial preprocessing of the Big Mac CSV file.
"""

import pandas as pd
from pathlib import Path


def load_bigmac_data(csv_path: str) -> pd.DataFrame:
    """
    Load Big Mac Index data from CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        DataFrame with parsed datetime and sorted data
    """
    # Load CSV file
    df = pd.read_csv(csv_path)
    
    # Parse date column as datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by country and date for better organization
    df = df.sort_values(['iso_a3', 'date']).reset_index(drop=True)
    
    return df


def get_data_path() -> str:
    """
    Get the path to the CSV file.
    Works from any directory when running the app.
    
    Returns:
        Absolute path to the CSV file
    """
    # Get the directory of this file (app folder)
    app_dir = Path(__file__).parent
    # Go up one level to project root, then into data folder
    csv_path = app_dir.parent / "data" / "big mac prices 2025.csv"
    return str(csv_path)
