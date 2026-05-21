#!/bin/bash

# ═══════════════════════════════════════════════════════════
# Database Restore Script
# ═══════════════════════════════════════════════════════════

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore-database.sh <backup-file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh backups/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will replace the current database!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo "📦 Decompressing backup..."
gunzip -c "$BACKUP_FILE" > /tmp/restore.sql

echo "🗄️  Restoring database..."
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U jobuser jobsdb < /tmp/restore.sql

rm /tmp/restore.sql

echo "✅ Database restored successfully!"
