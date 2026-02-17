# Weather Service Examples

本目录包含Weather Service的集成示例。

## Files

- `weather_example.py` - 完整的Weather Service集成示例

## Running Examples

```bash
# Set API key first (required)
export OPENWEATHER_API_KEY="your_api_key_here"

# Run weather example
python -m microservices.weather_service.examples.weather_example

# Or directly
cd microservices/weather_service/examples
python weather_example.py
```

## Getting API Key

1. Sign up at https://openweathermap.org/api
2. Get free API key
3. Set environment variable: `export OPENWEATHER_API_KEY="your_key"`

## Usage in Your Service

```python
from microservices.weather_service.client import WeatherServiceClient

# Initialize client (auto-discovers service URL)
weather = WeatherServiceClient()

# Get current weather
current = await weather.get_current_weather("New York")
print(f"Temperature: {current['temperature']}°C")

# Get forecast
forecast = await weather.get_forecast("London", days=5)
for day in forecast['forecast']:
    print(f"{day['date']}: {day['temp_max']}°C")
```

## Integration Patterns

### 1. Device Service + Weather Service
Display weather on smart frames and devices.

### 2. Notification Service + Weather Service
Send weather alerts and daily forecasts.

### 3. Calendar Service + Weather Service
Show weather for calendar events.

## Cache Strategy

- Current weather cached for 15 minutes
- Forecast cached for 30 minutes
- Automatic cache invalidation
- Redis for high-performance caching

