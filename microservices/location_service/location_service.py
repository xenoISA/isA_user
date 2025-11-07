"""
Location Service - Business Logic Layer
Coordinates location tracking, geofencing, and spatial operations
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from .models import (
    LocationReportRequest, LocationBatchRequest,
    GeofenceCreateRequest, GeofenceUpdateRequest,
    PlaceCreateRequest, PlaceUpdateRequest,
    NearbySearchRequest, RadiusSearchRequest, PolygonSearchRequest,
    LocationResponse, GeofenceResponse, PlaceResponse, RouteResponse,
    LocationOperationResult, LocationMethod, GeofenceShapeType,
    LocationEventType
)
from .location_repository import LocationRepository
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


class LocationService:
    """
    Location Service Business Logic

    Handles location tracking, geofencing, places, and route management
    """

    def __init__(self, consul_registry=None, event_bus=None):
        """
        Initialize location service

        Args:
            consul_registry: Optional ConsulRegistry for service discovery
            event_bus: Optional NATS event bus for publishing events
        """
        self.consul_registry = consul_registry
        self.event_bus = event_bus
        self.repository = LocationRepository()

        logger.info("Location service initialized")

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            # Simple query to test connection
            query = "SELECT 1"
            with self.repository.db:
                result = self.repository.db.query(query, [], schema=self.repository.schema)
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    # ==================== Location Operations ====================

    async def report_location(
        self,
        request: LocationReportRequest,
        user_id: str
    ) -> LocationOperationResult:
        """
        Report device location

        Args:
            request: Location report request
            user_id: User ID (from authentication)

        Returns:
            LocationOperationResult
        """
        try:
            location_id = str(uuid.uuid4())
            timestamp = request.timestamp or datetime.now(timezone.utc)

            location_data = {
                'location_id': location_id,
                'device_id': request.device_id,
                'user_id': user_id,
                'latitude': request.latitude,
                'longitude': request.longitude,
                'altitude': request.altitude,
                'accuracy': request.accuracy,
                'heading': request.heading,
                'speed': request.speed,
                'address': request.address,
                'city': request.city,
                'state': request.state,
                'country': request.country,
                'postal_code': request.postal_code,
                'location_method': request.location_method,
                'battery_level': request.battery_level,
                'source': request.source,
                'metadata': request.metadata,
                'timestamp': timestamp,
                'created_at': datetime.now(timezone.utc)
            }

            # Store location
            try:
                result = await self.repository.create_location(location_data)
            except Exception as db_error:
                logger.error(f"Database error creating location: {db_error}", exc_info=True)
                return LocationOperationResult(
                    success=False,
                    operation="report_location",
                    message=f"Database error: {str(db_error)}"
                )

            if result:
                # Check geofences asynchronously
                await self._check_geofences_for_location(location_data)

                # Publish location update event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.LOCATION_UPDATED,
                            source=ServiceSource.LOCATION_SERVICE,
                            data={
                                'location_id': location_id,
                                'device_id': request.device_id,
                                'user_id': user_id,
                                'latitude': request.latitude,
                                'longitude': request.longitude,
                                'timestamp': timestamp.isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish location.updated event: {e}")

                return LocationOperationResult(
                    success=True,
                    location_id=location_id,
                    operation="report_location",
                    message="Location reported successfully",
                    data=result
                )
            else:
                logger.warning(f"create_location returned None for location_id: {location_id}")
                return LocationOperationResult(
                    success=False,
                    operation="report_location",
                    message="Failed to store location - database insert returned no result"
                )

        except Exception as e:
            logger.error(f"Error reporting location: {e}", exc_info=True)
            return LocationOperationResult(
                success=False,
                operation="report_location",
                message=f"Error: {str(e)}"
            )

    async def batch_report_locations(
        self,
        request: LocationBatchRequest,
        user_id: str
    ) -> LocationOperationResult:
        """
        Report multiple locations in batch

        Args:
            request: Batch location request
            user_id: User ID

        Returns:
            LocationOperationResult
        """
        try:
            success_count = 0
            failed_count = 0
            location_ids = []

            for loc_request in request.locations:
                result = await self.report_location(loc_request, user_id)
                if result.success:
                    success_count += 1
                    location_ids.append(result.location_id)
                else:
                    failed_count += 1

            return LocationOperationResult(
                success=True,
                operation="batch_report_locations",
                message=f"Batch processed: {success_count} successful, {failed_count} failed",
                affected_count=success_count,
                data={'location_ids': location_ids}
            )

        except Exception as e:
            logger.error(f"Error in batch location report: {e}")
            return LocationOperationResult(
                success=False,
                operation="batch_report_locations",
                message=f"Error: {str(e)}"
            )

    async def get_device_latest_location(
        self,
        device_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get device's latest location"""
        try:
            location = await self.repository.get_device_latest_location(device_id)

            # Verify user has access to this device's location
            if location and location['user_id'] != user_id:
                logger.warning(f"User {user_id} attempted to access device {device_id} location")
                return None

            return location

        except Exception as e:
            logger.error(f"Error getting device latest location: {e}")
            return None

    async def get_device_location_history(
        self,
        device_id: str,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get device location history"""
        try:
            locations = await self.repository.get_device_location_history(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset
            )

            # Filter locations that belong to this user
            return [loc for loc in locations if loc['user_id'] == user_id]

        except Exception as e:
            logger.error(f"Error getting device location history: {e}")
            return []

    async def get_user_devices_locations(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get latest locations for all user's devices"""
        try:
            # This would require joining with device_service to get user's device list
            # For now, return empty list and implement later with device service integration
            logger.info(f"Getting locations for user {user_id}'s devices")
            return []

        except Exception as e:
            logger.error(f"Error getting user devices locations: {e}")
            return []

    # ==================== Geofence Operations ====================

    async def create_geofence(
        self,
        request: GeofenceCreateRequest,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> LocationOperationResult:
        """Create a new geofence"""
        try:
            geofence_id = str(uuid.uuid4())

            # Validate shape-specific requirements
            if request.shape_type == GeofenceShapeType.CIRCLE and not request.radius:
                return LocationOperationResult(
                    success=False,
                    operation="create_geofence",
                    message="Radius is required for circle geofences"
                )

            if request.shape_type == GeofenceShapeType.POLYGON and not request.polygon_coordinates:
                return LocationOperationResult(
                    success=False,
                    operation="create_geofence",
                    message="Polygon coordinates are required for polygon geofences"
                )

            geofence_data = {
                'geofence_id': geofence_id,
                'name': request.name,
                'description': request.description,
                'user_id': user_id,
                'organization_id': organization_id,
                'shape_type': request.shape_type,
                'center_lat': request.center_lat,
                'center_lon': request.center_lon,
                'radius': request.radius,
                'polygon_coordinates': request.polygon_coordinates,
                'active': True,
                'trigger_on_enter': request.trigger_on_enter,
                'trigger_on_exit': request.trigger_on_exit,
                'trigger_on_dwell': request.trigger_on_dwell,
                'dwell_time_seconds': request.dwell_time_seconds,
                'target_devices': request.target_devices,
                'target_groups': request.target_groups,
                'active_days': request.active_days,
                'active_hours': request.active_hours,
                'notification_channels': request.notification_channels,
                'notification_template': request.notification_template,
                'tags': request.tags,
                'metadata': request.metadata,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }

            result = await self.repository.create_geofence(geofence_data)

            if result:
                # Publish geofence created event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.GEOFENCE_CREATED,
                            source=ServiceSource.LOCATION_SERVICE,
                            data={
                                'geofence_id': geofence_id,
                                'name': request.name,
                                'user_id': user_id,
                                'shape_type': request.shape_type
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish geofence.created event: {e}")

                return LocationOperationResult(
                    success=True,
                    geofence_id=geofence_id,
                    operation="create_geofence",
                    message="Geofence created successfully",
                    data=result
                )
            else:
                return LocationOperationResult(
                    success=False,
                    operation="create_geofence",
                    message="Failed to create geofence"
                )

        except Exception as e:
            logger.error(f"Error creating geofence: {e}")
            return LocationOperationResult(
                success=False,
                operation="create_geofence",
                message=f"Error: {str(e)}"
            )

    async def get_geofence(
        self,
        geofence_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get geofence by ID"""
        try:
            geofence = await self.repository.get_geofence_by_id(geofence_id)

            # Verify user has access
            if geofence and geofence['user_id'] != user_id:
                logger.warning(f"User {user_id} attempted to access geofence {geofence_id}")
                return None

            return geofence

        except Exception as e:
            logger.error(f"Error getting geofence: {e}")
            return None

    async def list_geofences(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List geofences for a user"""
        try:
            return await self.repository.list_geofences(
                user_id=user_id,
                active_only=active_only,
                limit=limit,
                offset=offset
            )

        except Exception as e:
            logger.error(f"Error listing geofences: {e}")
            return []

    async def update_geofence(
        self,
        geofence_id: str,
        request: GeofenceUpdateRequest,
        user_id: str
    ) -> LocationOperationResult:
        """Update geofence"""
        try:
            # Verify ownership
            geofence = await self.repository.get_geofence_by_id(geofence_id)
            if not geofence or geofence['user_id'] != user_id:
                return LocationOperationResult(
                    success=False,
                    operation="update_geofence",
                    message="Geofence not found or access denied"
                )

            # Build update dict
            updates = {}
            for field, value in request.model_dump(exclude_unset=True).items():
                if value is not None:
                    updates[field] = value

            if updates:
                success = await self.repository.update_geofence(geofence_id, updates)

                if success:
                    return LocationOperationResult(
                        success=True,
                        geofence_id=geofence_id,
                        operation="update_geofence",
                        message="Geofence updated successfully"
                    )

            return LocationOperationResult(
                success=False,
                operation="update_geofence",
                message="No updates applied"
            )

        except Exception as e:
            logger.error(f"Error updating geofence: {e}")
            return LocationOperationResult(
                success=False,
                operation="update_geofence",
                message=f"Error: {str(e)}"
            )

    async def delete_geofence(
        self,
        geofence_id: str,
        user_id: str
    ) -> LocationOperationResult:
        """Delete geofence"""
        try:
            # Verify ownership
            geofence = await self.repository.get_geofence_by_id(geofence_id)
            if not geofence or geofence['user_id'] != user_id:
                return LocationOperationResult(
                    success=False,
                    operation="delete_geofence",
                    message="Geofence not found or access denied"
                )

            success = await self.repository.delete_geofence(geofence_id)

            if success:
                # Publish geofence deleted event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.GEOFENCE_DELETED,
                            source=ServiceSource.LOCATION_SERVICE,
                            data={
                                'geofence_id': geofence_id,
                                'user_id': user_id
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish geofence.deleted event: {e}")

                return LocationOperationResult(
                    success=True,
                    operation="delete_geofence",
                    message="Geofence deleted successfully"
                )
            else:
                return LocationOperationResult(
                    success=False,
                    operation="delete_geofence",
                    message="Failed to delete geofence"
                )

        except Exception as e:
            logger.error(f"Error deleting geofence: {e}")
            return LocationOperationResult(
                success=False,
                operation="delete_geofence",
                message=f"Error: {str(e)}"
            )

    async def activate_geofence(
        self,
        geofence_id: str,
        user_id: str
    ) -> LocationOperationResult:
        """Activate a geofence"""
        return await self._toggle_geofence(geofence_id, user_id, True)

    async def deactivate_geofence(
        self,
        geofence_id: str,
        user_id: str
    ) -> LocationOperationResult:
        """Deactivate a geofence"""
        return await self._toggle_geofence(geofence_id, user_id, False)

    async def _toggle_geofence(
        self,
        geofence_id: str,
        user_id: str,
        active: bool
    ) -> LocationOperationResult:
        """Toggle geofence active status"""
        try:
            geofence = await self.repository.get_geofence_by_id(geofence_id)
            if not geofence or geofence['user_id'] != user_id:
                return LocationOperationResult(
                    success=False,
                    operation="toggle_geofence",
                    message="Geofence not found or access denied"
                )

            success = await self.repository.update_geofence(
                geofence_id,
                {'active': active}
            )

            action = "activated" if active else "deactivated"
            if success:
                return LocationOperationResult(
                    success=True,
                    geofence_id=geofence_id,
                    operation="toggle_geofence",
                    message=f"Geofence {action} successfully"
                )
            else:
                return LocationOperationResult(
                    success=False,
                    operation="toggle_geofence",
                    message=f"Failed to {action.lower()[:-1]} geofence"
                )

        except Exception as e:
            logger.error(f"Error toggling geofence: {e}")
            return LocationOperationResult(
                success=False,
                operation="toggle_geofence",
                message=f"Error: {str(e)}"
            )

    async def _check_geofences_for_location(self, location_data: Dict[str, Any]):
        """
        Check if location triggers any geofences

        This runs asynchronously after location is stored
        """
        try:
            triggered_geofences = await self.repository.check_point_in_geofences(
                latitude=location_data['latitude'],
                longitude=location_data['longitude'],
                device_id=location_data['device_id'],
                user_id=location_data['user_id']
            )

            for geofence in triggered_geofences:
                # Publish geofence trigger event
                if self.event_bus and geofence.get('trigger_on_enter'):
                    try:
                        event = Event(
                            event_type=EventType.GEOFENCE_ENTERED,
                            source=ServiceSource.LOCATION_SERVICE,
                            data={
                                'geofence_id': geofence['geofence_id'],
                                'geofence_name': geofence['name'],
                                'device_id': location_data['device_id'],
                                'user_id': location_data['user_id'],
                                'location_id': location_data['location_id'],
                                'timestamp': location_data['timestamp'].isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish geofence.entered event: {e}")

        except Exception as e:
            logger.error(f"Error checking geofences: {e}")

    # ==================== Search Operations ====================

    async def find_nearby_devices(
        self,
        request: NearbySearchRequest,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Find devices near a location"""
        try:
            return await self.repository.find_nearby_devices(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_meters=request.radius_meters,
                user_id=user_id,
                time_window_minutes=request.time_window_minutes,
                device_types=request.device_types,
                limit=request.limit
            )

        except Exception as e:
            logger.error(f"Error finding nearby devices: {e}")
            return []

    async def search_radius(
        self,
        request: RadiusSearchRequest,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Search locations in a circular area"""
        try:
            return await self.repository.search_locations_in_radius(
                center_lat=request.center_lat,
                center_lon=request.center_lon,
                radius_meters=request.radius_meters,
                start_time=request.start_time,
                end_time=request.end_time,
                device_ids=request.device_ids,
                limit=request.limit
            )

        except Exception as e:
            logger.error(f"Error searching radius: {e}")
            return []

    @staticmethod
    def calculate_distance(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float
    ) -> Dict[str, float]:
        """Calculate distance between two points"""
        distance_m = LocationRepository.calculate_distance(from_lat, from_lon, to_lat, to_lon)
        return {
            'distance_meters': distance_m,
            'distance_km': distance_m / 1000
        }

    # ==================== Place Operations ====================

    async def create_place(
        self,
        request: PlaceCreateRequest,
        user_id: str
    ) -> LocationOperationResult:
        """Create a new place"""
        try:
            place_id = str(uuid.uuid4())

            place_data = {
                'place_id': place_id,
                'user_id': user_id,
                'name': request.name,
                'category': request.category,
                'latitude': request.latitude,
                'longitude': request.longitude,
                'address': request.address,
                'radius': request.radius,
                'icon': request.icon,
                'color': request.color,
                'tags': request.tags,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }

            result = await self.repository.create_place(place_data)

            if result:
                return LocationOperationResult(
                    success=True,
                    place_id=place_id,
                    operation="create_place",
                    message="Place created successfully",
                    data=result
                )
            else:
                return LocationOperationResult(
                    success=False,
                    operation="create_place",
                    message="Failed to create place"
                )

        except Exception as e:
            logger.error(f"Error creating place: {e}")
            return LocationOperationResult(
                success=False,
                operation="create_place",
                message=f"Error: {str(e)}"
            )

    async def get_place(
        self,
        place_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get place by ID"""
        try:
            place = await self.repository.get_place_by_id(place_id)

            # Verify user has access
            if place and place['user_id'] != user_id:
                logger.warning(f"User {user_id} attempted to access place {place_id}")
                return None

            return place

        except Exception as e:
            logger.error(f"Error getting place: {e}")
            return None

    async def list_user_places(self, user_id: str) -> List[Dict[str, Any]]:
        """List places for a user"""
        try:
            return await self.repository.list_user_places(user_id)

        except Exception as e:
            logger.error(f"Error listing places: {e}")
            return []

    async def update_place(
        self,
        place_id: str,
        request: PlaceUpdateRequest,
        user_id: str
    ) -> LocationOperationResult:
        """Update place"""
        try:
            # Verify ownership
            place = await self.repository.get_place_by_id(place_id)
            if not place or place['user_id'] != user_id:
                return LocationOperationResult(
                    success=False,
                    operation="update_place",
                    message="Place not found or access denied"
                )

            # Build update dict
            updates = {}
            for field, value in request.model_dump(exclude_unset=True).items():
                if value is not None:
                    updates[field] = value

            if updates:
                success = await self.repository.update_place(place_id, updates)

                if success:
                    return LocationOperationResult(
                        success=True,
                        place_id=place_id,
                        operation="update_place",
                        message="Place updated successfully"
                    )

            return LocationOperationResult(
                success=False,
                operation="update_place",
                message="No updates applied"
            )

        except Exception as e:
            logger.error(f"Error updating place: {e}")
            return LocationOperationResult(
                success=False,
                operation="update_place",
                message=f"Error: {str(e)}"
            )

    async def delete_place(
        self,
        place_id: str,
        user_id: str
    ) -> LocationOperationResult:
        """Delete place"""
        try:
            # Verify ownership
            place = await self.repository.get_place_by_id(place_id)
            if not place or place['user_id'] != user_id:
                return LocationOperationResult(
                    success=False,
                    operation="delete_place",
                    message="Place not found or access denied"
                )

            success = await self.repository.delete_place(place_id)

            if success:
                return LocationOperationResult(
                    success=True,
                    operation="delete_place",
                    message="Place deleted successfully"
                )
            else:
                return LocationOperationResult(
                    success=False,
                    operation="delete_place",
                    message="Failed to delete place"
                )

        except Exception as e:
            logger.error(f"Error deleting place: {e}")
            return LocationOperationResult(
                success=False,
                operation="delete_place",
                message=f"Error: {str(e)}"
            )

    # ==================== Statistics ====================

    async def get_location_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get location statistics for a user"""
        try:
            # Placeholder for statistics implementation
            return {
                'total_locations': 0,
                'active_devices': 0,
                'total_geofences': 0,
                'active_geofences': 0,
                'total_places': 0,
                'total_routes': 0
            }

        except Exception as e:
            logger.error(f"Error getting location statistics: {e}")
            return {}
