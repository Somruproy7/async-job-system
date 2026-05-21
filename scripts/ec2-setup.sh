#!/bin/bash
# scripts/ec2-setup.sh
# Run once on a fresh AWS EC2 instance (Ubuntu 24.04 LTS) to set up the server.
set -euo pipefail

echo "=== AWS EC2 Server Setup for Async Job System ==="

# ── System update ─────────────────────────────────────────────────────────────
apt-get update && apt-get upgrade -y

# ── Docker ────────────────────────────────────────────────────────────────────
apt-get install -y ca-certificates curl gnupg lsb-release git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker without sudo
usermod -aG docker ubuntu
systemctl enable docker

# ── Firewall (UFW) ─────────────────────────────────────────────────────────────
ufw --force enable
ufw allow ssh
ufw allow 80/tcp    # HTTP (reverse proxy)
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # API (direct, restrict in prod)
ufw allow 5555/tcp  # Flower dashboard

# ── App directory ─────────────────────────────────────────────────────────────
mkdir -p /opt/async-job-system
chown ubuntu:ubuntu /opt/async-job-system

# ── Clone repo ────────────────────────────────────────────────────────────────
su - ubuntu -c "
  cd /opt/async-job-system
  git clone https://github.com/YOUR_USERNAME/async-job-system.git .
  cp .env.example .env
  # Edit .env with production values before starting!
  echo '⚠️  Remember to edit /opt/async-job-system/.env with production secrets!'
"

# ── Systemd service (ensures Docker Compose restarts on reboot) ───────────────
cat > /etc/systemd/system/async-job-system.service << 'EOF'
[Unit]
Description=Async Job Processing System
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/async-job-system
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable async-job-system

echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Edit /opt/async-job-system/.env with production secrets"
echo "  2. Run: cd /opt/async-job-system && docker compose up -d"
echo "  3. Check health: curl http://localhost:8000/health"
