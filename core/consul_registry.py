"""
Consul Service Discovery Module

Provides service discovery functionality for microservices.
Service registration is handled by Consul agent sidecar (not programmatically).
"""

import consul
import logging
import asyncio
import socket
import json
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ConsulRegistry:
    """
    Consul Service Discovery Client

    NOTE: Service registration is handled by Consul agent sidecar.
    This class ONLY provides service discovery functionality.
    """

    def __init__(
        self,
        service_name: str = None,
        service_port: int = None,
        consul_host: str = "localhost",
        consul_port: int = 8500,
        service_host: Optional[str] = None,
        tags: Optional[List[str]] = None,
        health_check_type: str = "ttl"  # kept for backward compatibility
    ):
        """
        Initialize Consul service discovery client

        Args:
            service_name: (Optional) Name of the calling service (for logging)
            service_port: (Optional) Port of the calling service (for logging)
            consul_host: Consul server host
            consul_port: Consul server port

        Note: service_host, tags, health_check_type kept for backward compatibility but not used
        """
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.service_name = service_name
        self.service_port = service_port
        logger.info(f"Consul service discovery initialized: {consul_host}:{consul_port}")

        # Keep these for backward compatibility (not used for sidecar registration)
        import os
        if service_host and service_host != "0.0.0.0":
            self.service_host = service_host
        else:
            self.service_host = os.getenv('HOSTNAME', socket.gethostname())
        self.service_id = f"{service_name}-{self.service_host}-{service_port}" if service_name and service_port else "discovery-client"
        self.tags = tags or []

    # ========================================
    # Registration Methods (No-op - handled by Consul agent sidecar)
    # ========================================

    def cleanup_stale_registrations(self) -> int:
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping cleanup")
        return 0

    def register(self, cleanup_stale: bool = True) -> bool:
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping programmatic registration")
        return True

    def deregister(self) -> bool:
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping deregistration")
        return True

    async def maintain_registration(self):
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping maintenance")
        pass

    def start_maintenance(self):
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping maintenance start")
        pass

    def stop_maintenance(self):
        """No-op: Registration handled by Consul agent sidecar"""
        logger.debug("Registration handled by Consul agent sidecar, skipping maintenance stop")
        pass
    
    # Configuration Management Methods
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from Consul KV store"""
        try:
            full_key = f"{self.service_name}/{key}"
            index, data = self.consul.kv.get(full_key)
            if data and data.get('Value'):
                value = data['Value'].decode('utf-8')
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return default
        except Exception as e:
            logger.error(f"Failed to get config {key}: {e}")
            return default
    
    def set_config(self, key: str, value: Any) -> bool:
        """Set configuration value in Consul KV store"""
        try:
            full_key = f"{self.service_name}/{key}"
            # Convert to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            return self.consul.kv.put(full_key, value)
        except Exception as e:
            logger.error(f"Failed to set config {key}: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration for this service"""
        try:
            prefix = f"{self.service_name}/"
            index, data = self.consul.kv.get(prefix, recurse=True)
            if not data:
                return {}
            
            config = {}
            for item in data:
                if item['Value']:
                    key = item['Key'].replace(prefix, '')
                    value = item['Value'].decode('utf-8')
                    try:
                        config[key] = json.loads(value)
                    except json.JSONDecodeError:
                        config[key] = value
            return config
        except Exception as e:
            logger.error(f"Failed to get all config: {e}")
            return {}
    
    def watch_config(self, key: str, callback):
        """Watch for configuration changes (blocking call)"""
        full_key = f"{self.service_name}/{key}"
        index = None
        while True:
            try:
                index, data = self.consul.kv.get(full_key, index=index, wait='30s')
                if data:
                    value = data['Value'].decode('utf-8')
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                    callback(key, value)
            except Exception as e:
                logger.error(f"Error watching config {key}: {e}")
                break
    
    # Service Discovery Methods
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover healthy instances of a service"""
        try:
            # Get health checks for the service
            index, services = self.consul.health.service(service_name, passing=True)
            
            instances = []
            for service in services:
                instance = {
                    'id': service['Service']['ID'],
                    'address': service['Service']['Address'],
                    'port': service['Service']['Port'],
                    'tags': service['Service'].get('Tags', []),
                    'meta': service['Service'].get('Meta', {})
                }
                instances.append(instance)
            
            return instances
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return []
    
    def get_service_endpoint(self, service_name: str, strategy: str = 'health_weighted') -> Optional[str]:
        """Get a single service endpoint using advanced load balancing strategy"""
        instances = self.discover_service(service_name)
        if not instances:
            return None

        # 只有一个实例时直接返回
        if len(instances) == 1:
            instance = instances[0]
            return f"http://{instance['address']}:{instance['port']}"

        # 高级负载均衡策略
        if strategy == 'health_weighted':
            # 基于健康状态和权重选择最佳实例
            instance = self._select_best_instance(instances)
        elif strategy == 'random':
            import random
            instance = random.choice(instances)
        elif strategy == 'round_robin':
            # 实现真正的轮询（使用实例缓存）
            instance = self._get_round_robin_instance(service_name, instances)
        elif strategy == 'least_connections':
            # 选择连接数最少的实例（模拟实现）
            instance = min(instances, key=lambda x: hash(x['id']) % 100)
        else:
            # 默认随机选择
            import random
            instance = random.choice(instances)

        return f"http://{instance['address']}:{instance['port']}"
    
    def _select_best_instance(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最佳实例（基于健康状态和负载）"""
        # 简单实现：优先选择标签包含'preferred'的实例
        preferred_instances = [inst for inst in instances if 'preferred' in inst.get('tags', [])]
        if preferred_instances:
            import random
            return random.choice(preferred_instances)
        
        # 没有首选实例时随机选择
        import random
        return random.choice(instances)
    
    def _get_round_robin_instance(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """实现真正的轮询负载均衡"""
        if not hasattr(self, '_round_robin_counters'):
            self._round_robin_counters = {}
        
        if service_name not in self._round_robin_counters:
            self._round_robin_counters[service_name] = 0
        
        # 获取当前计数器并递增
        counter = self._round_robin_counters[service_name]
        self._round_robin_counters[service_name] = (counter + 1) % len(instances)
        
        return instances[counter]

    def _log_service_metrics(self, operation: str, success: bool, service_name: str = None):
        """记录服务操作指标"""
        service = service_name or self.service_name
        status = "SUCCESS" if success else "FAILED"
        
        # 使用项目统一的logger记录指标
        logger.info(
            f"🔍 CONSUL_METRICS | operation={operation} | service={service} | "
            f"status={status} | service_id={self.service_id}"
        )

    def get_service_address(self, service_name: str, fallback_url: Optional[str] = None, max_retries: int = 3) -> str:
        """
        Get service address from Consul discovery with automatic fallback and retry

        Args:
            service_name: Name of the service to discover
            fallback_url: Fallback URL if service not found in Consul (e.g., "http://localhost:8201")
            max_retries: Maximum number of discovery attempts

        Returns:
            Service URL (from Consul or fallback)

        Example:
            consul = ConsulRegistry("my_service", 8080)
            url = consul.get_service_address("account_service", "http://localhost:8201")
            # Returns: "http://10.0.1.5:8201" (from Consul) or "http://localhost:8201" (fallback)
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                endpoint = self.get_service_endpoint(service_name)
                if endpoint:
                    logger.debug(f"Discovered {service_name} at {endpoint} (attempt {attempt + 1})")
                    return endpoint
                    
                # 如果没找到服务但没有异常，记录并继续
                last_error = f"Service {service_name} not found in Consul registry"
                
            except Exception as e:
                last_error = e
                logger.warning(f"Consul discovery attempt {attempt + 1} failed for {service_name}: {e}")
                
                # 短暂等待后重试（除了最后一次）
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))  # 递增延迟

        # 所有重试都失败，使用fallback
        if fallback_url:
            logger.warning(f"All {max_retries} discovery attempts failed for {service_name}: {last_error}, using fallback: {fallback_url}")
            return fallback_url

        raise ValueError(f"Service {service_name} not found after {max_retries} attempts and no fallback provided. Last error: {last_error}")
    
    def watch_service(self, service_name: str, callback, wait_time: str = '30s'):
        """Watch for changes in service instances"""
        index = None
        while True:
            try:
                index, services = self.consul.health.service(
                    service_name, 
                    passing=True, 
                    index=index, 
                    wait=wait_time
                )
                # Convert to simplified format
                instances = []
                for service in services:
                    instances.append({
                        'id': service['Service']['ID'],
                        'address': service['Service']['Address'],
                        'port': service['Service']['Port']
                    })
                callback(service_name, instances)
            except Exception as e:
                logger.error(f"Error watching service {service_name}: {e}")
                break


@asynccontextmanager
async def consul_lifespan(
    app,
    service_name: str,
    service_port: int,
    consul_host: str = "localhost",
    consul_port: int = 8500,
    tags: Optional[List[str]] = None,
    health_check_type: str = "ttl"
):
    """
    FastAPI lifespan context manager for Consul registration
    
    Usage:
        app = FastAPI(lifespan=lambda app: consul_lifespan(app, "my-service", 8080))
    """
    # Startup
    # Use SERVICE_HOST env var if available, otherwise use hostname
    import os
    service_host = os.getenv('SERVICE_HOST', socket.gethostname())

    registry = ConsulRegistry(
        service_name=service_name,
        service_port=service_port,
        consul_host=consul_host,
        consul_port=consul_port,
        service_host=service_host,  # Use SERVICE_HOST from env or hostname
        tags=tags,
        health_check_type=health_check_type
    )
    
    # Register with Consul
    if registry.register():
        # Start maintenance task
        registry.start_maintenance()
        # Store in app state for access in routes
        app.state.consul_registry = registry
    else:
        logger.warning("Failed to register with Consul, continuing without service discovery")
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'consul_registry'):
        registry.stop_maintenance()
        registry.deregister()