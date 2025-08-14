# Mantis Docker Deployment

This directory contains Docker deployment configurations for the Mantis agent coordination system.

## Quick Start

### Production Setup (Recommended)

Use the improved compose configuration that focuses on `serve-all`:

```bash
# Start the entire system
docker-compose -f docker-compose.improved.yml up -d

# View logs
docker-compose -f docker-compose.improved.yml logs -f

# Stop the system
docker-compose -f docker-compose.improved.yml down
```

### Development/Debug Setup

For debugging individual agents, use the debug override:

```bash
# Start with debug services enabled
docker-compose -f docker-compose.improved.yml -f docker-compose.debug.yml up -d

# Start only specific debug profiles
docker-compose -f docker-compose.improved.yml -f docker-compose.debug.yml --profile debug up -d
```

## Services

### Core Services

1. **a2a-registry** (Port 8080)
   - Central agent registration and discovery
   - Health endpoint: `http://localhost:8080/health`

2. **agent-server** (Ports 9001-9050)
   - Consolidated server running all agents via `serve-all`
   - Automatically discovers and serves agents from `/agents-quick`
   - Health endpoint: `http://localhost:9001/health`

3. **jsonrpc-service** (Port 8081)
   - JSON-RPC interface for programmatic access
   - Health endpoint: `http://localhost:8081/health`

### Debug Services (Optional)

- **chief-of-staff-debug** (Port 9201): Individual chief of staff instance for debugging

## Architecture Improvements

### Before (Legacy)
- Mixed `serve-all` and multiple `serve-single` containers
- Resource duplication across individual agent containers
- Complex port management (9001-9200 + individual ports)
- Maintenance overhead for individual agent services

### After (Improved)
- **Primary**: Single `serve-all` container handling all agents
- **Optional**: Debug overlay for development
- Optimized port range (9001-9050)
- Better resource utilization
- Simplified configuration management

## Configuration

### Environment Variables

Required:
- `ANTHROPIC_API_KEY`: For Claude models
- `GOOGLE_API_KEY`: For Gemini models via ADK

Optional:
- `OPENAI_API_KEY`: For OpenAI models
- `REGISTRY_URL`: Registry endpoint (default: http://a2a-registry:8080)

### Networking

- Custom bridge network: `agent-network` (172.20.0.0/16)
- Service discovery via container names
- Health checks with proper dependency ordering

## Monitoring & Health Checks

All services include:
- Health check endpoints
- Proper startup dependencies
- Configurable retry policies
- Structured logging

Monitor health:
```bash
# Check all service health
docker-compose -f docker-compose.improved.yml ps

# Individual service logs
docker-compose -f docker-compose.improved.yml logs agent-server
```

## Scaling

To scale agent capacity:

1. **Horizontal**: Add more `agent-server` replicas
```bash
docker-compose -f docker-compose.improved.yml up -d --scale agent-server=3
```

2. **Vertical**: Adjust `--max-agents` parameter in compose file

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 8080, 8081, 9001-9050 are available
2. **API keys**: Verify environment variables are set
3. **Agent loading**: Check agent JSON files in `/agents-quick` are valid
4. **Registry connection**: Verify `a2a-registry` is healthy before agent startup

### Debug Commands

```bash
# View agent discovery
curl http://localhost:8080/agents

# Test JSON-RPC service
curl -X POST http://localhost:8081 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"get_service_info","params":{},"id":"1"}'

# Check individual agent
curl http://localhost:9001/.well-known/agent.json
```

## Migration from Legacy

To migrate from the original docker-compose.yml:

1. Stop existing containers:
   ```bash
   docker-compose down
   ```

2. Switch to improved configuration:
   ```bash
   docker-compose -f docker-compose.improved.yml up -d
   ```

3. Verify all agents are registered:
   ```bash
   curl http://localhost:8080/agents | jq
   ```

The improved setup maintains full compatibility while providing better resource utilization and simplified management.