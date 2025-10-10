# Service Port Mapping

## 标准端口分配

| Service Name | Port | Environment Variable |
|-------------|------|---------------------|
| auth_service | 8201 | AUTH_SERVICE_PORT |
| account_service | 8202 | ACCOUNT_SERVICE_PORT |
| session_service | 8203 | SESSION_SERVICE_PORT |
| authorization_service | 8204 | AUTHORIZATION_SERVICE_PORT |
| audit_service | 8205 | AUDIT_SERVICE_PORT |
| notification_service | 8206 | NOTIFICATION_SERVICE_PORT |
| payment_service | 8207 | PAYMENT_SERVICE_PORT |
| wallet_service | 8208 | WALLET_SERVICE_PORT |
| storage_service | 8209 | STORAGE_SERVICE_PORT |
| order_service | 8210 | ORDER_SERVICE_PORT |
| task_service | 8211 | TASK_SERVICE_PORT |
| organization_service | 8212 | ORGANIZATION_SERVICE_PORT |
| invitation_service | 8213 | INVITATION_SERVICE_PORT |
| vault_service | 8214 | VAULT_SERVICE_PORT |
| device_service | 8220 | DEVICE_SERVICE_PORT |
| ota_service | 8221 | OTA_SERVICE_PORT |
| telemetry_service | 8225 | TELEMETRY_SERVICE_PORT |
| event_service | 8230 | EVENT_SERVICE_PORT |

## 注意事项

1. ConfigManager 会自动查找 `{SERVICE_NAME}_PORT` 格式的环境变量
2. 服务启动时使用 `config.service_port` 获取端口
3. Consul 注册时使用实际监听的端口