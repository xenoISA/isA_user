"""
Unit Tests for core.mqtt_client

Tests the MQTTEventBus and related components using mocked AsyncMQTTClient.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# Mock the isa_common imports before importing mqtt_client
@pytest.fixture(autouse=True)
def mock_isa_common():
    """Mock AsyncMQTTClient from isa_common"""
    with patch.dict('sys.modules', {'isa_common': MagicMock()}):
        yield


class TestMQTTTopics:
    """Test MQTTTopics helper class"""

    def test_device_commands_topic(self):
        """Test device commands topic generation"""
        from core.mqtt_client import MQTTTopics

        topic = MQTTTopics.device_commands("device-123")
        assert topic == "devices/device-123/commands"

    def test_device_status_topic(self):
        """Test device status topic generation"""
        from core.mqtt_client import MQTTTopics

        topic = MQTTTopics.device_status("device-456")
        assert topic == "devices/device-456/status"

    def test_sensor_readings_topic(self):
        """Test sensor readings topic generation"""
        from core.mqtt_client import MQTTTopics

        topic = MQTTTopics.sensor_readings("sensor-789")
        assert topic == "sensors/sensor-789/readings"

    def test_alerts_topic(self):
        """Test alerts topic generation"""
        from core.mqtt_client import MQTTTopics

        topic = MQTTTopics.alerts("temperature")
        assert topic == "alerts/temperature"


class TestMQTTEventBus:
    """Test MQTTEventBus class"""

    @pytest.fixture
    def mock_async_mqtt_client(self):
        """Create a mocked AsyncMQTTClient"""
        mock_client = MagicMock()
        mock_client.mqtt_connect = AsyncMock(return_value={"session_id": "test-session-123"})
        mock_client.disconnect = AsyncMock(return_value={"success": True})
        mock_client.publish = AsyncMock(return_value={"success": True})
        mock_client.publish_json = AsyncMock(return_value={"success": True})
        mock_client.publish_batch = AsyncMock(return_value={"published_count": 3, "failed_count": 0})
        mock_client.register_device = AsyncMock(return_value={"success": True})
        mock_client.update_device_status = AsyncMock(return_value={"success": True})
        mock_client.get_statistics = AsyncMock(return_value={"total_devices": 10})
        mock_client.health_check = AsyncMock(return_value={"status": "healthy"})

        # Mock context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        return mock_client

    @pytest.fixture
    def mock_config_manager(self):
        """Mock ConfigManager"""
        mock_config = MagicMock()
        mock_config.mqtt_host = "localhost"
        mock_config.mqtt_port = 50053

        mock_manager = MagicMock()
        mock_manager.get_service_config.return_value = mock_config

        return mock_manager

    @pytest.mark.asyncio
    async def test_connect(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus connect"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client

                result = await bus.connect()

                assert result is True
                assert bus.connected is True
                assert bus.session_id == "test-session-123"

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus disconnect"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                result = await bus.disconnect()

                assert result is True
                assert bus.connected is False
                assert bus.session_id is None

    @pytest.mark.asyncio
    async def test_publish_json(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus publish_json"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                data = {"test": "message", "value": 42}
                result = await bus.publish_json("test/topic", data, qos=1)

                assert result is True
                mock_async_mqtt_client.publish_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_batch(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus publish_batch"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                messages = [
                    {"topic": "t1", "payload": b"msg1", "qos": 1},
                    {"topic": "t2", "payload": b"msg2", "qos": 1},
                    {"topic": "t3", "payload": b"msg3", "qos": 1},
                ]

                result = await bus.publish_batch(messages)

                assert result["published_count"] == 3
                assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_send_device_command(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus send_device_command"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                command_id = await bus.send_device_command(
                    device_id="device-123",
                    command="restart",
                    parameters={"force": True},
                    timeout=60
                )

                assert command_id is not None
                assert len(command_id) == 32  # hex(16) = 32 chars

    @pytest.mark.asyncio
    async def test_publish_device_status(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus publish_device_status"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                result = await bus.publish_device_status(
                    device_id="device-123",
                    status="online",
                    metadata={"battery": 85}
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_publish_alert(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus publish_alert"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client
                bus.session_id = "test-session"
                bus.connected = True

                result = await bus.publish_alert(
                    alert_type="temperature",
                    message="High temperature detected",
                    severity="WARNING",
                    source="sensor-123"
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_register_device(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus register_device"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client

                result = await bus.register_device(
                    device_id="new-device",
                    device_name="Test Device",
                    device_type="sensor",
                    metadata={"location": "room1"}
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self, mock_async_mqtt_client, mock_config_manager):
        """Test MQTTEventBus health_check"""
        with patch('core.mqtt_client.AsyncMQTTClient', return_value=mock_async_mqtt_client):
            with patch('core.mqtt_client.ConfigManager', return_value=mock_config_manager):
                from core.mqtt_client import MQTTEventBus

                bus = MQTTEventBus(service_name="test_service")
                bus.client = mock_async_mqtt_client

                result = await bus.health_check()

                assert result["status"] == "healthy"


class TestDeviceCommandClient:
    """Test DeviceCommandClient class"""

    @pytest.fixture
    def mock_mqtt_bus(self):
        """Create mocked MQTTEventBus"""
        mock_bus = MagicMock()
        mock_bus.connect = AsyncMock(return_value=True)
        mock_bus.disconnect = AsyncMock()
        mock_bus.send_device_command = AsyncMock(return_value="cmd-123")
        mock_bus.send_ota_command = AsyncMock(return_value="ota-456")
        mock_bus.connected = True
        return mock_bus

    @pytest.mark.asyncio
    async def test_connect(self, mock_mqtt_bus):
        """Test DeviceCommandClient connect"""
        with patch('core.mqtt_client.MQTTEventBus', return_value=mock_mqtt_bus):
            from core.mqtt_client import DeviceCommandClient

            client = DeviceCommandClient()
            client.mqtt_bus = mock_mqtt_bus

            result = await client.connect()

            assert result is True

    @pytest.mark.asyncio
    async def test_send_device_command(self, mock_mqtt_bus):
        """Test DeviceCommandClient send_device_command"""
        with patch('core.mqtt_client.MQTTEventBus', return_value=mock_mqtt_bus):
            from core.mqtt_client import DeviceCommandClient

            client = DeviceCommandClient()
            client.mqtt_bus = mock_mqtt_bus

            command_id = await client.send_device_command(
                device_id="device-123",
                command="restart"
            )

            assert command_id == "cmd-123"

    @pytest.mark.asyncio
    async def test_send_ota_command(self, mock_mqtt_bus):
        """Test DeviceCommandClient send_ota_command"""
        with patch('core.mqtt_client.MQTTEventBus', return_value=mock_mqtt_bus):
            from core.mqtt_client import DeviceCommandClient

            client = DeviceCommandClient()
            client.mqtt_bus = mock_mqtt_bus

            command_id = await client.send_ota_command(
                device_id="device-123",
                firmware_url="https://example.com/fw.bin",
                version="1.2.0",
                checksum="abc123"
            )

            assert command_id == "ota-456"

    def test_is_connected(self, mock_mqtt_bus):
        """Test DeviceCommandClient is_connected"""
        with patch('core.mqtt_client.MQTTEventBus', return_value=mock_mqtt_bus):
            from core.mqtt_client import DeviceCommandClient

            client = DeviceCommandClient()
            client.mqtt_bus = mock_mqtt_bus

            assert client.is_connected() is True


class TestAlbumMQTTPublisher:
    """Test AlbumMQTTPublisher class"""

    @pytest.fixture
    def mock_mqtt_bus(self):
        """Create mocked MQTTEventBus for album publisher"""
        mock_bus = MagicMock()
        mock_bus.connect = AsyncMock(return_value=True)
        mock_bus.close = AsyncMock()
        mock_bus.publish_json = AsyncMock(return_value=True)
        mock_bus.connected = True
        return mock_bus

    @pytest.mark.asyncio
    async def test_publish_photo_added(self, mock_mqtt_bus):
        """Test AlbumMQTTPublisher publish_photo_added"""
        with patch('microservices.album_service.mqtt.publisher.MQTTEventBus', return_value=mock_mqtt_bus):
            from microservices.album_service.mqtt.publisher import AlbumMQTTPublisher

            publisher = AlbumMQTTPublisher()
            publisher.mqtt_bus = mock_mqtt_bus
            publisher._initialized = True

            result = await publisher.publish_photo_added(
                album_id="album-123",
                file_id="file-456",
                photo_metadata={
                    "file_name": "test.jpg",
                    "content_type": "image/jpeg",
                    "file_size": 1024
                }
            )

            assert result is True
            mock_mqtt_bus.publish_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_photo_removed(self, mock_mqtt_bus):
        """Test AlbumMQTTPublisher publish_photo_removed"""
        with patch('microservices.album_service.mqtt.publisher.MQTTEventBus', return_value=mock_mqtt_bus):
            from microservices.album_service.mqtt.publisher import AlbumMQTTPublisher

            publisher = AlbumMQTTPublisher()
            publisher.mqtt_bus = mock_mqtt_bus
            publisher._initialized = True

            result = await publisher.publish_photo_removed(
                album_id="album-123",
                file_id="file-456"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_album_sync(self, mock_mqtt_bus):
        """Test AlbumMQTTPublisher publish_album_sync"""
        with patch('microservices.album_service.mqtt.publisher.MQTTEventBus', return_value=mock_mqtt_bus):
            from microservices.album_service.mqtt.publisher import AlbumMQTTPublisher

            publisher = AlbumMQTTPublisher()
            publisher.mqtt_bus = mock_mqtt_bus
            publisher._initialized = True

            photos = [
                {"file_id": "f1", "name": "photo1.jpg"},
                {"file_id": "f2", "name": "photo2.jpg"},
            ]

            result = await publisher.publish_album_sync(
                album_id="album-123",
                frame_id="frame-789",
                photos=photos
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_frame_command(self, mock_mqtt_bus):
        """Test AlbumMQTTPublisher publish_frame_command"""
        with patch('microservices.album_service.mqtt.publisher.MQTTEventBus', return_value=mock_mqtt_bus):
            from microservices.album_service.mqtt.publisher import AlbumMQTTPublisher

            publisher = AlbumMQTTPublisher()
            publisher.mqtt_bus = mock_mqtt_bus
            publisher._initialized = True

            result = await publisher.publish_frame_command(
                frame_id="frame-789",
                command="refresh",
                parameters={"delay": 5}
            )

            assert result is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
