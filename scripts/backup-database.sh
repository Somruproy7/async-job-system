#!/bin/bash

# ═══════════════════════════════════════════════════════════
# Database Backup Script
# ═══════════════════════════════════════════════════════════

set -e

echo "💾 Creating database backup..."

# Create backups directory
mkdir -p backups

# Generate backup filename with timestamp
BACKUP_FILE="backups/jobsystem-$(date +%Y%m%d-%H%M%S).sql"

# Create backup
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U jobuser jobsdb > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

echo "✅ Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 days of backups
find backups/ -name "*.sql.gz" -mtime +7 -delete

echo "🧹 Old backups cleaned up (kept last 7 days)"
