"""
Location Service Client Example

Demonstrates how to use the LocationServiceClient
"""

import asyncio
from datetime import datetime, timezone
from microservices.location_service.client import LocationServiceClient


async def main():
    """Example usage of LocationServiceClient"""

    # Initialize client
    client = LocationServiceClient()
    print("Location Service Client initialized\n")

    # ==================== Report Location ====================

    print("1. Reporting device location...")
    location_result = await client.report_location(
        device_id="smart_frame_001",
        latitude=37.7749,  # San Francisco
        longitude=-122.4194,
        accuracy=10.0,
        location_method="gps",
        battery_level=85.5
    )
    print(f"Location reported: {location_result}")
    print()

    # ==================== Batch Report ====================

    print("2. Batch reporting multiple locations...")
    locations = [
        {
            "device_id": "smart_frame_001",
            "latitude": 37.7750,
            "longitude": -122.4195,
            "accuracy": 12.0,
            "location_method": "gps",
            "source": "device"
        },
        {
            "device_id": "smart_frame_001",
            "latitude": 37.7751,
            "longitude": -122.4196,
            "accuracy": 15.0,
            "location_method": "hybrid",
            "source": "device"
        }
    ]
    batch_result = await client.batch_report_locations(locations)
    print(f"Batch result: {batch_result}")
    print()

    # ==================== Get Latest Location ====================

    print("3. Getting device latest location...")
    latest = await client.get_device_latest_location("smart_frame_001")
    print(f"Latest location: {latest}")
    print()

    # ==================== Create Geofence ====================

    print("4. Creating a circular geofence...")
    geofence_result = await client.create_geofence(
        name="Home Geofence",
        shape_type="circle",
        center_lat=37.7749,
        center_lon=-122.4194,
        radius=100.0,  # 100 meters
        trigger_on_enter=True,
        trigger_on_exit=True,
        trigger_on_dwell=True,
        dwell_time_seconds=300,  # 5 minutes
        target_devices=["smart_frame_001"],
        notification_channels=["push", "email"],
        description="Geofence around home location"
    )
    print(f"Geofence created: {geofence_result}")
    geofence_id = geofence_result.get('geofence_id')
    print()

    # ==================== List Geofences ====================

    print("5. Listing all geofences...")
    geofences = await client.list_geofences(active_only=True)
    print(f"Active geofences: {geofences}")
    print()

    # ==================== Find Nearby Devices ====================

    print("6. Finding nearby devices...")
    nearby = await client.find_nearby_devices(
        latitude=37.7749,
        longitude=-122.4194,
        radius_meters=5000,  # 5km
        time_window_minutes=30
    )
    print(f"Nearby devices: {nearby}")
    print()

    # ==================== Search Locations in Radius ====================

    print("7. Searching locations in radius...")
    search_result = await client.search_radius(
        center_lat=37.7749,
        center_lon=-122.4194,
        radius_meters=1000,
        start_time=datetime.now(timezone.utc).replace(hour=0, minute=0),
        end_time=datetime.now(timezone.utc),
        limit=50
    )
    print(f"Locations in radius: {search_result}")
    print()

    # ==================== Calculate Distance ====================

    print("8. Calculating distance between two points...")
    distance = await client.calculate_distance(
        from_lat=37.7749,
        from_lon=-122.4194,
        to_lat=37.7850,
        to_lon=-122.4095
    )
    print(f"Distance: {distance}")
    print()

    # ==================== Get Location History ====================

    print("9. Getting device location history...")
    history = await client.get_device_location_history(
        device_id="smart_frame_001",
        limit=10
    )
    print(f"Location history: {history}")
    print()

    # ==================== Update Geofence ====================

    if geofence_id:
        print("10. Updating geofence...")
        update_result = await client.update_geofence(
            geofence_id=geofence_id,
            name="Updated Home Geofence",
            trigger_on_dwell=False
        )
        print(f"Geofence updated: {update_result}")
        print()

    # ==================== Deactivate Geofence ====================

    if geofence_id:
        print("11. Deactivating geofence...")
        deactivate_result = await client.deactivate_geofence(geofence_id)
        print(f"Geofence deactivated: {deactivate_result}")
        print()

    # ==================== Reactivate Geofence ====================

    if geofence_id:
        print("12. Reactivating geofence...")
        activate_result = await client.activate_geofence(geofence_id)
        print(f"Geofence activated: {activate_result}")
        print()

    # ==================== Get Statistics ====================

    print("13. Getting user statistics...")
    stats = await client.get_user_stats("test_user")
    print(f"User statistics: {stats}")
    print()

    # ==================== Delete Geofence ====================

    if geofence_id:
        print("14. Deleting geofence...")
        delete_result = await client.delete_geofence(geofence_id)
        print(f"Geofence deleted: {delete_result}")
        print()

    print("✓ Location Service Client example completed!")


if __name__ == "__main__":
    asyncio.run(main())
