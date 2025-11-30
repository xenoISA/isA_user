#!/bin/bash

# 微服务列表 (service_name:port)
SERVICES=(
    "auth_service:8201"
    "account_service:8202"
    "session_service:8203"
    "authorization_service:8204"
    "audit_service:8205"
    "notification_service:8206"
    "payment_service:8207"
    "wallet_service:8208"
    "storage_service:8209"
    "order_service:8210"
    "task_service:8211"
    "organization_service:8212"
    "invitation_service:8213"
    "vault_service:8214"
    "product_service:8215"
    "billing_service:8216"
    "calendar_service:8217"
    "weather_service:8218"
    "album_service:8219"
    "device_service:8220"
    "ota_service:8221"
    "media_service:8222"
    "memory_service:8223"
    "location_service:8224"
    "telemetry_service:8225"
    "compliance_service:8226"
    "document_service:8227"
    "event_service:8230"
)

NAMESPACE="isa-cloud-staging"
OUTPUT_DIR="manifests"

mkdir -p $OUTPUT_DIR

for svc in "${SERVICES[@]}"; do
    IFS=':' read -r service_name port <<< "$svc"
    
    # 生成短名称 (去掉 _service 后缀)
    short_name="${service_name%_service}"
    
    # 生成环境变量名
    env_var_name=$(echo "${service_name}" | tr '[:lower:]' '[:upper:]')_PORT
    
    echo "Generating manifest for $service_name..."
    
    cat > $OUTPUT_DIR/${short_name}-deployment.yaml <<EOFMANIFEST
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${short_name}
  namespace: ${NAMESPACE}
  labels:
    app: ${short_name}
    tier: applications
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${short_name}
  template:
    metadata:
      labels:
        app: ${short_name}
        tier: applications
    spec:
      enableServiceLinks: false
      containers:
        - name: ${short_name}
          image: isa-${short_name}:latest
          imagePullPolicy: IfNotPresent
          
          ports:
            - name: http
              containerPort: ${port}
          
          envFrom:
            - configMapRef:
                name: user-config
          
          env:
            - name: SERVICE_NAME
              value: "${service_name}"
            - name: ${env_var_name}
              value: "${port}"
            - name: SERVICE_HOST
              value: "${short_name}.${NAMESPACE}.svc.cluster.local"
          
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 1Gi
          
          livenessProbe:
            httpGet:
              path: /health
              port: ${port}
            initialDelaySeconds: 60
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          
          readinessProbe:
            httpGet:
              path: /health
              port: ${port}
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: ${short_name}
  namespace: ${NAMESPACE}
  labels:
    app: ${short_name}
    tier: applications
spec:
  type: ClusterIP
  selector:
    app: ${short_name}
  ports:
    - name: http
      port: ${port}
      targetPort: ${port}
      protocol: TCP
EOFMANIFEST

done

echo "All manifests generated in $OUTPUT_DIR/"
