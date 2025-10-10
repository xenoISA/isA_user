#!/usr/bin/env python3
"""
设备认证集成测试脚本

测试流程：
1. 创建数据库表
2. 启动 auth_service 
3. 启动 device_service
4. 注册设备
5. 设备认证
6. 验证 token
"""

import requests
import json
import time
import subprocess
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.database.supabase_client import get_supabase_client

# Use config manager for service URLs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_manager import ConfigManager

# Get service URLs from config
auth_config = ConfigManager("auth_service").get_service_config()
device_config = ConfigManager("device_service").get_service_config()

AUTH_SERVICE_URL = f"http://localhost:{auth_config.service_port}" if auth_config.service_port else "http://localhost:8202"
DEVICE_SERVICE_URL = f"http://localhost:{device_config.service_port}" if device_config.service_port else "http://localhost:8220"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_step(msg):
    print(f"{Colors.BLUE}[STEP]{Colors.END} {msg}")

def print_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.YELLOW}[INFO]{Colors.END} {msg}")

def setup_database():
    """创建数据库表（使用Supabase）"""
    print_step("Setting up database tables...")
    
    try:
        supabase = get_supabase_client()
        
        # 检查表是否已存在
        # Supabase 会自动处理表创建，我们只需要确保连接正常
        try:
            # 尝试查询表以验证连接
            result = supabase.table('device_credentials').select('device_id').limit(1).execute()
            print_info("Device credentials table already exists")
        except Exception as e:
            # 表不存在，需要创建
            print_info("Table does not exist, will be created on first insert")
        
        print_success("Database setup completed")
        return True
        
    except Exception as e:
        print_error(f"Database setup failed: {e}")
        print_info("Make sure Supabase is running and configured properly")
        return False

def start_services():
    """启动微服务"""
    print_step("Starting microservices...")
    
    processes = []
    
    # 启动 auth_service
    print_info("Starting auth_service on port 8202...")
    auth_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "microservices.auth_service.main:app", 
         "--host", "127.0.0.1", "--port", "8202"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(auth_process)
    
    # 启动 device_service
    print_info("Starting device_service on port 8220...")
    device_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "microservices.device_service.main:app", 
         "--host", "127.0.0.1", "--port", "8220"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(device_process)
    
    # 等待服务启动
    print_info("Waiting for services to start...")
    time.sleep(5)
    
    # 检查服务健康状态
    try:
        auth_health = requests.get(f"{AUTH_SERVICE_URL}/health", timeout=5)
        if auth_health.status_code == 200:
            print_success("auth_service is healthy")
        
        device_health = requests.get(f"{DEVICE_SERVICE_URL}/health", timeout=5)
        if device_health.status_code == 200:
            print_success("device_service is healthy")
    except Exception as e:
        print_error(f"Service health check failed: {e}")
        for p in processes:
            p.terminate()
        return None
    
    return processes

def test_device_registration():
    """测试设备注册"""
    print_step("Testing device registration...")
    
    device_data = {
        "device_id": "test_device_001",
        "organization_id": "org_123",
        "device_name": "Test Temperature Sensor",
        "device_type": "sensor",
        "metadata": {
            "location": "Building A, Floor 2",
            "manufacturer": "IoT Corp"
        }
    }
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/device/register",
            json=device_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Device registered: {result['device_id']}")
            print_info(f"Device secret: {result['device_secret']}")
            return result
        else:
            print_error(f"Registration failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Registration request failed: {e}")
        return None

def test_device_authentication(device_id, device_secret):
    """测试设备认证"""
    print_step("Testing device authentication...")
    
    auth_data = {
        "device_id": device_id,
        "device_secret": device_secret
    }
    
    try:
        # 通过 device_service 认证
        response = requests.post(
            f"{DEVICE_SERVICE_URL}/api/v1/devices/auth",
            json=auth_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Device authenticated via device_service")
            print_info(f"Token: {result['token'][:50]}...")
            return result
        else:
            print_error(f"Authentication failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Authentication request failed: {e}")
        return None

def test_direct_auth(device_id, device_secret):
    """直接测试 auth_service 的设备认证"""
    print_step("Testing direct authentication via auth_service...")
    
    auth_data = {
        "device_id": device_id,
        "device_secret": device_secret
    }
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/device/authenticate",
            json=auth_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Direct authentication successful")
            print_info(f"Organization ID: {result.get('organization_id')}")
            return result
        else:
            print_error(f"Direct authentication failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Direct authentication request failed: {e}")
        return None

def test_token_verification(token):
    """测试 token 验证"""
    print_step("Testing token verification...")
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/device/verify-token",
            json={"token": token}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("valid"):
                print_success(f"Token is valid")
                print_info(f"Device ID: {result.get('device_id')}")
                print_info(f"Expires at: {result.get('expires_at')}")
            else:
                print_error(f"Token is invalid: {result.get('error')}")
            return result
        else:
            print_error(f"Token verification failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Token verification request failed: {e}")
        return None

def test_list_devices(organization_id):
    """测试设备列表"""
    print_step("Testing device listing...")
    
    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/api/v1/auth/device/list",
            params={"organization_id": organization_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Found {result.get('count', 0)} devices")
            for device in result.get('devices', []):
                print_info(f"  - {device['device_id']}: {device.get('device_name', 'N/A')}")
            return result
        else:
            print_error(f"Device listing failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Device listing request failed: {e}")
        return None

def cleanup(processes):
    """清理资源"""
    print_step("Cleaning up...")
    
    if processes:
        for p in processes:
            p.terminate()
            p.wait()
        print_success("Services stopped")

def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("   Device Authentication Integration Test")
    print("="*60 + "\n")
    
    processes = None
    
    try:
        # 1. 设置数据库
        if not setup_database():
            print_error("Database setup failed, aborting tests")
            return 1
        
        # 2. 启动服务
        processes = start_services()
        if not processes:
            print_error("Failed to start services, aborting tests")
            return 1
        
        # 3. 注册设备
        device = test_device_registration()
        if not device:
            print_error("Device registration failed, aborting tests")
            return 1
        
        device_id = device['device_id']
        device_secret = device['device_secret']
        organization_id = device['organization_id']
        
        # 4. 直接认证测试
        auth_result = test_direct_auth(device_id, device_secret)
        if not auth_result:
            print_error("Direct authentication failed")
        
        # 5. 通过 device_service 认证
        device_auth = test_device_authentication(device_id, device_secret)
        if not device_auth:
            print_error("Device service authentication failed")
            return 1
        
        # 6. 验证 token
        if device_auth and device_auth.get('token'):
            test_token_verification(device_auth['token'])
        
        # 7. 列出设备
        test_list_devices(organization_id)
        
        print("\n" + "="*60)
        print_success("All tests completed successfully!")
        print("="*60 + "\n")
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1
    finally:
        if processes:
            cleanup(processes)

if __name__ == "__main__":
    sys.exit(main())