# Big Mac Index API

A simple, beginner-friendly FastAPI application that serves and analyzes Big Mac price data from a CSV file.

## Project Overview

This API allows you to:
- Fetch the latest Big Mac price for any country
- View historical price data
- Get analyzed insights including price trends and economic ratios
- Understand how Big Mac prices change over time

## Project Structure

```
Big Mac API/
├── app/
│   ├── main.py           # Main FastAPI application with endpoints
│   ├── data_loader.py    # CSV loading and preprocessing
│   └── transform.py      # Data transformations and derived metrics
├── data/
│   └── big mac prices 2025.csv  # Big Mac Index data
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Installation

### 1. Clone/Download the Project

Navigate to the project directory:
```bash
cd "path/to/Big Mac API"
```

### 2. Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the API

### Start the Server

```bash
uvicorn app.main:app --reload
```

The server will start at: **http://127.0.0.1:8000**

The `--reload` flag enables auto-reload when you modify code (useful for development).

### Stop the Server

Press `Ctrl+C` in the terminal.

## API Documentation

### Interactive Docs

Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

You can test all endpoints directly from these pages.

## Available Endpoints

### 1. Welcome / Root
```
GET /
```
Returns API information and available endpoints.

**Example:**
```bash
curl http://127.0.0.1:8000/
```

**Response:**
```json
{
  "message": "Welcome to the Big Mac Index API!",
  "description": "Get Big Mac price data and insights for different countries",
  "endpoints": {
    "country": "/country/{iso} - Latest data for a country",
    "history": "/history/{iso} - Full history for a country",
    "insight": "/insight/{iso} - Analysis and insights for a country"
  }
}
```

---

### 2. Get Latest Price by Country
```
GET /country/{iso}
```
Returns the most recent Big Mac price and exchange data for a country.

**Parameters:**
- `iso` (path): 3-letter ISO country code (e.g., `USA`, `CHE`, `NOR`)

**Example:**
```bash
curl http://127.0.0.1:8000/country/USA
```

**Response:**
```json
{
  "country": "United States",
  "iso_a3": "USA",
  "currency_code": "USD",
  "date": "2024-07-01",
  "local_price": 5.15,
  "dollar_price": 5.15,
  "dollar_ex": 1.0,
  "GDP_dollar": 76398.456
}
```

---

### 3. Get Historical Data
```
GET /history/{iso}
```
Returns all historical Big Mac prices for a country with derived metrics.

**Parameters:**
- `iso` (path): 3-letter ISO country code

**Example:**
```bash
curl http://127.0.0.1:8000/history/CHE
```

**Response:**
```json
{
  "country": "Switzerland",
  "iso_a3": "CHE",
  "data_points": 12,
  "history": [
    {
      "date": "2015-01-01",
      "local_price": 7.2,
      "dollar_price": 7.99,
      "dollar_ex": 0.90085,
      "GDP_dollar": 101510.023,
      "price_change_pct": null,
      "bm_gdp_ratio": 0.0000786,
      "rolling_avg_3": 7.99
    },
    ...
  ]
}
```

---

### 4. Get Country Insights
```
GET /insight/{iso}
```
Returns analysis including price trends, economic ratios, and predictions.

**Parameters:**
- `iso` (path): 3-letter ISO country code

**Example:**
```bash
curl http://127.0.0.1:8000/insight/NOR
```

**Response:**
```json
{
  "country": "Norway",
  "iso_a3": "NOR",
  "currency_code": "NOK",
  "date": "2024-07-01",
  "latest_price": 6.77,
  "price_one_year_ago": 7.14,
  "price_change_pct": -5.18,
  "bm_gdp_ratio": 0.0000625,
  "rolling_avg_3": 6.81,
  "trend": "Decreasing",
  "interpretation": "The Big Mac price is decreasing in Norway."
}
```

---

### 5. List All Countries
```
GET /countries
```
Returns a list of all countries in the dataset.

**Example:**
```bash
curl http://127.0.0.1:8000/countries
```

**Response:**
```json
{
  "total_countries": 42,
  "countries": [
    {
      "name": "Argentina",
      "iso_a3": "ARG"
    },
    ...
  ]
}
```

---

### 6. Search Countries
```
GET /search?term={text}
```
Search by country name or currency code.

**Example:**
```bash
curl "http://127.0.0.1:8000/search?term=united"
```

---

### 7. Compare Countries
```
GET /compare/{iso1}/{iso2}
```
Compare latest indicators for two countries.

**Example:**
```bash
curl http://127.0.0.1:8000/compare/NOR/CHE
```

---

### 8. Trend Analysis
```
GET /trend/{iso}?window={n}
```
Get rolling slope trend values for the selected window.

**Example:**
```bash
curl http://127.0.0.1:8000/trend/NOR?window=6
```

---

### 9. Alerts
```
GET /alerts/{iso}
```
Detect simplicity anomaly warnings (YoY swing >10%, high volatility).

**Example:**
```bash
curl http://127.0.0.1:8000/alerts/NOR
```

---

### 10. Reload Data
```
GET /reload
```
Reload the CSV dataset in runtime after the file is updated (twice per year in your use case).

**Example:**
```bash
curl http://127.0.0.1:8000/reload
```

---

## Understanding the Metrics

### price_change_pct
**Year-over-year percentage change** in Big Mac dollar price.
- Compares the current price to the price from approximately one year ago
- Positive = price increased, Negative = price decreased

### bm_gdp_ratio
**Big Mac price as a ratio of GDP per capita** (in dollars).
- Shows how Big Mac prices compare to a country's economic productivity
- Lower ratio = Big Mac is cheaper relative to the economy

### rolling_avg_3
**3-period rolling average** of dollar price.
- Smooths out short-term fluctuations
- Helps identify overall price trends more clearly

### trend
**Simple interpretation** of price movement:
- **Increasing**: Price up more than 2% year-over-year
- **Stable**: Price within ±2% year-over-year
- **Decreasing**: Price down more than 2% year-over-year

## Dependencies

- **FastAPI**: Modern Python web framework for building APIs
- **Uvicorn**: ASGI server to run FastAPI
- **Pandas**: Data processing and manipulation
- **NumPy**: Numerical computing (used by pandas)

## Code Quality Notes

- Code is organized into separate modules for clarity:
  - `data_loader.py`: Handles data ingestion
  - `transform.py`: Calculates metrics
  - `main.py`: API endpoints
- Every function has docstrings explaining its purpose
- Comments explain complex logic
- Data is sorted and validated for consistency
- Missing values are handled safely

## Learning Resources

This project demonstrates:
- Creating a simple API with FastAPI
- Data loading and preprocessing with pandas
- Time-series calculations (rolling averages, YoY changes)
- Error handling and status codes
- RESTful API design
- Project organization for beginners

## Troubleshooting

### "Module not found" errors
Make sure you've installed dependencies:
```bash
pip install -r requirements.txt
```

### Port already in use
Change the port when running:
```bash
uvicorn app.main:app --reload --port 8001
```

### CSV file not found
Ensure `data/big mac prices 2025.csv` exists in the project directory.

## Example Workflow

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
uvicorn app.main:app --reload

# 3. In another terminal, fetch data
curl http://127.0.0.1:8000/insight/USA

# 4. View interactive docs
# Open browser to http://127.0.0.1:8000/docs
```

## Future Enhancements

Possible improvements (not included to keep this beginner-friendly):
- Add a database for persistent storage
- Add user authentication
- Add filtering and sorting parameters
- Add data export to JSON/CSV
- Add statistical analysis endpoints
- Add caching for performance

## License

This is a learning project. Feel free to modify and use as needed.

---

**Created**: 2025  
**Purpose**: Learning FastAPI and data handling  
**Difficulty Level**: Beginner-friendly
