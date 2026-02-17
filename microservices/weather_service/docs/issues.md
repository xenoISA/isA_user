# Weather Service - Known Issues

**Last Updated:** 2025-10-28
**Test Results:** Not Fully Tested

## Overview
Weather service integrates with external weather APIs and has not been comprehensively tested.

## Status: Incomplete Testing

### Tests Available
- `tests/weather_test.sh` exists

### Testing Status
- ⚠️ Tests run but showed failures
- 🔄 Service needs debugging and verification
- 📋 External API integration needs validation

---

## Required Actions

### 1. Run and Document Tests
**Priority:** High

**Steps:**
```bash
cd microservices/weather_service/tests
bash weather_test.sh 2>&1 | tee test_results.log
```

**Expected Checks:**
- Health check endpoints
- Weather data retrieval
- Location-based queries
- Forecast data
- Cache management
- API key validation

### 2. Verify External API Integration
**Priority:** High

**Checks Needed:**
- Weather API credentials configured
- API endpoints accessible
- Rate limiting handled
- Error handling for API failures
- Cache to reduce API calls

### 3. Common Issues to Investigate
**Priority:** High

Likely issues:
- Missing API keys in environment
- External API not accessible in test environment
- Database schema for caching not created
- Response parsing errors
- Rate limiting not implemented

---

## Known Infrastructure

### Service Files:
- ✅ `main.py` - Service entry point
- ✅ `weather_service.py` - Business logic
- ✅ Test script available

### External Dependencies:
- 🔄 Weather API (e.g., OpenWeatherMap, WeatherAPI)
- 🔄 API credentials/keys

### Database:
- 🔄 Schema for caching weather data
- 🔄 Location data storage

### Service Dependencies:
- Auth Service (for authentication)
- PostgreSQL (optional, for caching)

---

## Environment Configuration Needed

### Required Environment Variables:
```bash
# Weather API Configuration
WEATHER_API_KEY=your_api_key_here
WEATHER_API_URL=https://api.weatherapi.com/v1
WEATHER_CACHE_TTL=3600  # Cache for 1 hour

# Optional
WEATHER_API_PROVIDER=openweathermap  # or weatherapi
WEATHER_DEFAULT_UNITS=metric  # or imperial
```

---

## Potential Fixes Needed

### 1. Add API Key Validation
```python
def __init__(self):
    self.api_key = os.getenv('WEATHER_API_KEY')
    if not self.api_key:
        logger.warning("Weather API key not configured")
        self.api_enabled = False
    else:
        self.api_enabled = True
```

### 2. Add Cache Layer
```python
async def get_weather(self, location: str):
    # Check cache first
    cached = await self.get_from_cache(location)
    if cached and not self.is_expired(cached):
        return cached

    # Fetch from API
    weather_data = await self.fetch_from_api(location)

    # Store in cache
    await self.store_in_cache(location, weather_data)

    return weather_data
```

### 3. Add Error Handling for API Failures
```python
try:
    response = await self.weather_client.get(...)
    if response.status_code != 200:
        return self.get_default_response()
except Exception as e:
    logger.error(f"Weather API error: {e}")
    return self.get_cached_or_default()
```

### 4. Add Mock/Test Mode
```python
if os.getenv('WEATHER_SERVICE_MODE') == 'test':
    # Return mock data
    return self.get_mock_weather_data(location)
```

---

## Test Environment Considerations

### For Testing Without Real API:
1. **Mock API responses** for test environment
2. **Use test API keys** with limited quota
3. **Cache test data** to avoid repeated API calls
4. **Add test mode** that doesn't require API

### Recommended Test Approach:
```python
# In weather_service.py
class WeatherService:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode or os.getenv('TEST_MODE') == 'true'

        if self.test_mode:
            logger.info("Running in TEST MODE - using mock data")
```

---

## Next Steps

1. **Check API configuration** and credentials
2. **Run tests** with proper API setup
3. **Implement caching** to reduce API calls
4. **Add test mode** for offline testing
5. **Document results** in this file
6. **Fix identified issues**
7. **Re-test** to verify fixes

---

## API Rate Limiting

### Typical Limits:
- Free tier: 1000 calls/day
- Standard: 10,000 calls/day
- Cache TTL: 15-60 minutes recommended

### Implementation:
```python
class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period  # in seconds
        self.calls = []

    async def check_limit(self) -> bool:
        # Remove old calls outside period
        # Check if under limit
        # Add new call if allowed
```

---

## Template for Updates

After running tests, add:

```markdown
## Test Results

**Date:** YYYY-MM-DD
**Tests Passing:** X/Y (Z%)

### API Configuration
- Provider: OpenWeatherMap/WeatherAPI
- API Key: Configured ✅ / Not Configured ❌
- Cache Enabled: Yes/No

### Critical Issues
- Issue 1: Description
- Issue 2: Description

### Working Features
- Feature 1
- Feature 2
```

---

## Related Files

- `weather_service.py` - Business logic
- `main.py` - API endpoints
- `tests/weather_test.sh` - Test suite
- `.env` - Environment configuration (API keys)
