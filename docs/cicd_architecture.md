# CI/CD Architecture for isA_user Platform

## Overview

This document outlines the Continuous Integration and Continuous Deployment (CI/CD) strategy for the isA_user microservices platform, covering both local Kind Kubernetes clusters and cloud-based Kubernetes deployments.

## Architecture Principles

1. **Environment Parity**: Local Kind environments mirror production as closely as possible
2. **Automated Testing**: All changes go through automated testing before deployment
3. **Progressive Delivery**: Deploy to staging before production
4. **Rollback Capability**: Easy rollback to previous versions
5. **Security First**: Secrets management and vulnerability scanning
6. **Observability**: Built-in monitoring and logging

## Deployment Environments

### 1. Local Development (Kind Kubernetes)

**Purpose**: Developer testing and integration testing

**Infrastructure**:
- Kind cluster: `isa-cloud-local`
- Nodes: 1 control-plane + 2 workers
- Namespace: `isa-cloud-staging`
- Local Docker registry for images

**Characteristics**:
- Fast iteration cycles
- Full microservices stack
- Port-forwarding for external access
- Suitable for E2E testing

### 2. Cloud Staging (Cloud Kubernetes)

**Purpose**: Pre-production validation

**Infrastructure**:
- Managed Kubernetes (GKE/EKS/AKS)
- Namespace: `staging`
- Cloud-native storage and networking
- Load balancers and ingress controllers

**Characteristics**:
- Production-like environment
- External accessibility
- Integration with cloud services
- Performance testing

### 3. Cloud Production (Cloud Kubernetes)

**Purpose**: Live user traffic

**Infrastructure**:
- Managed Kubernetes with HA
- Namespace: `production`
- Auto-scaling enabled
- Multi-zone deployment
- CDN and edge caching

**Characteristics**:
- High availability
- Auto-scaling
- Monitoring and alerting
- Disaster recovery

---

## CI/CD Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Code Changes                             │
│                    (Push to GitHub)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CI: Continuous Integration                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Lint &     │  │  Unit Tests  │  │Build Docker  │         │
│  │   Format     │─▶│              │─▶│   Images     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Local Kind K8s Testing (Optional)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Deploy to   │  │ Integration  │  │  E2E Tests   │         │
│  │  Kind        │─▶│    Tests     │─▶│              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                CD: Continuous Deployment                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            Push to Container Registry                 │       │
│  │         (Docker Hub / ECR / GCR / ACR)               │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                           │
│         ┌─────────────┴─────────────┐                           │
│         ▼                           ▼                            │
│  ┌─────────────┐            ┌─────────────┐                    │
│  │  Deploy to  │            │  Deploy to  │                    │
│  │  Staging    │            │ Production  │                    │
│  │             │            │ (Manual/Auto)│                    │
│  └─────┬───────┘            └─────┬───────┘                    │
│        │                          │                              │
│        ▼                          ▼                              │
│  ┌─────────────┐            ┌─────────────┐                    │
│  │  Smoke Tests│            │ Canary/Blue │                    │
│  │             │            │ Green Deploy│                    │
│  └─────────────┘            └─────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## GitHub Actions Workflows

### Workflow 1: CI - Build and Test

**File**: `.github/workflows/ci.yml`

**Triggers**:
- Push to `main`, `develop`, or `release/*` branches
- Pull requests

**Steps**:
1. Checkout code
2. Set up Python environment
3. Install dependencies
4. Run linters (flake8, black)
5. Run unit tests with coverage
6. Build Docker images for changed services
7. Push images to registry (tagged with commit SHA)
8. Upload test reports

**Artifacts**:
- Test coverage reports
- Docker images (tagged with SHA)

---

### Workflow 2: Local Kind Integration Tests

**File**: `.github/workflows/kind-integration.yml`

**Triggers**:
- Manual dispatch
- Scheduled (nightly)
- After CI passes on `develop` branch

**Steps**:
1. Checkout code
2. Set up Kind cluster
3. Install infrastructure (PostgreSQL, NATS, MQTT, MinIO, Consul)
4. Deploy all microservices
5. Run integration tests
6. Run E2E tests (photo sharing, billing flow, etc.)
7. Collect logs and artifacts
8. Tear down cluster

**Artifacts**:
- Integration test results
- Service logs
- Performance metrics

---

### Workflow 3: Deploy to Cloud Staging

**File**: `.github/workflows/deploy-staging.yml`

**Triggers**:
- Push to `develop` branch (after CI and Kind tests pass)
- Manual dispatch

**Steps**:
1. Checkout code
2. Authenticate with cloud provider
3. Pull Docker images from registry
4. Apply Kubernetes manifests to staging namespace
5. Wait for rollout completion
6. Run smoke tests
7. Notify team (Slack/Discord)

**Secrets Required**:
- `KUBE_CONFIG_STAGING`: Kubernetes config for staging cluster
- `CLOUD_CREDENTIALS`: Cloud provider credentials
- `REGISTRY_TOKEN`: Container registry access token

---

### Workflow 4: Deploy to Cloud Production

**File**: `.github/workflows/deploy-production.yml`

**Triggers**:
- Manual approval after staging validation
- Push to `main` branch (with approval gate)

**Steps**:
1. Checkout code
2. Authenticate with cloud provider
3. Pull tested images from staging
4. Apply production Kubernetes manifests
5. Perform canary deployment (10% → 50% → 100%)
6. Monitor error rates and performance
7. Automatic rollback on failure
8. Notify team and update status page

**Approval Gates**:
- Requires manual approval from team lead
- Staging must be healthy for 24 hours
- All critical tests must pass

---

## Build and Deploy Scripts

### 1. Build Script for Services

**Location**: `deployment/k8s/build-all-images.sh`

**Usage**:
```bash
# Build specific service
./deployment/k8s/build-all-images.sh --service album

# Build all services
./deployment/k8s/build-all-images.sh --all

# Build and push to registry
./deployment/k8s/build-all-images.sh --all --push --registry gcr.io/my-project
```

**Features**:
- Builds only changed services (via git diff)
- Loads images to local Kind cluster
- Pushes to remote registry
- Tags with version and commit SHA

---

### 2. Deploy Script for Kind

**Location**: `deployment/k8s/deploy-to-kind.sh`

**Usage**:
```bash
# Deploy all services to Kind
./deployment/k8s/deploy-to-kind.sh

# Deploy specific service
./deployment/k8s/deploy-to-kind.sh --service album

# With auto port-forward
./deployment/k8s/deploy-to-kind.sh --port-forward
```

**Features**:
- Creates Kind cluster if not exists
- Deploys infrastructure services
- Deploys application services
- Sets up port-forwarding
- Runs health checks

---

### 3. Deploy Script for Cloud

**Location**: `deployment/k8s/deploy-to-cloud.sh`

**Usage**:
```bash
# Deploy to staging
./deployment/k8s/deploy-to-cloud.sh --env staging

# Deploy to production
./deployment/k8s/deploy-to-cloud.sh --env production

# Canary deployment
./deployment/k8s/deploy-to-cloud.sh --env production --canary --percentage 10
```

**Features**:
- Validates cluster connection
- Applies manifests with kubectl
- Monitors rollout status
- Runs post-deployment tests
- Sends notifications

---

## Configuration Management

### Environment-Specific Configs

```
deployment/
├── k8s/
│   ├── base/                      # Base manifests
│   │   ├── deployments/
│   │   ├── services/
│   │   ├── configmaps/
│   │   └── kustomization.yaml
│   ├── overlays/
│   │   ├── local/                 # Kind cluster config
│   │   │   ├── kustomization.yaml
│   │   │   └── patches/
│   │   ├── staging/               # Cloud staging config
│   │   │   ├── kustomization.yaml
│   │   │   └── patches/
│   │   └── production/            # Cloud production config
│   │       ├── kustomization.yaml
│   │       └── patches/
│   └── scripts/
│       ├── build-all-images.sh
│       ├── deploy-to-kind.sh
│       └── deploy-to-cloud.sh
└── staging/
    └── config/
        ├── .env.staging
        └── requirements.staging.txt
```

### Using Kustomize

```bash
# Apply local Kind configuration
kubectl apply -k deployment/k8s/overlays/local

# Apply staging configuration
kubectl apply -k deployment/k8s/overlays/staging

# Apply production configuration
kubectl apply -k deployment/k8s/overlays/production
```

---

## Secrets Management

### Local Development (Kind)

- **Method**: Kubernetes Secrets from files
- **Storage**: `.env` files (gitignored)
- **Access**: Loaded via ConfigMaps and Secrets

```bash
# Create secrets from env file
kubectl create secret generic app-secrets \
  --from-env-file=deployment/staging/config/.env.staging \
  -n isa-cloud-staging
```

### Cloud Environments

- **Method**: External Secrets Operator + Cloud Secret Manager
- **Storage**: AWS Secrets Manager / GCP Secret Manager / Azure Key Vault
- **Access**: Via External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
  data:
    - secretKey: DATABASE_PASSWORD
      remoteRef:
        key: prod/database/password
```

---

## Testing Strategy

### 1. Unit Tests

**Location**: `tests/unit/`

**Run**:
```bash
pytest tests/unit/ -v --cov=microservices
```

**Coverage**: Aim for >80% coverage

---

### 2. Integration Tests

**Location**: `tests/integration/`

**Run**:
```bash
# Requires services running
pytest tests/integration/ -v
```

**Coverage**:
- Service-to-service communication
- Database interactions
- Event bus (NATS) flows
- MQTT messaging

---

### 3. E2E Tests

**Location**: `tests/integration/test_*_e2e.py`

**Run**:
```bash
pytest tests/integration/test_photo_sharing_mqtt_e2e.py -v
```

**Coverage**:
- Complete user workflows
- Photo sharing flow
- Billing flow
- User registration flow

---

## Monitoring and Observability

### Metrics

- **Tool**: Prometheus + Grafana
- **Metrics**: Request rates, error rates, latencies, resource usage
- **Dashboards**: Per-service and system-wide views

### Logging

- **Tool**: Loki + Promtail (or ELK Stack)
- **Format**: Structured JSON logs
- **Retention**: 30 days (staging), 90 days (production)

### Tracing

- **Tool**: Jaeger / OpenTelemetry
- **Coverage**: All inter-service calls
- **Sampling**: 100% (staging), 10% (production)

### Alerting

- **Tool**: Alertmanager + PagerDuty
- **Alerts**:
  - Service down
  - High error rate (>1%)
  - High latency (P95 > 500ms)
  - Pod crashes
  - Resource exhaustion

---

## Disaster Recovery

### Backup Strategy

**Databases**:
- **Frequency**: Hourly (incremental), Daily (full)
- **Retention**: 7 days (hourly), 30 days (daily)
- **Storage**: Cloud object storage (S3/GCS)

**Kubernetes State**:
- **Tool**: Velero
- **Frequency**: Daily
- **Retention**: 30 days

### Recovery Procedures

**Database Recovery**:
```bash
# Restore from backup
./scripts/restore-database.sh --backup-id 2025-01-12-00-00

# Verify data integrity
./scripts/verify-database.sh
```

**Service Recovery**:
```bash
# Rollback to previous version
kubectl rollout undo deployment/album -n production

# Restore from Velero backup
velero restore create --from-backup daily-backup-2025-01-12
```

---

## Best Practices

### 1. Image Tagging Strategy

- **Development**: `service-name:latest`
- **Staging**: `service-name:develop-<SHA>`
- **Production**: `service-name:v1.2.3` (semantic versioning)

### 2. Resource Limits

Always specify resource requests and limits:

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 3. Health Checks

Implement proper liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 4. Rolling Updates

Configure deployment strategy:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

### 5. Pod Disruption Budgets

Ensure availability during updates:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: album-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: album
```

---

## Security Considerations

### 1. Image Scanning

- Scan all images for vulnerabilities before deployment
- Use Trivy, Clair, or cloud-native scanners
- Block deployment of critical vulnerabilities

### 2. Network Policies

- Restrict pod-to-pod communication
- Deny all by default, allow only necessary traffic
- Segment namespaces with network policies

### 3. RBAC

- Principle of least privilege
- Service accounts with minimal permissions
- Regular audit of permissions

### 4. Secrets Rotation

- Rotate secrets every 90 days
- Automated rotation for database credentials
- Monitor secret access

---

## Quick Reference

### Common Commands

```bash
# Build and deploy to local Kind
./deployment/k8s/build-all-images.sh --all
kubectl apply -k deployment/k8s/overlays/local

# Deploy specific service to staging
./deployment/k8s/build-all-images.sh --service album --push
kubectl rollout restart deployment/album -n staging

# Check deployment status
kubectl get pods -n isa-cloud-staging
kubectl logs -f deployment/album -n isa-cloud-staging

# Port-forward for local testing
kubectl port-forward -n isa-cloud-staging svc/album 8219:8219

# Run integration tests
pytest tests/integration/ -v -s
```

---

## Future Enhancements

1. **GitOps with ArgoCD**: Declarative deployment management
2. **Service Mesh (Istio)**: Advanced traffic management and security
3. **Progressive Delivery (Flagger)**: Automated canary deployments
4. **Cost Optimization**: Spot instances, autoscaling, resource optimization
5. **Multi-Region Deployment**: Geographic redundancy
6. **Chaos Engineering**: Automated failure injection testing

---

**Document Version**: 1.0
**Last Updated**: 2025-01-12
**Maintained By**: Platform Team
