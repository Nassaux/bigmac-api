"""
Big Mac Index API - Security Hardened
Serves Big Mac price data with comprehensive security measures.
"""

import logging
import threading
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import pandas as pd

from .data_loader import load_bigmac_data, get_data_path
from .transform import add_derived_metrics, get_price_trend, calculate_rolling_trend, detect_alerts

# ============================================================================
# LOGGING - All requests and errors logged for security audit trails
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# APP INITIALIZATION WITH SECURITY HARDENING
# ============================================================================

app = FastAPI(
    title="Big Mac Index API",
    description="Serving and analyzing Big Mac price data across countries",
    version="1.0.0"
)

# Security Headers Middleware - Prevent XSS, Clickjacking, MIME sniffing
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"  # Prevent MIME sniffing
    response.headers["X-Frame-Options"] = "DENY"  # Prevent clickjacking
    response.headers["X-XSS-Protection"] = "1; mode=block"  # XSS protection
    response.headers["Strict-Transport-Security"] = "max-age=31536000"  # Force HTTPS
    return response

# Restrict to trusted hosts only - Prevent Host header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"]
)

# CORS - Restrict to localhost only (prevent unauthorized cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Rate Limiting - Prevent DoS/brute force attacks
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded from {request.client.host}")
    raise HTTPException(status_code=429, detail="Too many requests")

# ============================================================================
# DATA INITIALIZATION WITH THREAD SAFETY
# ============================================================================

# Thread-safe access to global dataframe
df_lock = threading.Lock()
csv_path = get_data_path()
df = load_bigmac_data(csv_path)
df = add_derived_metrics(df)

logger.info(f"API initialized with {len(df)} data points from {csv_path}")

# ============================================================================
# INPUT VALIDATION - Prevent injection attacks
# ============================================================================

def validate_iso_code(iso: str) -> str:
    """Validate ISO country code - prevents injection attacks."""
    if not iso or len(iso.strip()) != 3:
        raise HTTPException(status_code=400, detail="ISO code must be 3 letters")
    if not iso.isalpha():
        raise HTTPException(status_code=400, detail="ISO code must contain only letters")
    return iso.upper()


def validate_search_term(term: str) -> str:
    """Validate search term - prevents injection and DoS attacks."""
    if not term or len(term.strip()) < 1:
        raise HTTPException(status_code=400, detail="Search term cannot be empty")
    if len(term) > 50:
        raise HTTPException(status_code=400, detail="Search term too long (max 50 characters)")
    # Only allow alphanumeric, spaces, hyphens - blocks special characters
    if not re.match(r'^[a-zA-Z0-9\s\-]*$', term):
        raise HTTPException(status_code=400, detail="Invalid characters in search term")
    return term.strip()


def validate_window(window: int) -> int:
    """Validate window parameter - prevents resource exhaustion."""
    if not isinstance(window, int) or window < 1 or window > 20:
        raise HTTPException(status_code=400, detail="Window must be between 1 and 20")
    return window


# ============================================================================
# ENDPOINTS - WITH SECURITY VALIDATION & LOGGING
# ============================================================================

@app.get("/")
@limiter.limit("10/minute")
async def read_root(request: Request):
    """Welcome endpoint - Rate limited."""
    logger.info(f"Root accessed from {request.client.host}")
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
@limiter.limit("30/minute")
async def get_country_latest(request: Request, iso: str):
    """Get latest country data - Input validated, errors sanitized."""
    try:
        iso = validate_iso_code(iso)
        with df_lock:
            country_data = df[df['iso_a3'] == iso]
        
        if country_data.empty:
            logger.warning(f"Country not found: {iso}")
            raise HTTPException(status_code=404, detail="Country not found")
        
        latest = country_data.nlargest(1, 'date').iloc[0]
        logger.info(f"Country data retrieved: {iso} from {request.client.host}")
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving country data: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/history/{iso}")
@limiter.limit("20/minute")
async def get_country_history(request: Request, iso: str):
    """Get historical data - Thread-safe access."""
    try:
        iso = validate_iso_code(iso)
        with df_lock:
            country_data = df[df['iso_a3'] == iso].sort_values('date')
        
        if country_data.empty:
            logger.warning(f"History not found: {iso}")
            raise HTTPException(status_code=404, detail="Country not found")
        
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
        
        logger.info(f"History retrieved: {iso} ({len(history)} points)")
        return {
            "country": country_data.iloc[0]['name'],
            "iso_a3": iso,
            "data_points": len(history),
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving history: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/insight/{iso}")
@limiter.limit("30/minute")
async def get_country_insight(request: Request, iso: str):
    """Get insights for a country - Comprehensive AI-ready data."""
    try:
        iso = validate_iso_code(iso)
        with df_lock:
            country_data = df[df['iso_a3'] == iso]
        
        if country_data.empty:
            logger.warning(f"Insight not found: {iso}")
            raise HTTPException(status_code=404, detail="Country not found")
        
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
        
        explanation = f"Latest price is {float(latest['dollar_price']):.2f} USD. Trend is {trend.lower()}."
        
        logger.info(f"Insight retrieved: {iso}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving insight: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/countries")
@limiter.limit("10/minute")
async def list_countries(request: Request):
    """List all countries - Cached read."""
    try:
        with df_lock:
            countries = df[['name', 'iso_a3']].drop_duplicates().sort_values('iso_a3')
        
        logger.info(f"Countries list retrieved ({len(countries)} countries)")
        return {
            "total_countries": len(countries),
            "countries": [{"name": row['name'], "iso_a3": row['iso_a3']} for _, row in countries.iterrows()]
        }
    except Exception as e:
        logger.error(f"Unexpected error retrieving countries: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/search")
@limiter.limit("20/minute")
async def search_countries(request: Request, term: str):
    """Search countries - Injection-safe regex validation."""
    try:
        term = validate_search_term(term)
        with df_lock:
            filtered = df[df['name'].str.contains(term, case=False, na=False) | df['currency_code'].str.contains(term, case=False, na=False)]
        
        if filtered.empty:
            logger.info(f"No search results for: {term}")
            raise HTTPException(status_code=404, detail="No results found")
        
        logger.info(f"Search performed: {term} ({len(filtered)} results)")
        return filtered[['name', 'iso_a3', 'currency_code']].drop_duplicates().to_dict(orient='records')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error searching: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/compare/{iso1}/{iso2}")
@limiter.limit("15/minute")
async def compare_countries(request: Request, iso1: str, iso2: str):
    """Compare two countries - Both inputs validated."""
    try:
        iso1 = validate_iso_code(iso1)
        iso2 = validate_iso_code(iso2)
        
        with df_lock:
            c1 = df[df['iso_a3'] == iso1]
            c2 = df[df['iso_a3'] == iso2]
        
        if c1.empty or c2.empty:
            logger.warning(f"Compare failed: {iso1} or {iso2} not found")
            raise HTTPException(status_code=404, detail="One or both countries not found")
        
        r1 = c1.nlargest(1, 'date').iloc[0]
        r2 = c2.nlargest(1, 'date').iloc[0]
        
        logger.info(f"Comparison: {iso1} vs {iso2}")
        return {
            'left': {
                'iso_a3': r1['iso_a3'],
                'country': r1['name'],
                'date': r1['date'].strftime('%Y-%m-%d'),
                'dollar_price': float(r1['dollar_price']),
                'price_change_pct': float(r1['price_change_pct']) if pd.notna(r1['price_change_pct']) else None,
            },
            'right': {
                'iso_a3': r2['iso_a3'],
                'country': r2['name'],
                'date': r2['date'].strftime('%Y-%m-%d'),
                'dollar_price': float(r2['dollar_price']),
                'price_change_pct': float(r2['price_change_pct']) if pd.notna(r2['price_change_pct']) else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error comparing: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/trend/{iso}")
@limiter.limit("15/minute")
async def country_trend(request: Request, iso: str, window: int = 3):
    """Get trend for a country - Window parameter validated."""
    try:
        iso = validate_iso_code(iso)
        window = validate_window(window)
        
        with df_lock:
            country_data = df[df['iso_a3'] == iso].sort_values('date')
        
        if country_data.empty:
            logger.warning(f"Trend not found: {iso}")
            raise HTTPException(status_code=404, detail="Country not found")
        
        slopes = calculate_rolling_trend(country_data, window=window)
        result = []
        for i, r in country_data.iterrows():
            result.append({
                'date': r['date'].strftime('%Y-%m-%d'),
                'dollar_price': float(r['dollar_price']),
                'rolling_slope': float(slopes.loc[i]) if pd.notna(slopes.loc[i]) else None
            })
        
        logger.info(f"Trend retrieved: {iso} (window={window})")
        return {'iso_a3': iso, 'window': window, 'trend': result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving trend: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/alerts/{iso}")
@limiter.limit("20/minute")
async def country_alerts(request: Request, iso: str):
    """Get alerts for a country - Anomaly detection."""
    try:
        iso = validate_iso_code(iso)
        with df_lock:
            country_data = df[df['iso_a3'] == iso].sort_values('date')
        
        if country_data.empty:
            logger.warning(f"Alerts not found: {iso}")
            raise HTTPException(status_code=404, detail="Country not found")
        
        latest = country_data.iloc[-1]
        alerts = detect_alerts(latest, country_data.tail(6))
        
        logger.info(f"Alerts retrieved: {iso}")
        return {'iso_a3': iso, 'date': latest['date'].strftime('%Y-%m-%d'), 'alerts': alerts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving alerts: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/reload")
@limiter.limit("2/minute")
async def reload_data(request: Request):
    """Reload CSV data - Thread-safe with strict rate limiting."""
    try:
        global df
        logger.warning(f"Data reload initiated from {request.client.host}")
        
        with df_lock:
            csv_path_reload = get_data_path()
            df = load_bigmac_data(csv_path_reload)
            df = add_derived_metrics(df)
        
        logger.info(f"Data successfully reloaded: {len(df)} rows")
        return {'status': 'reloaded', 'rows': len(df)}
    except Exception as e:
        logger.error(f"Error reloading data: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Big Mac Index API with security hardening...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

