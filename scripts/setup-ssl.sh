#!/bin/bash

# ═══════════════════════════════════════════════════════════
# SSL Certificate Setup Script (Let's Encrypt)
# ═══════════════════════════════════════════════════════════

set -e

echo "🔒 Setting up SSL certificates with Let's Encrypt..."

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: ./setup-ssl.sh yourdomain.com"
    exit 1
fi

DOMAIN=$1
EMAIL=${2:-admin@$DOMAIN}

echo "Domain: $DOMAIN"
echo "Email: $EMAIL"

# Install certbot
echo "📦 Installing certbot..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y certbot
elif command -v yum &> /dev/null; then
    sudo yum install -y certbot
else
    echo "❌ Package manager not supported. Please install certbot manually."
    exit 1
fi

# Create directories
mkdir -p nginx/ssl
mkdir -p /var/www/certbot

# Get certificate
echo "🔐 Obtaining SSL certificate..."
sudo certbot certonly --standalone \
    --preferred-challenges http \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Copy certificates
echo "📋 Copying certificates..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/*.pem

# Set up auto-renewal
echo "🔄 Setting up auto-renewal..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem $(pwd)/nginx/ssl/ && docker compose -f docker-compose.prod.yml restart nginx") | crontab -

echo "✅ SSL setup complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Update nginx/nginx.conf with your domain name"
echo "  2. Restart nginx: docker compose -f docker-compose.prod.yml restart nginx"
echo ""
