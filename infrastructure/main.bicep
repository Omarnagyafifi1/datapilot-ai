@description('The name of the resource group and resources')
param name string = 'datapilot-ai'

@description('The Azure region to deploy to')
param location string = 'eastus'

@description('The SKU for the Container Apps Environment')
param environmentSku string = 'Consumption'

@description('The name of the Azure Container Registry')
param acrName string = 'acr${uniqueString(resourceGroup().id)}'

@description('The name of the Azure Container App')
param containerAppName string = 'ca-${name}'

@description('The name of the Log Analytics Workspace')
param logAnalyticsName string = 'la-${name}'

@description('Application Insights name')
param appInsightsName string = 'ai-${name}'

@description('Key Vault name')
param keyVaultName string = 'kv-${name}${uniqueString(resourceGroup().id)}'

@description('Azure Static Web App name')
param staticWebAppName string = 'swa-${name}'

// ===================== Resources =====================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${name}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      secrets: [
        { name: 'encryption-key', value: '' }
        { name: 'groq-api-key', value: '' }
        { name: 'openrouter-api-key', value: '' }
        { name: 'gemini-api-key', value: '' }
        { name: 'azure-openai-api-key', value: '' }
        { name: 'database-url', value: '' }
        { name: 'appinsights-key', value: '' }
      ]
      registries: [
        {
          server: '${acr.properties.loginServer}'
          username: acr.listCredentials().username
          passwordSecretRef: ''
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${acr.properties.loginServer}/datapilot-ai-backend:latest'
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: [
            { name: 'LLM_PROVIDER', value: 'groq' }
            { name: 'ENCRYPTION_KEY', secretRef: 'encryption-key' }
            { name: 'GROQ_API_KEY', secretRef: 'groq-api-key' }
            { name: 'OPENROUTER_API_KEY', secretRef: 'openrouter-api-key' }
            { name: 'GEMINI_API_KEY', secretRef: 'gemini-api-key' }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-api-key' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-key' }
            { name: 'ALLOW_ORIGINS', value: 'https://${staticWebAppName}.azureedge.net' }
            { name: 'DEBUG', value: 'false' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/live', port: 8000 }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8000 }
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            custom: {
              type: 'http'
              metadata: { concurrentRequests: '100' }
            }
          }
        ]
      }
    }
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { name: 'standard', family: 'A' }
    tenantId: subscription().tenantId
    accessPolicies: []
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 7
  }
}

resource staticWebApp 'Microsoft.Web/staticSites@2022-03-01' = {
  name: staticWebAppName
  location: location
  properties: {
    repositoryUrl: ''
    branch: 'main'
    buildProperties: {
      appLocation: 'frontend'
      outputLocation: 'frontend/dist'
    }
  }
}

// ===================== Outputs =====================

output acrLoginServer string = acr.properties.loginServer
output containerAppName string = containerApp.name
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output keyVaultName string = keyVault.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
