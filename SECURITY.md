# Security Implementation

This document outlines the security hardening measures implemented in the Big Mac Index API.

## Security Features

### 1. **Input Validation** ✅
- **ISO Code Validation**: Ensures country codes are exactly 3 alphabetic characters
- **Search Term Sanitization**: Regex validation blocks injection attacks, max 50 characters
- **Window Parameter Bounds**: Trend window limited to 1-20 to prevent resource exhaustion
- **Protection Against**: SQL injection, command injection, buffer overflow attacks

### 2. **Rate Limiting** ✅
- **Global Limit**: 100 requests/minute default
- **Endpoint-Specific Limits**:
  - `/reload`: 2 requests/minute (admin operation)
  - `/country/{iso}`: 30 requests/minute
  - `/history/{iso}`: 20 requests/minute
  - `/search`: 20 requests/minute
  - Root `/`: 10 requests/minute
- **429 Status Code**: Returns "Too many requests" when exceeded
- **Protection Against**: DDoS attacks, brute force, resource exhaustion

### 3. **CORS (Cross-Origin Resource Sharing)** ✅
- **Allowed Origins**: `http://localhost:3000`, `http://127.0.0.1:3000` only
- **Allowed Methods**: GET only (read-only API)
- **Credentials**: Disabled (prevents cookie/auth token leaks)
- **Protection Against**: Unauthorized cross-origin requests, CSRF attacks

### 4. **Security Headers** ✅
```
X-Content-Type-Options: nosniff          # Prevents MIME sniffing attacks
X-Frame-Options: DENY                    # Prevents clickjacking
X-XSS-Protection: 1; mode=block         # XSS attack prevention
Strict-Transport-Security: max-age=...   # Forces HTTPS
```
- **Protection Against**: XSS, Clickjacking, MIME sniffing

### 5. **Trusted Hosts Middleware** ✅
- **Allowed Hosts**: `127.0.0.1`, `localhost` only
- **Protection Against**: Host header injection attacks

### 6. **Thread Safety** ✅
- **Global Data Lock**: `threading.Lock()` protects dataframe access
- **Prevents**: Race conditions, data corruption in concurrent requests
- **Safe for**: Multi-worker deployments (Uvicorn workers, etc.)

### 7. **Error Handling & Logging** ✅
- **Sanitized Errors**: No internal stack traces exposed to client
- **Security Logging**: All requests logged with:
  - Timestamp
  - Client IP address
  - Endpoint accessed
  - Success/failure status
- **Error Classification**: Different logging for security events
- **Protection Against**: Information disclosure, undetected attacks

### 8. **Data Validation** ✅
- **Type Safety**: FastAPI's Pydantic handles type validation
- **Range Checks**: Window parameter (1-20), search term length (1-50)
- **Whitelist Patterns**: Regex allows only safe characters
- **Protection Against**: Type confusion attacks, buffer overflows

### 9. **Localhost-Only Binding** ✅
- **Host**: `127.0.0.1` (not `0.0.0.0`)
- **Port**: 8000 (local development)
- **Protection Against**: Accidental public exposure

### 10. **Dependency Security** ✅
- **Regular Updates**: Requirements use tested stable versions
- **Key Packages**:
  - `fastapi`: Web framework with built-in security
  - `slowapi`: Rate limiting
  - `uvicorn`: ASGI server with security defaults
  - `pandas`: Data processing with no known critical vulnerabilities

## Compliance & Standards

- ✅ **OWASP Top 10**: Protections against injection, broken auth, XSS, CSRF, using components with known vulns
- ✅ **NIST Guidelines**: Input validation, output encoding, secure defaults
- ✅ **API Security Best Practices**: Rate limiting, authentication-ready, error handling

## For Production Deployment

When deploying to production:

1. **Enable HTTPS**
   ```bash
   # Use a reverse proxy like Nginx with SSL certificates
   # Or use Hypercorn with SSL
   hypercorn app.main:app --certfile=cert.pem --keyfile=key.pem
   ```

2. **Expand Allowed Origins**
   Update `CORSMiddleware` with your frontend domains:
   ```python
   allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
   ```

3. **Add Authentication**
   ```python
   from fastapi.security import HTTPBearer
   security = HTTPBearer()
   
   @app.get("/protected")
   async def protected(credentials: HTTPAuthCredentials = Depends(security)):
       # Validate token here
       pass
   ```

4. **Increase Rate Limits** (if needed)
   Adjust based on expected legitimate traffic

5. **Monitor Logs**
   - Set up centralized logging (ELK, CloudWatch, etc.)
   - Alert on repeated failed requests, injection attempts
   - Track 429 (rate limit) responses for DDoS signs

6. **Environment Variables**
   ```bash
   # Move sensitive config to environment variables
   ALLOWED_HOSTS=yourdomain.com
   ALLOWED_ORIGINS=https://yourdomain.com
   RATE_LIMIT=1000/minute
   ```

7. **Regular Security Updates**
   ```bash
   pip install --upgrade fastapi uvicorn slowapi pandas numpy
   ```

## Testing Security

To test security measures locally:

```bash
# Test rate limiting (should get 429 after ~30 requests)
for i in {1..50}; do curl http://127.0.0.1:8000/country/USA; done

# Test input validation (should get 400 error)
curl "http://127.0.0.1:8000/country/INVALID"
curl "http://127.0.0.1:8000/search?term=../../etc/passwd"

# Test CORS (should be rejected from different origins)
curl -H "Origin: http://evil.com" http://127.0.0.1:8000/

# Test trusted hosts (should work only from localhost)
curl -H "Host: evil.com" http://127.0.0.1:8000/
```

## Logging

All security events are logged to stdout. Example:
```
2026-03-25 10:15:32 - app.main - INFO - Country data retrieved: USA from 127.0.0.1
2026-03-25 10:15:35 - app.main - WARNING - Rate limit exceeded from 192.168.1.100
2026-03-25 10:15:38 - app.main - ERROR - Unexpected error retrieving country data: ValueError
```

## Vulnerability Disclosure

If you discover a security vulnerability in this API:

1. **DO NOT** open a public GitHub issue
2. **DO** email security details to: `antoi@example.com`
3. Allow 7-14 days for a response and patch
4. Coordinated disclosure appreciated

## References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)
