#!/bin/bash

# 为每个服务的 manifest 添加 SERVICE_HOST_OVERRIDE 环境变量

MANIFESTS_DIR="manifests"

for manifest in $MANIFESTS_DIR/*-deployment.yaml; do
    service_name=$(basename "$manifest" | sed 's/-deployment.yaml//')
    
    echo "Fixing $service_name..."
    
    # 使用 yq 或 sed 添加环境变量
    # 在 env 部分添加 SERVICE_HOST_OVERRIDE
    sed -i.bak "/name: SERVICE_NAME/a\\
            - name: SERVICE_HOST_OVERRIDE\\
              value: \"${service_name}.isa-cloud-staging.svc.cluster.local\"" "$manifest"
done

echo "All manifests fixed. Backup files saved with .bak extension"
