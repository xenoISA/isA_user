"""
Weather Service Integration Example

示例：如何在其他服务中集成Weather Service
"""

import asyncio
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from microservices.weather_service.client import WeatherServiceClient


async def example_weather_integration():
    """示例：完整的天气服务集成流程"""
    
    # Initialize client
    # Option 1: Use service discovery (auto-detect from Consul)
    client = WeatherServiceClient()
    
    # Option 2: Use explicit URL
    # client = WeatherServiceClient("http://localhost:8241")
    
    try:
        # 1. Health Check
        print("=" * 60)
        print("1. Health Check")
        print("=" * 60)
        healthy = await client.health_check()
        print(f"Service healthy: {healthy}\n")
        
        if not healthy:
            print("Weather service is not available!")
            return
        
        # 2. Get Current Weather
        print("=" * 60)
        print("2. Get Current Weather")
        print("=" * 60)
        
        weather = await client.get_current_weather("New York")
        
        if weather:
            print(f"✓ Weather for {weather['location']}:")
            print(f"  Temperature: {weather['temperature']}°C")
            print(f"  Feels like: {weather.get('feels_like', 'N/A')}°C")
            print(f"  Humidity: {weather['humidity']}%")
            print(f"  Condition: {weather['condition']}")
            print(f"  Description: {weather.get('description', 'N/A')}")
            print(f"  Wind speed: {weather.get('wind_speed', 'N/A')} m/s")
            print(f"  Cached: {weather.get('cached', False)}")
        else:
            print("✗ Failed to get weather data")
            print("Note: Make sure OPENWEATHER_API_KEY is configured")
            return
        
        print()
        
        # 3. Get Weather Forecast
        print("=" * 60)
        print("3. Get 5-Day Weather Forecast")
        print("=" * 60)
        
        forecast = await client.get_forecast("London", days=5)
        
        if forecast:
            print(f"✓ 5-day forecast for {forecast['location']}:")
            for i, day in enumerate(forecast['forecast'], 1):
                print(f"  Day {i}: {day['temp_max']}°C / {day['temp_min']}°C - {day['condition']}")
        else:
            print("✗ Failed to get forecast")
        
        print()
        
        # 4. Get Weather for Multiple Cities
        print("=" * 60)
        print("4. Get Weather for Multiple Cities")
        print("=" * 60)
        
        cities = ["Tokyo", "Paris", "Sydney", "Dubai"]
        
        for city in cities:
            weather = await client.get_current_weather(city)
            if weather:
                print(f"✓ {city}: {weather['temperature']}°C, {weather['condition']}")
            else:
                print(f"✗ {city}: Failed")
        
        print()
        
        # 5. Save Favorite Location
        print("=" * 60)
        print("5. Save Favorite Location")
        print("=" * 60)
        
        location = await client.save_location(
            user_id="user_123",
            location="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            is_default=True,
            nickname="Home"
        )
        
        if location:
            print(f"✓ Saved location: {location['location']} ({location['nickname']})")
            location_id = location['id']
        else:
            print("✗ Failed to save location")
            location_id = None
        
        print()
        
        # 6. Get User's Favorite Locations
        print("=" * 60)
        print("6. Get User's Favorite Locations")
        print("=" * 60)
        
        locations = await client.get_user_locations("user_123")
        
        if locations:
            print(f"✓ Found {locations['total']} locations:")
            for loc in locations['locations']:
                default_mark = " (default)" if loc.get('is_default') else ""
                nickname = f" - {loc.get('nickname')}" if loc.get('nickname') else ""
                print(f"  • {loc['location']}{nickname}{default_mark}")
        
        print()
        
        # 7. Get Weather Summary (Current + Forecast)
        print("=" * 60)
        print("7. Get Weather Summary")
        print("=" * 60)
        
        summary = await client.get_weather_summary("Berlin")
        
        if summary:
            print(f"✓ Weather summary for {summary['location']}:")
            print(f"  Current: {summary['current']['temperature']}°C, {summary['current']['condition']}")
            print(f"  Forecast:")
            for i, day in enumerate(summary['forecast'][:3], 1):
                print(f"    Day {i}: {day['temp_max']}°C / {day['temp_min']}°C")
        
        print()
        
        # 8. Get Weather Alerts
        print("=" * 60)
        print("8. Get Weather Alerts")
        print("=" * 60)
        
        alerts = await client.get_weather_alerts("Miami")
        
        if alerts:
            if alerts['alerts']:
                print(f"⚠️  Found {len(alerts['alerts'])} weather alerts:")
                for alert in alerts['alerts']:
                    print(f"  • {alert['headline']} ({alert['severity']})")
            else:
                print("✓ No active weather alerts")
        
        print()
        
        # 9. Test Caching
        print("=" * 60)
        print("9. Test Weather Data Caching")
        print("=" * 60)
        
        import time
        
        # First request (not cached)
        start = time.time()
        weather1 = await client.get_current_weather("Moscow")
        time1 = time.time() - start
        
        # Second request (should be cached)
        start = time.time()
        weather2 = await client.get_current_weather("Moscow")
        time2 = time.time() - start
        
        print(f"✓ First request: {time1:.3f}s (cached: {weather1.get('cached', False)})")
        print(f"✓ Second request: {time2:.3f}s (cached: {weather2.get('cached', False)})")
        print(f"  Speed improvement: {time1/time2:.1f}x faster")
        
        print()
        
        # 10. Cleanup - Delete Location
        if location_id:
            print("=" * 60)
            print("10. Delete Favorite Location")
            print("=" * 60)
            
            deleted = await client.delete_location(location_id, "user_123")
            if deleted:
                print(f"✓ Deleted location ID: {location_id}")
            
            print()
        
    finally:
        # Clean up
        await client.close()


async def example_device_service_integration():
    """示例：Device Service 如何使用 Weather Service"""
    
    print("\n" + "=" * 60)
    print("Example: Device Service + Weather Service")
    print("=" * 60 + "\n")
    
    weather = WeatherServiceClient()
    
    try:
        # Smart display device requests weather for its location
        device_location = "Seattle"
        
        # Get current weather
        current = await weather.get_current_weather(device_location)
        
        if current:
            print(f"📱 Display weather on device:")
            print(f"   Location: {current['location']}")
            print(f"   Temperature: {current['temperature']}°C")
            print(f"   Condition: {current['condition']}")
            print(f"   Icon: {current.get('icon', 'N/A')}")
        
        # Get forecast for smart home planning
        forecast = await weather.get_forecast(device_location, days=3)
        
        if forecast:
            print(f"\n📅 3-day forecast:")
            for day in forecast['forecast']:
                print(f"   {day['date'][:10]}: {day['condition']}, {day['temp_max']}°C")
        
    finally:
        await weather.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Weather Service Integration Examples")
    print("=" * 60 + "\n")
    
    print("⚠️  Note: These examples require OPENWEATHER_API_KEY to be set")
    print("Set it with: export OPENWEATHER_API_KEY=\"your_api_key_here\"")
    print()
    
    # Run examples
    asyncio.run(example_weather_integration())
    asyncio.run(example_device_service_integration())
    
    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60 + "\n")

