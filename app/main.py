"""
Big Mac Index API
A simple FastAPI application serving Big Mac price data and analysis.
"""

from fastapi import FastAPI, HTTPException
import pandas as pd

from .data_loader import load_bigmac_data, get_data_path
from .transform import add_derived_metrics, get_price_trend, calculate_rolling_trend, detect_alerts

app = FastAPI(
    title="Big Mac Index API",
    description="Serving and analyzing Big Mac price data across countries",
    version="1.0.0"
)

csv_path = get_data_path()
df = load_bigmac_data(csv_path)
df = add_derived_metrics(df)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Big Mac Index API!",
        "description": "Get Big Mac price data and insights for different countries",
        "endpoints": {
            "country": "/country/{iso}",
            "history": "/history/{iso}",
            "insight": "/insight/{iso}",
            "countries": "/countries",
            "search": "/search?term=...",
            "compare": "/compare/{iso1}/{iso2}",
            "trend": "/trend/{iso}?window=...",
            "alerts": "/alerts/{iso}",
            "reload": "/reload"
        }
    }


@app.get("/country/{iso}")
def get_country_latest(iso: str):
    country_data = df[df['iso_a3'] == iso.upper()]
    if country_data.empty:
        raise HTTPException(status_code=404, detail=f"Country with ISO code '{iso}' not found")
    latest = country_data.nlargest(1, 'date').iloc[0]
    return {
        "country": latest['name'],
        "iso_a3": latest['iso_a3'],
        "currency_code": latest['currency_code'],
        "date": latest['date'].strftime('%Y-%m-%d'),
        "local_price": float(latest['local_price']),
        "dollar_price": float(latest['dollar_price']),
        "dollar_ex": float(latest['dollar_ex']),
        "GDP_dollar": float(latest['GDP_dollar'])
    }


@app.get("/history/{iso}")
def get_country_history(iso: str):
    country_data = df[df['iso_a3'] == iso.upper()].sort_values('date')
    if country_data.empty:
        raise HTTPException(status_code=404, detail=f"Country with ISO code '{iso}' not found")
    history = []
    for _, row in country_data.iterrows():
        history.append({
            "date": row['date'].strftime('%Y-%m-%d'),
            "local_price": float(row['local_price']),
            "dollar_price": float(row['dollar_price']),
            "dollar_ex": float(row['dollar_ex']),
            "GDP_dollar": float(row['GDP_dollar']),
            "price_change_pct": float(row['price_change_pct']) if pd.notna(row['price_change_pct']) else None,
            "bm_gdp_ratio": float(row['bm_gdp_ratio']) if pd.notna(row['bm_gdp_ratio']) else None,
            "rolling_avg_3": float(row['rolling_avg_3']) if pd.notna(row['rolling_avg_3']) else None
        })
    return {
        "country": country_data.iloc[0]['name'],
        "iso_a3": iso.upper(),
        "data_points": len(history),
        "history": history
    }


@app.get("/insight/{iso}")
def get_country_insight(iso: str):
    country_data = df[df['iso_a3'] == iso.upper()]
    if country_data.empty:
        raise HTTPException(status_code=404, detail=f"Country with ISO code '{iso}' not found")
    latest = country_data.nlargest(1, 'date').iloc[0]
    price_change = latest['price_change_pct']
    trend = get_price_trend(price_change)
    factors = []
    if pd.notna(price_change):
        if price_change > 5:
            factors.append('Strong year-over-year increase')
        elif price_change < -5:
            factors.append('Strong year-over-year decrease')
        else:
            factors.append('Moderate year-over-year movement')
    factors.append(f"BMI to GDP ratio is {latest['bm_gdp_ratio']:.6f}" if pd.notna(latest['bm_gdp_ratio']) else 'BMI/GDP ratio unavailable')
    explanation = (
        f"Latest price is {float(latest['dollar_price']):.2f} USD. Trend is {trend.lower()}. "
        f"Year-over-year change is {float(price_change):.2f}%" if pd.notna(price_change) else "Trend data unavailable"
    )
    return {
        "country": latest['name'],
        "iso_a3": latest['iso_a3'],
        "currency_code": latest['currency_code'],
        "date": latest['date'].strftime('%Y-%m-%d'),
        "latest_price": float(latest['dollar_price']),
        "price_change_pct": float(price_change) if pd.notna(price_change) else None,
        "bm_gdp_ratio": float(latest['bm_gdp_ratio']) if pd.notna(latest['bm_gdp_ratio']) else None,
        "rolling_avg_3": float(latest['rolling_avg_3']) if pd.notna(latest['rolling_avg_3']) else None,
        "trend": trend,
        "interpretation": f"The Big Mac price is {trend.lower()} in {latest['name']}.",
        "key_factors": factors,
        "explanation": explanation
    }


@app.get("/countries")
def list_countries():
    countries = df[['name', 'iso_a3']].drop_duplicates().sort_values('iso_a3')
    return {
        "total_countries": len(countries),
        "countries": [{"name": row['name'], "iso_a3": row['iso_a3']} for _, row in countries.iterrows()]
    }


@app.get("/search")
def search_countries(term: str):
    filtered = df[df['name'].str.contains(term, case=False, na=False) | df['currency_code'].str.contains(term, case=False, na=False)]
    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"No results for '{term}'")
    return filtered[['name', 'iso_a3', 'currency_code']].drop_duplicates().to_dict(orient='records')


@app.get("/compare/{iso1}/{iso2}")
def compare_countries(iso1: str, iso2: str):
    def latest_values(iso):
        c = df[df['iso_a3'] == iso.upper()]
        if c.empty:
            raise HTTPException(status_code=404, detail=f"{iso} not found")
        r = c.nlargest(1, 'date').iloc[0]
        return {
            'iso_a3': r['iso_a3'],
            'country': r['name'],
            'date': r['date'].strftime('%Y-%m-%d'),
            'dollar_price': float(r['dollar_price']),
            'price_change_pct': float(r['price_change_pct']) if pd.notna(r['price_change_pct']) else None,
            'bm_gdp_ratio': float(r['bm_gdp_ratio']) if pd.notna(r['bm_gdp_ratio']) else None,
            'rolling_avg_3': float(r['rolling_avg_3']) if pd.notna(r['rolling_avg_3']) else None,
        }
    return {'left': latest_values(iso1), 'right': latest_values(iso2)}


@app.get("/trend/{iso}")
def country_trend(iso: str, window: int = 3):
    country_data = df[df['iso_a3'] == iso.upper()].sort_values('date')
    if country_data.empty:
        raise HTTPException(status_code=404, detail=f"{iso} not found")
    slopes = calculate_rolling_trend(country_data, window=window)
    result = []
    for i, r in country_data.iterrows():
        result.append({'date': r['date'].strftime('%Y-%m-%d'), 'dollar_price': float(r['dollar_price']), 'rolling_slope': float(slopes.loc[i]) if pd.notna(slopes.loc[i]) else None})
    return {'iso_a3': iso.upper(), 'window': window, 'trend': result}


@app.get("/alerts/{iso}")
def country_alerts(iso: str):
    country_data = df[df['iso_a3'] == iso.upper()].sort_values('date')
    if country_data.empty:
        raise HTTPException(status_code=404, detail=f"{iso} not found")
    latest = country_data.iloc[-1]
    alerts = detect_alerts(latest, country_data.tail(6))
    return {'iso_a3': iso.upper(), 'date': latest['date'].strftime('%Y-%m-%d'), 'alerts': alerts}


@app.get("/reload")
def reload_data():
    global df
    csv_path = get_data_path()
    df = load_bigmac_data(csv_path)
    df = add_derived_metrics(df)
    return {'status': 'reloaded', 'rows': len(df)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
