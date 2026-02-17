# Weather Service

天气服务微服务 - Weather data fetching and caching with external API integration.

## Features

- 🌤️ **Current Weather** - Get real-time weather data
- 📅 **Weather Forecast** - Multi-day forecast (up to 16 days)
- 🚨 **Weather Alerts** - Severe weather warnings
- 💾 **Smart Caching** - Redis caching with 15-30 min TTL
- 📍 **Favorite Locations** - Save and manage user locations
- 🔌 **Multiple Providers** - OpenWeatherMap, WeatherAPI, Visual Crossing

## Quick Start

### Start Service

```bash
python -m microservices.weather_service.main
# Service runs on http://localhost:8241
```

### Run Tests

```bash
./tests/weather_test.sh
```

## API Endpoints

### Weather Data
- `GET /api/v1/weather/current?location={location}` - Current weather
- `GET /api/v1/weather/forecast?location={location}&days={days}` - Forecast
- `GET /api/v1/weather/alerts?location={location}` - Weather alerts

### Locations
- `POST /api/v1/weather/locations` - Save favorite location
- `GET /api/v1/weather/locations/{user_id}` - List saved locations
- `DELETE /api/v1/weather/locations/{id}` - Remove location

## Integration Example

```python
from microservices.weather_service.client import WeatherServiceClient

weather = WeatherServiceClient("http://localhost:8241")

# Get current weather
current = await weather.get_current_weather("New York")
print(f"Temperature: {current['temperature']}°C")

# Get 5-day forecast
forecast = await weather.get_forecast("London", days=5)
```

## Configuration

Set environment variables:

```bash
export WEATHER_SERVICE_PORT=8241
export OPENWEATHER_API_KEY="your_api_key_here"
export REDIS_URL="redis://localhost:6379"
export WEATHER_CACHE_TTL=900  # 15 minutes in seconds
```

## External APIs

### OpenWeatherMap (Default)
1. Sign up at https://openweathermap.org/api
2. Get API key
3. Set `OPENWEATHER_API_KEY`

## Port

- Default: `8241`
- Configure: `WEATHER_SERVICE_PORT=8241`

## Cache Strategy

- Current weather: 15 min TTL
- Forecast: 30 min TTL
- Alerts: 10 min TTL

## See Also

- [Examples](examples/) - Integration examples
- [Tests](tests/) - Test scripts
- [Migrations](migrations/) - Database schema

