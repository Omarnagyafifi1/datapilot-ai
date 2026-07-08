# Azure Deployment Guide - DataPilot AI

## 1. Azure Resources Required

| Resource | Name Pattern | SKU/Tier | Purpose |
|----------|-------------|----------|---------|
| Resource Group | `rg-datapilot` | - | Logical container |
| Azure Container Registry | `acrdatapilot<uniq>` | Basic | Docker image storage |
| Azure Container Apps Environment | `cae-datapilot` | Consumption | Serverless container host |
| Azure Container App | `ca-datapilot` | - | Backend API |
| Azure Static Web Apps | `swa-datapilot` | Free/Standard | Frontend hosting |
| Azure Key Vault | `kv-datapilot<uniq>` | Standard | Secrets management |
| Application Insights | `ai-datapilot` | Per-GB | Monitoring & diagnostics |
| Log Analytics Workspace | `la-datapilot` | Per-GB | Log aggregation |
| PostgreSQL (optional) | `psql-datapilot` | Burstable | Production database |
| Azure OpenAI (optional) | `oai-datapilot` | S0 | LLM provider |

## 2. Azure CLI Commands

### Login and Setup

```bash
az login
az account set --subscription "<subscription-id>"

# Create Resource Group
az group create --name rg-datapilot --location eastus
```

### Deploy Infrastructure

```bash
# Deploy Bicep template
az deployment group create \
  --resource-group rg-datapilot \
  --template-file infrastructure/main.bicep \
  --parameters name=datapilot-ai
```

### Azure Container Registry

```bash
# Login to ACR
az acr login --name acrdatapilot

# Build and push image locally
docker build -t acrdatapilot.azurecr.io/datapilot-ai-backend:latest .
docker push acrdatapilot.azurecr.io/datapilot-ai-backend:latest
```

### Azure Container Apps

```bash
# Create Container App (if not using Bicep)
az containerapp create \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --environment cae-datapilot \
  --image acrdatapilot.azurecr.io/datapilot-ai-backend:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server acrdatapilot.azurecr.io \
  --registry-identity system \
  --min-replicas 1 \
  --max-replicas 10 \
  --env-vars \
    LLM_PROVIDER=groq \
    DEBUG=false \
    ALLOW_ORIGINS=https://swa-datapilot.azureedge.net \
  --secrets \
    encryption-key=<value> \
    groq-api-key=<value> \
    database-url=<value>

# Update existing Container App
az containerapp update \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --image acrdatapilot.azurecr.io/datapilot-ai-backend:latest
```

### Azure Static Web Apps

```bash
# Create Static Web App
az staticwebapp create \
  --name swa-datapilot \
  --resource-group rg-datapilot \
  --source https://github.com/your-org/datapilot-ai \
  --branch main \
  --app-location frontend \
  --output-location frontend/dist \
  --login-with-github

# Set API URL environment variable
az staticwebapp appsettings set \
  --name swa-datapilot \
  --resource-group rg-datapilot \
  --setting-names VITE_API_URL=https://ca-datapilot.<region>.azurecontainerapps.io
```

### Application Insights

```bash
# Get connection string
az monitor app-insights component show \
  --app ai-datapilot \
  --resource-group rg-datapilot \
  --query connectionString \
  --output tsv
```

## 3. Azure Key Vault

Store all secrets in Key Vault and reference them:

```bash
# Store secrets
az keyvault secret set --vault-name kv-datapilot --name "encryption-key" --value "<value>"
az keyvault secret set --vault-name kv-datapilot --name "groq-api-key" --value "<value>"
az keyvault secret set --vault-name kv-datapilot --name "azure-openai-api-key" --value "<value>"
az keyvault secret set --vault-name kv-datapilot --name "database-url" --value "<value>"
az keyvault secret set --vault-name kv-datapilot --name "appinsights-key" --value "<value>"
```

## 4. Required Environment Variables

```bash
# LLM Provider (choose one)
LLM_PROVIDER=azure|groq|openrouter|gemini|mock

# For Azure OpenAI:
AZURE_OPENAI_ENDPOINT=https://oai-datapilot.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# For other providers:
GROQ_API_KEY=<key>
OPENROUTER_API_KEY=<key>
GEMINI_API_KEY=<key>

# Required
ENCRYPTION_KEY=<32-byte-base64-key>

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql+asyncpg://user:pass@psql-datapilot.postgres.database.azure.com:5432/datapilot
DATA_SOURCES_DB_URL=postgresql+psycopg2://user:pass@psql-datapilot.postgres.database.azure.com:5432/datapilot
QUERY_HISTORY_DB_URL=postgresql+psycopg2://user:pass@psql-datapilot.postgres.database.azure.com:5432/datapilot

# Or use POSTGRES_* variables for auto-configuration:
POSTGRES_HOST=psql-datapilot.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_USER=datapilot
POSTGRES_PASSWORD=<password>
POSTGRES_DB=datapilot

# CORS
ALLOW_ORIGINS=https://swa-datapilot.azureedge.net

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=<from-app-insights>

# Optional
REDIS_URL=redis://redis:6379/0
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=<key>
LANGCHAIN_PROJECT=datapilot-ai
```

## 5. Docker Commands

```bash
# Build for production
docker build -t datapilot-ai:latest -f Dockerfile .

# Run locally with production config
docker compose -f docker-compose.prod.yml up -d

# Run locally with dev config
docker compose up -d

# Tag and push to ACR
docker tag datapilot-ai:latest acrdatapilot.azurecr.io/datapilot-ai-backend:latest
docker push acrdatapilot.azurecr.io/datapilot-ai-backend:latest
```

## 6. Deployment Commands

### Manual Deployment

```bash
# 1. Build and push Docker image
docker build -t acrdatapilot.azurecr.io/datapilot-ai-backend:$(date +%Y%m%d)-$(git rev-parse --short HEAD) .
docker push acrdatapilot.azurecr.io/datapilot-ai-backend:$(date +%Y%m%d)-$(git rev-parse --short HEAD)

# 2. Update Container App
az containerapp update \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --image acrdatapilot.azurecr.io/datapilot-ai-backend:$(date +%Y%m%d)-$(git rev-parse --short HEAD)
```

### CI/CD Deployment

Push to `main` branch. The GitHub Actions workflow in `.github/workflows/ci-cd.yml` will:

1. Run linting and tests
2. Build and push Docker image to ACR
3. Deploy backend to Azure Container Apps
4. Build and deploy frontend to Azure Static Web Apps

## 7. Rollback Process

```bash
# Rollback to previous Container App revision
az containerapp revision list \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --query "[?properties.active]" \
  -o table

# Activate a specific revision
az containerapp revision activate \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --revision <revision-name>

# Or rollback to a specific image tag
az containerapp update \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --image acrdatapilot.azurecr.io/datapilot-ai-backend:<previous-tag>
```

## 8. Monitoring

### Application Insights

- **Live Metrics**: Real-time monitoring in Azure Portal
- **Performance**: Request rates, response times, failure rates
- **Failures**: Exception tracking and stack traces
- **Logs**: Custom query logging via OpenCensus/Python logging

### Configure App Insights in the app:

```python
# The APPLICATIONINSIGHTS_CONNECTION_STRING env var enables
# OpenCensus Azure Monitor exporters for:
# - Request tracking
# - Exception tracking
# - Dependency tracking (DB, HTTP calls)
# - Custom metrics
```

### Key Metrics to Watch

- Request rate (requests/minute)
- Response time (p95 latency)
- Failure rate (< 1%)
- CPU/Memory usage per container
- Active container replicas
- Database connections

## 9. Scaling

### Auto-scaling Configuration

The Container App is configured with:

```yaml
scale:
  minReplicas: 1
  maxReplicas: 10
  rules:
    - name: http-scaling
      custom:
        type: http
        metadata:
          concurrentRequests: '100'
```

### Manual Scaling

```bash
az containerapp update \
  --name ca-datapilot \
  --resource-group rg-datapilot \
  --min-replicas 2 \
  --max-replicas 20
```

## 10. Cost Optimization Recommendations

| Area | Recommendation | Estimated Savings |
|-----|---------------|-------------------|
| Container Apps | Use Consumption plan (pay-per-execution) | 60-80% vs Dedicated |
| ACR | Use Basic SKU + delete old tags | ~$5/month |
| PostgreSQL | Use Burstable (B1ms) for dev, General Purpose for prod | 50-70% |
| Static Web Apps | Free tier includes 100GB bandwidth | $0/month |
| Key Vault | Standard tier, 10k operations/month free | ~$1/month |
| Log Analytics | Set retention to 30 days | 50% |
| Azure OpenAI | Use PTU (provisioned) for predictable workloads | 40% |
| Dev/Test | Use Azure Dev/Test pricing with subscription | Variable |

### Monthly Cost Estimate (Production)

| Resource | Estimated Cost |
|----------|---------------|
| Container Apps (Consumption) | $20-50 |
| ACR (Basic) | $5 |
| PostgreSQL (GP - 2 cores) | $150 |
| Static Web Apps | $0 (Free) |
| Key Vault | $1 |
| Log Analytics | $10 |
| Application Insights | $5 |
| Azure OpenAI (Pay-as-you-go) | $50-200 |
| **Total** | **~$240-420/month** |

## Azure Portal Setup Steps

1. **Create Resource Group** → `rg-datapilot`
2. **Deploy Bicep template** → Infrastructure as Code
3. **Azure OpenAI** → Create OpenAI resource, deploy model (GPT-4o), get endpoint & key
4. **Azure Container Registry** → Enable admin user, note credentials
5. **Azure Container Apps** → Deploy from ACR image
6. **Azure Static Web Apps** → Connect GitHub repo for auto-deploy
7. **Azure Key Vault** → Create secrets, grant access to Container Apps via managed identity
8. **Application Insights** → Connect to Container Apps via env var
9. **PostgreSQL** → Create Flexible Server, configure firewall, create database
10. **Configure DNS** → Point custom domain to Container Apps / Static Web Apps
11. **Set up monitoring** → Configure alerts for key metrics
12. **Run CI/CD** → Push to main branch triggers automatic deployment

## Security Checklist

- [ ] All secrets in Key Vault, not env vars
- [ ] CORS restricted to specific origins
- [ ] HTTPS enforced (Container Apps and Static Web Apps do this by default)
- [ ] PostgreSQL firewall restricted to Azure services + Container Apps outbound IPs
- [ ] Managed Identity used instead of service principals where possible
- [ ] Application Insights logs do not contain secrets
- [ ] Container App uses non-root user (already configured in Dockerfile)
- [ ] API rate limiting enabled (in-app middleware + Azure Front Door optional)
- [ ] Input validation on all endpoints (Pydantic models)
- [ ] SQL injection protection (parameterized queries via SQLAlchemy)
- [ ] Prompt injection protection via LLM guardrails in prompts
