"""
Data Transformation Module
Handles creating derived metrics from Big Mac data.
"""

import pandas as pd
import numpy as np


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calculated metrics to the Big Mac data.
    
    Metrics added:
    - price_change_pct: Year-over-year % change in dollar price per country
    - bm_gdp_ratio: Big Mac price as a ratio of GDP per capita (in dollars)
    - rolling_avg_3: 3-period rolling average of dollar price per country
    
    Args:
        df: Input DataFrame with Big Mac data
        
    Returns:
        DataFrame with new columns for derived metrics
    """
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Initialize new columns with NaN
    df['price_change_pct'] = np.nan
    df['bm_gdp_ratio'] = np.nan
    df['rolling_avg_3'] = np.nan
    
    # Calculate metrics per country
    for country in df['iso_a3'].unique():
        # Filter data for this country
        country_mask = df['iso_a3'] == country
        country_data = df[country_mask].copy()
        country_data = country_data.sort_values('date').reset_index(drop=True)
        
        # 1. Year-over-year price change (%)
        # Compare price to same time last year
        price_change = calculate_yoy_change(country_data)
        df.loc[country_mask, 'price_change_pct'] = price_change.values
        
        # 2. Big Mac to GDP ratio
        # Dollar price divided by GDP per capita (in dollars)
        # Safely divide, handling zero values
        gdp_ratio = country_data['dollar_price'] / country_data['GDP_dollar']
        gdp_ratio = gdp_ratio.replace([np.inf, -np.inf], np.nan)
        df.loc[country_mask, 'bm_gdp_ratio'] = gdp_ratio.values
        
        # 3. Rolling 3-period average of dollar price
        # Smooth out short-term fluctuations
        rolling_avg = country_data['dollar_price'].rolling(
            window=3, 
            center=False,
            min_periods=1
        ).mean()
        df.loc[country_mask, 'rolling_avg_3'] = rolling_avg.values
    
    return df


def calculate_yoy_change(country_df: pd.DataFrame) -> pd.Series:
    """
    Calculate year-over-year percentage change in dollar price.
    
    Compares each price to the price from ~1 year ago (any recorded date ~12 months prior).
    
    Args:
        country_df: DataFrame for a single country, sorted by date
        
    Returns:
        Series with YoY percentage change (NaN where previous year data doesn't exist)
    """
    price_change_pct = pd.Series(np.nan, index=country_df.index)
    
    # Create a date-to-price mapping
    date_price_map = dict(zip(country_df['date'], country_df['dollar_price'].values))
    
    for idx, row in country_df.iterrows():
        current_date = row['date']
        current_price = row['dollar_price']
        
        # Look for a price approximately 1 year ago (within 120-400 days)
        # This handles both 6-month and yearly data
        one_year_ago_min = pd.Timestamp(current_date.year - 1, current_date.month, 1)
        one_year_ago_max = pd.Timestamp(current_date.year - 1, 
                                        min(12, current_date.month + 2), 1)
        
        # Find matching previous year entries
        previous_prices = [
            price for date, price in date_price_map.items()
            if one_year_ago_min <= date <= one_year_ago_max
        ]
        
        if previous_prices:
            # Use the first matching previous year price
            previous_price = previous_prices[0]
            if previous_price > 0:
                yoy_change = ((current_price - previous_price) / previous_price) * 100
                price_change_pct[idx] = yoy_change
    
    return price_change_pct


def get_price_trend(price_change_pct: float) -> str:
    """
    Interpret price trend based on year-over-year change percentage.
    
    Args:
        price_change_pct: Percentage change in price
        
    Returns:
        Simple interpretation string
    """
    if pd.isna(price_change_pct):
        return "No trend data"
    
    if price_change_pct > 2:
        return "Increasing"
    elif price_change_pct < -2:
        return "Decreasing"
    else:
        return "Stable"


def calculate_rolling_trend(country_df: pd.DataFrame, window: int = 3) -> pd.Series:
    """
    Calculate rolling trend slope for the given window.

    Args:
        country_df: DataFrame for a single country sorted by date
        window: number of records to use for trend window
    """
    prices = country_df['dollar_price'].astype(float)
    # No regression package needed: slope via differences
    trend_scores = pd.Series(np.nan, index=country_df.index)

    for i in range(window - 1, len(prices)):
        segment = prices.iloc[i - window + 1:i + 1]
        days = (country_df['date'].iloc[i] - country_df['date'].iloc[i - window + 1]).days
        if days <= 0:
            trend_scores.iloc[i] = np.nan
            continue
        price_diff = segment.iloc[-1] - segment.iloc[0]
        trend_scores.iloc[i] = price_diff / max(days, 1)

    return trend_scores


def detect_alerts(latest_row: pd.Series, recent_rows: pd.DataFrame) -> list:
    """
    Detect simple alert conditions in country data.

    Conditions:
    - YoY change > 10% (or < -10%)
    - Rolling average volatility (std) in recent window > threshold
    """
    alerts = []

    if pd.notna(latest_row.get('price_change_pct')):
        if latest_row['price_change_pct'] > 10:
            alerts.append('Large YoY increase > 10%')
        elif latest_row['price_change_pct'] < -10:
            alerts.append('Large YoY decrease > 10%')

    if len(recent_rows) >= 3:
        vol = recent_rows['dollar_price'].std()
        if pd.notna(vol) and vol / recent_rows['dollar_price'].mean() > 0.1:
            alerts.append('High recent volatility')

    if not alerts:
        alerts.append('No alerts')

    return alerts

