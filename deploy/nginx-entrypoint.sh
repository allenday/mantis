#!/bin/sh
# Nginx entrypoint script to wait for persona orchestrator and copy config

set -e

echo "Waiting for persona orchestrator to generate nginx config..."

# Wait for orchestrator to be ready and generate config
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s http://persona-orchestrator:9010/health > /dev/null 2>&1; then
        echo "Orchestrator is ready, attempting to get nginx config..."
        
        # Try to get the generated config
        if curl -f -s http://persona-orchestrator:9010/nginx-config -o /tmp/persona-proxy.conf 2>/dev/null; then
            echo "Successfully retrieved nginx config from orchestrator"
            cp /tmp/persona-proxy.conf /etc/nginx/conf.d/persona-proxy.conf
            break
        else
            echo "Config not ready yet, using template..."
            cp /etc/nginx/nginx-persona-proxy.conf.template /etc/nginx/conf.d/persona-proxy.conf
            break
        fi
    fi
    
    echo "Waiting for orchestrator... (attempt $((attempt + 1))/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "Warning: Could not connect to orchestrator, using template config"
    cp /etc/nginx/nginx-persona-proxy.conf.template /etc/nginx/conf.d/persona-proxy.conf
fi

echo "Nginx configuration ready"