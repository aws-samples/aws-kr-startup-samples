# Observability Assistant Helm Chart

This Helm chart deploys the Observability Assistant application along with its MCP (Model Context Protocol) servers.

## Components

The chart deploys the following components:

1. **Observability Assistant** - Main application with a LoadBalancer service
2. **Grafana MCP Server** - Interface to Grafana with ClusterIP service  
3. **Tempo MCP Server** - Interface to Tempo with ClusterIP service

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

## Installation

### Add the repository (if applicable)
```bash
# If you have a Helm repository
helm repo add observability-assistant <repository-url>
helm repo update
```

### Install the chart
```bash
# Install with default values
helm install my-observability-assistant ./helm/observability-assistant

# Install with custom values
helm install my-observability-assistant ./helm/observability-assistant -f values.yaml

# Install with specific namespace
helm install my-observability-assistant ./helm/observability-assistant --namespace observability --create-namespace
```

## Configuration

### Required Configuration

Before installing, you must configure the following environment variables in your `values.yaml`:

```yaml
grafanaMcpServer:
  env:
    grafanaUrll: "https://your-grafana-instance.com"
    grafanaApiKey: "your-grafana-api-key"

tempoMcpServer:
  env:
    tempoUrl: "https://your-tempo-instance.com"
```

### Image Configuration

Update the image repositories and tags for your built images:

```yaml
observabilityAssistant:
  image:
    repository: your-registry/observability-assistant
    tag: "v1.0.0"

tempoMcpServer:
  image:
    repository: your-registry/tempo-mcp-server
    tag: "v1.0.0"
```

### Complete Values Example

```yaml
observabilityAssistant:
  image:
    repository: myregistry/observability-assistant
    tag: "1.0.0"
  service:
    type: LoadBalancer
    port: 80
  replicaCount: 2

grafanaMcpServer:
  image:
    repository: mcp/grafana
    tag: "latest"
  env:
    grafanaUrll: "https://grafana.example.com"
    grafanaApiKey: "glsa_xxxxxxxxxxxxxxxxxxxx"
  replicaCount: 1

tempoMcpServer:
  image:
    repository: myregistry/tempo-mcp-server
    tag: "1.0.0"
  env:
    tempoUrl: "https://tempo.example.com"
  replicaCount: 1
```

## Parameters

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nameOverride` | Override the name of the chart | `""` |
| `fullnameOverride` | Override the full name of the chart | `""` |
| `imagePullSecrets` | Image pull secrets | `[]` |

### Observability Assistant Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `observabilityAssistant.image.repository` | Image repository | `observability-assistant` |
| `observabilityAssistant.image.tag` | Image tag | `latest` |
| `observabilityAssistant.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `observabilityAssistant.service.type` | Service type | `LoadBalancer` |
| `observabilityAssistant.service.port` | Service port | `80` |
| `observabilityAssistant.replicaCount` | Number of replicas | `1` |

**Note**: The observability-assistant automatically receives the following environment variables:
- `GRAFANA_MCP_URL`: Points to the Grafana MCP server service
- `TEMPO_MCP_URL`: Points to the Tempo MCP server service

### Grafana MCP Server Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `grafanaMcpServer.image.repository` | Image repository | `mcp/grafana` |
| `grafanaMcpServer.env.grafanaUrll` | Grafana instance URL | `""` |
| `grafanaMcpServer.env.grafanaApiKey` | Grafana API key | `""` |
| `grafanaMcpServer.service.port` | Service port | `8000` |
| `grafanaMcpServer.replicaCount` | Number of replicas | `1` |

### Tempo MCP Server Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tempoMcpServer.image.repository` | Image repository | `tempo-mcp-server` |
| `tempoMcpServer.env.tempoUrl` | Tempo instance URL | `""` |
| `tempoMcpServer.service.port` | Service port | `8000` |
| `tempoMcpServer.replicaCount` | Number of replicas | `1` |

## Accessing the Application

After installation, follow the instructions shown in the NOTES to access your application:

1. **LoadBalancer Service**: Wait for the external IP and access via that IP
2. **Port Forward**: Use kubectl port-forward for local access
3. **Ingress**: Configure an ingress controller for advanced routing

## Health Checks

The chart includes health checks for all components:

- **Observability Assistant**: HTTP health check on `/_stcore/health`
- **Grafana MCP Server**: TCP socket check on port 8000
- **Tempo MCP Server**: TCP socket check on port 8000

## Upgrading

```bash
# Upgrade the release
helm upgrade my-observability-assistant ./helm/observability-assistant

# Upgrade with new values
helm upgrade my-observability-assistant ./helm/observability-assistant -f new-values.yaml
```

## Uninstalling

```bash
# Uninstall the release
helm uninstall my-observability-assistant

# Uninstall from specific namespace
helm uninstall my-observability-assistant --namespace observability
```

## Troubleshooting

### Common Issues

1. **Pod not starting**: Check image pull secrets and image availability
2. **Service not accessible**: Verify LoadBalancer provisioning in your cluster
3. **Environment variables**: Ensure required env vars are set in values.yaml

### Useful Commands

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/instance=my-observability-assistant

# Check service status
kubectl get services -l app.kubernetes.io/instance=my-observability-assistant

# View logs
kubectl logs -l app.kubernetes.io/component=observability-assistant
kubectl logs -l app.kubernetes.io/component=grafana-mcp-server
kubectl logs -l app.kubernetes.io/component=tempo-mcp-server

# Describe resources
kubectl describe deployment my-observability-assistant-observability-assistant
```

## Contributing

When making changes to the chart:

1. Update the chart version in `Chart.yaml`
2. Update this README if new parameters are added
3. Test the chart with `helm install --dry-run --debug`
4. Validate with `helm lint` 