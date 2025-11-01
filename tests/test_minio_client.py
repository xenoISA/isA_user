#!/usr/bin/env python3
"""
完整的 MinIO gRPC 远程访问客户端
文件名: test_minio_remote_client.py

这个脚本演示如何从远程服务访问 MinIO gRPC 服务，并实际调用服务方法。
"""

import grpc
import sys
from datetime import datetime

# 导入生成的 proto 文件
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_user/tests')
from proto import minio_service_pb2
from proto import minio_service_pb2_grpc


class MinIORemoteClient:
    """MinIO gRPC 远程客户端"""
    
    def __init__(self, host='localhost', port=50051):
        """
        初始化客户端
        
        Args:
            host: 服务器地址
                  - 本地: 'localhost'
                  - 局域网: '192.168.31.62'
                  - 公网: 'your-server.com'
            port: 服务端口（默认 50051）
        
        示例:
            # 本地访问
            client = MinIORemoteClient('localhost', 50051)
            
            # 远程访问
            client = MinIORemoteClient('192.168.31.62', 50051)
        """
        self.host = host
        self.port = port
        self.address = f'{host}:{port}'
        
        print(f"🔗 连接到 MinIO gRPC 服务: {self.address}")
        
        # 创建 gRPC channel
        # 注意: 生产环境应该使用 secure_channel
        self.channel = grpc.insecure_channel(
            self.address,
            options=[
                ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
                ('grpc.max_send_message_length', 100 * 1024 * 1024),     # 100MB
                ('grpc.keepalive_time_ms', 10000),
                ('grpc.keepalive_timeout_ms', 5000),
            ]
        )
        
        # 创建 stub
        self.stub = minio_service_pb2_grpc.MinIOServiceStub(self.channel)
        
        # 测试连接
        try:
            grpc.channel_ready_future(self.channel).result(timeout=5)
            print(f"✅ 连接成功!\n")
        except Exception as e:
            print(f"❌ 连接失败: {e}\n")
            raise
    
    def health_check(self, detailed=True):
        """
        健康检查
        
        Args:
            detailed: 是否返回详细信息
        
        Returns:
            HealthCheckResponse
        """
        print("=" * 60)
        print("测试 1: 健康检查 (HealthCheck)")
        print("=" * 60)
        
        try:
            request = minio_service_pb2.HealthCheckRequest(detailed=detailed)
            response = self.stub.HealthCheck(request)
            
            print(f"✅ 服务状态: {response.status}")
            print(f"   健康: {response.healthy}")
            print(f"   成功: {response.success}")
            if response.details:
                print(f"   详细信息: {dict(response.details)}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def create_bucket(self, bucket_name, user_id, organization_id='remote-org'):
        """
        创建存储桶
        
        Args:
            bucket_name: 桶名称
            user_id: 用户 ID
            organization_id: 组织 ID
        
        Returns:
            CreateBucketResponse
        """
        print("\n" + "=" * 60)
        print(f"测试 2: 创建存储桶 (CreateBucket)")
        print("=" * 60)
        print(f"桶名称: {bucket_name}")
        print(f"用户 ID: {user_id}")
        print(f"组织 ID: {organization_id}")
        
        try:
            request = minio_service_pb2.CreateBucketRequest(
                bucket_name=bucket_name,
                user_id=user_id,
                organization_id=organization_id,
                region='us-east-1'
            )
            
            response = self.stub.CreateBucket(request)
            
            if response.success:
                print(f"✅ 桶创建成功!")
                if response.bucket_info:
                    print(f"   名称: {response.bucket_info.name}")
                    print(f"   所有者: {response.bucket_info.owner_id}")
                    print(f"   组织: {response.bucket_info.organization_id}")
            else:
                print(f"⚠️  {response.message or response.error}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def list_buckets(self, user_id, organization_id='remote-org'):
        """
        列出存储桶
        
        Args:
            user_id: 用户 ID
            organization_id: 组织 ID
        
        Returns:
            ListBucketsResponse
        """
        print("\n" + "=" * 60)
        print(f"测试 3: 列出存储桶 (ListBuckets)")
        print("=" * 60)
        
        try:
            request = minio_service_pb2.ListBucketsRequest(
                user_id=user_id,
                organization_id=organization_id
            )
            
            response = self.stub.ListBuckets(request)
            
            if response.success:
                print(f"✅ 找到 {len(response.buckets)} 个桶:")
                for i, bucket in enumerate(response.buckets, 1):
                    print(f"   {i}. {bucket.name}")
                    print(f"      所有者: {bucket.owner_id}")
                    print(f"      组织: {bucket.organization_id}")
            else:
                print(f"⚠️  {response.error}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def upload_object(self, bucket_name, object_key, data, user_id, content_type='text/plain'):
        """
        上传对象（流式）
        
        Args:
            bucket_name: 桶名称
            object_key: 对象键（路径）
            data: 二进制数据
            user_id: 用户 ID
            content_type: 内容类型
        
        Returns:
            PutObjectResponse
        """
        print("\n" + "=" * 60)
        print(f"测试 4: 上传对象 (PutObject - 流式)")
        print("=" * 60)
        print(f"桶: {bucket_name}")
        print(f"对象键: {object_key}")
        print(f"数据大小: {len(data)} bytes")
        print(f"内容类型: {content_type}")
        
        try:
            def request_generator():
                # 第一个消息：元数据
                metadata = minio_service_pb2.PutObjectMetadata(
                    bucket_name=bucket_name,
                    object_key=object_key,
                    user_id=user_id,
                    content_type=content_type,
                    content_length=len(data)
                )
                yield minio_service_pb2.PutObjectRequest(metadata=metadata)
                
                # 后续消息：数据块
                chunk_size = 1024 * 64  # 64KB chunks
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    yield minio_service_pb2.PutObjectRequest(chunk=chunk)
                    print(f"   上传进度: {min(i + chunk_size, len(data))}/{len(data)} bytes")
            
            response = self.stub.PutObject(request_generator())
            
            if response.success:
                print(f"✅ 对象上传成功!")
                print(f"   对象键: {response.object_key}")
                print(f"   大小: {response.size} bytes")
                print(f"   ETag: {response.etag}")
            else:
                print(f"⚠️  {response.error}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def list_objects(self, bucket_name, user_id, prefix=''):
        """
        列出对象
        
        Args:
            bucket_name: 桶名称
            user_id: 用户 ID
            prefix: 前缀过滤
        
        Returns:
            ListObjectsResponse
        """
        print("\n" + "=" * 60)
        print(f"测试 5: 列出对象 (ListObjects)")
        print("=" * 60)
        print(f"桶: {bucket_name}")
        
        try:
            request = minio_service_pb2.ListObjectsRequest(
                bucket_name=bucket_name,
                user_id=user_id,
                prefix=prefix,
                max_keys=100
            )
            
            response = self.stub.ListObjects(request)
            
            if response.success:
                print(f"✅ 找到 {len(response.objects)} 个对象:")
                for i, obj in enumerate(response.objects, 1):
                    print(f"   {i}. {obj.key}")
                    print(f"      大小: {obj.size} bytes")
                    print(f"      类型: {obj.content_type}")
                    print(f"      ETag: {obj.etag}")
            else:
                print(f"⚠️  {response.error}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def get_presigned_url(self, bucket_name, object_key, user_id, expiry_seconds=3600):
        """
        获取预签名 URL
        
        Args:
            bucket_name: 桶名称
            object_key: 对象键
            user_id: 用户 ID
            expiry_seconds: 过期时间（秒）
        
        Returns:
            GetPresignedURLResponse
        """
        print("\n" + "=" * 60)
        print(f"测试 6: 获取预签名 URL (GetPresignedURL)")
        print("=" * 60)
        
        try:
            request = minio_service_pb2.GetPresignedURLRequest(
                bucket_name=bucket_name,
                object_key=object_key,
                user_id=user_id,
                expiry_seconds=expiry_seconds
            )
            
            response = self.stub.GetPresignedURL(request)
            
            if response.success:
                print(f"✅ 预签名 URL 生成成功!")
                print(f"   URL: {response.url[:80]}...")
                print(f"   过期时间: {response.expires_at}")
            else:
                print(f"⚠️  {response.error}")
            
            return response
            
        except grpc.RpcError as e:
            print(f"❌ RPC 错误: {e.code()}")
            print(f"   详情: {e.details()}")
            return None
    
    def close(self):
        """关闭连接"""
        self.channel.close()
        print("\n" + "=" * 60)
        print("🔌 连接已关闭")
        print("=" * 60)


def main():
    """主测试函数"""
    print("=" * 60)
    print("  MinIO gRPC 远程访问完整测试")
    print("=" * 60)
    print()
    print("📍 服务信息:")
    print("   容器: isa-minio-grpc")
    print("   端口映射: 0.0.0.0:50051->50051/tcp")
    print()
    print("🌐 支持的访问方式:")
    print("   1. 本地访问: localhost:50051")
    print("   2. 局域网访问: 192.168.31.62:50051")
    print("   3. 公网访问: <公网IP>:50051 (需配置)")
    print()
    
    # 询问使用哪种访问方式
    print("请选择访问方式:")
    print("  1 - 本地访问 (localhost)")
    print("  2 - 局域网远程访问 (192.168.31.62)")
    print("  3 - 自定义地址")
    
    choice = input("\n选择 [1]: ").strip() or "1"
    
    if choice == "1":
        host = 'localhost'
    elif choice == "2":
        host = '192.168.31.62'
    elif choice == "3":
        host = input("请输入服务器地址: ").strip()
    else:
        host = 'localhost'
    
    print()
    
    try:
        # 创建客户端
        client = MinIORemoteClient(host=host, port=50051)
        
        # 测试参数
        test_user_id = f'remote-user-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        test_bucket_name = f'remote-test-bucket-{datetime.now().strftime("%H%M%S")}'
        test_object_key = 'test-file.txt'
        test_data = f"Hello from remote gRPC client!\nTimestamp: {datetime.now()}\nHost: {host}\n".encode()
        
        print(f"📋 测试参数:")
        print(f"   用户 ID: {test_user_id}")
        print(f"   桶名称: {test_bucket_name}")
        print(f"   对象键: {test_object_key}")
        print()
        
        # 执行测试
        # 1. 健康检查
        client.health_check(detailed=True)
        
        # 2. 创建桶
        client.create_bucket(
            bucket_name=test_bucket_name,
            user_id=test_user_id,
            organization_id='remote-test-org'
        )
        
        # 3. 列出桶
        client.list_buckets(user_id=test_user_id)
        
        # 4. 上传对象
        client.upload_object(
            bucket_name=test_bucket_name,
            object_key=test_object_key,
            data=test_data,
            user_id=test_user_id,
            content_type='text/plain'
        )
        
        # 5. 列出对象
        client.list_objects(
            bucket_name=test_bucket_name,
            user_id=test_user_id
        )
        
        # 6. 获取预签名 URL
        client.get_presigned_url(
            bucket_name=test_bucket_name,
            object_key=test_object_key,
            user_id=test_user_id,
            expiry_seconds=3600
        )
        
        # 关闭连接
        client.close()
        
        print()
        print("=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        print()
        print("💡 代码示例 (在其他项目中使用):")
        print()
        print("```python")
        print("import grpc")
        print("from proto import minio_service_pb2, minio_service_pb2_grpc")
        print()
        print(f"# 连接到远程服务")
        print(f"channel = grpc.insecure_channel('{host}:50051')")
        print("stub = minio_service_pb2_grpc.MinIOServiceStub(channel)")
        print()
        print("# 调用服务方法")
        print("request = minio_service_pb2.HealthCheckRequest(detailed=True)")
        print("response = stub.HealthCheck(request)")
        print("print(f'健康状态: {response.healthy}')")
        print()
        print("channel.close()")
        print("```")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()



