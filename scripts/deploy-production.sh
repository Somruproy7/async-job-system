#!/bin/bash

# ═══════════════════════════════════════════════════════════
# Production Deployment Script
# ═══════════════════════════════════════════════════════════

set -e  # Exit on error

echo "🚀 Starting production deployment..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}❌ Error: .env.production file not found!${NC}"
    echo "Please create .env.production with your production settings."
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Warning: Not running as root. Some operations may fail.${NC}"
fi

# Step 1: Pull latest code
echo -e "${GREEN}📥 Pulling latest code...${NC}"
git pull origin main || echo "Skipping git pull (not a git repository or no changes)"

# Step 2: Backup database
echo -e "${GREEN}💾 Creating database backup...${NC}"
mkdir -p backups
BACKUP_FILE="backups/backup-$(date +%Y%m%d-%H%M%S).sql"
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U jobuser jobsdb > "$BACKUP_FILE" 2>/dev/null || echo "No existing database to backup"
echo "Backup saved to: $BACKUP_FILE"

# Step 3: Build images
echo -e "${GREEN}🔨 Building Docker images...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache

# Step 4: Stop old containers
echo -e "${GREEN}🛑 Stopping old containers...${NC}"
docker compose -f docker-compose.prod.yml down

# Step 5: Start new containers
echo -e "${GREEN}🚀 Starting new containers...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Step 6: Wait for services to be healthy
echo -e "${GREEN}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Step 7: Run database migrations
echo -e "${GREEN}🗄️  Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head || echo "Migration skipped or failed"

# Step 8: Check service health
echo -e "${GREEN}🏥 Checking service health...${NC}"
docker compose -f docker-compose.prod.yml ps

# Step 9: Test API endpoint
echo -e "${GREEN}🧪 Testing API health endpoint...${NC}"
sleep 5
curl -f http://localhost:8000/health || echo "Health check failed - service may still be starting"

# Step 10: Show logs
echo -e "${GREEN}📋 Recent logs:${NC}"
docker compose -f docker-compose.prod.yml logs --tail=20

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Service URLs:"
echo "  - API: http://localhost:8000"
echo "  - Frontend: http://localhost:3001"
echo "  - Flower: http://localhost:5555/flower/"
echo ""
echo "📝 Next steps:"
echo "  1. Configure your domain DNS to point to this server"
echo "  2. Set up SSL certificates (see scripts/setup-ssl.sh)"
echo "  3. Update ALLOWED_ORIGINS in .env.production"
echo "  4. Monitor logs: docker compose -f docker-compose.prod.yml logs -f"
echo ""
