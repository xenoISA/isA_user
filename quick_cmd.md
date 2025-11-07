  📝 常用命令：

  # 重启服务
  docker exec user-staging supervisorctl restart auth_service

  # 查看状态
  docker exec user-staging supervisorctl status
  docker exec user-staging supervisorctl status auth_service

  # 停止/启动服务
  docker exec user-staging supervisorctl stop auth_service
  docker exec user-staging supervisorctl start auth_service

  # 查看日志（因为日志输出到 stdout）
  docker logs -f user-staging | grep "auth_service"