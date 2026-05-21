#!/bin/bash

# ═══════════════════════════════════════════════════════════
# System Monitoring Script
# ═══════════════════════════════════════════════════════════

echo "📊 Job System Monitoring Dashboard"
echo "═══════════════════════════════════════════════════════"
echo ""

# Container status
echo "🐳 Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

# Resource usage
echo "💻 Resource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
echo ""

# Disk usage
echo "💾 Disk Usage:"
df -h | grep -E "Filesystem|/dev/"
echo ""

# Database size
echo "🗄️  Database Size:"
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U jobuser jobsdb -c "SELECT pg_size_pretty(pg_database_size('jobsdb')) as size;" 2>/dev/null || echo "Database not accessible"
echo ""

# Recent errors
echo "❌ Recent Errors (last 10):"
docker compose -f docker-compose.prod.yml logs --tail=100 | grep -i error | tail -10 || echo "No recent errors"
echo ""

# API health
echo "🏥 API Health:"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "API not responding"
echo ""

# Worker status
echo "👷 Worker Status:"
docker compose -f docker-compose.prod.yml exec -T worker \
    celery -A app.core.celery_app.celery_app inspect active 2>/dev/null || echo "Workers not accessible"
echo ""

echo "═══════════════════════════════════════════════════════"
echo "✅ Monitoring complete"
