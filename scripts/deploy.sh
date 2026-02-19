#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/DefaultPerson/pushover-bot.git"
APP_DIR="${APP_DIR:-$HOME/pushover-bot}"
COMPOSE_FILE="docker-compose.full.yml"

echo "=== Pushover Bot Deploy Script ==="

# 1. Install Docker if not present
if ! command -v docker &>/dev/null; then
    echo ">>> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"
    echo ">>> Docker installed. You may need to re-login for group changes."
fi

# Check Docker Compose plugin
if ! docker compose version &>/dev/null; then
    echo "ERROR: Docker Compose plugin not found."
    echo "Install it: https://docs.docker.com/compose/install/"
    exit 1
fi

# 2. Clone or update repo
if [ -d "$APP_DIR" ]; then
    echo ">>> Updating existing repo at $APP_DIR..."
    git -C "$APP_DIR" pull --ff-only
else
    echo ">>> Cloning repo to $APP_DIR..."
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# 3. Create .env from example if missing
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo ""
        echo ">>> .env created from .env.example"
        echo ">>> IMPORTANT: Edit .env and fill in your tokens before continuing!"
        echo ">>>   nano $APP_DIR/.env"
        echo ""
        read -rp "Press Enter when .env is configured..."
    else
        echo "ERROR: .env.example not found."
        exit 1
    fi
fi

# 4. Build and start
echo ">>> Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --build

# 5. Check status
echo ""
echo ">>> Service status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "=== Deploy complete ==="
echo "Logs: docker compose -f $COMPOSE_FILE logs -f bot"
