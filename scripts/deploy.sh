#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/DefaultPerson/pushover-bot.git"
APP_DIR="${APP_DIR:-$HOME/pushover-bot}"
COMPOSE_FILE="docker-compose.full.yml"

# --- Helpers ---

prompt() {
    local var_name="$1" prompt_text="$2" required="${3:-true}" default="${4:-}"
    local value=""

    while true; do
        if [ -n "$default" ]; then
            printf "%s [%s]: " "$prompt_text" "$default" >/dev/tty
        else
            printf "%s: " "$prompt_text" >/dev/tty
        fi
        read -r value </dev/tty

        value="${value:-$default}"

        if [ "$required" = "true" ] && [ -z "$value" ]; then
            echo "  This field is required." >/dev/tty
            continue
        fi
        break
    done

    eval "$var_name='$value'"
}

generate_password() {
    tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 24 || true
}

echo "=== Pushover Bot Deploy ==="
echo ""

# --- 1. Docker ---

if ! command -v docker &>/dev/null; then
    echo ">>> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"
    echo ">>> Docker installed. You may need to re-login for group changes."
    echo ""
fi

if ! docker compose version &>/dev/null; then
    echo "ERROR: Docker Compose plugin not found."
    echo "Install: https://docs.docker.com/compose/install/"
    exit 1
fi

# --- 2. Clone repo ---

if [ -d "$APP_DIR" ]; then
    echo ">>> Updating existing repo at $APP_DIR..."
    git -C "$APP_DIR" pull --ff-only
else
    echo ">>> Cloning repo to $APP_DIR..."
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# --- 3. Configure .env ---

if [ -f .env ]; then
    echo ">>> .env already exists, skipping configuration."
    echo ""
else
    echo ">>> Configure your bot (press Enter for defaults where shown):"
    echo ""

    DB_PASS_DEFAULT=$(generate_password)

    prompt BOT_TOKEN       "Telegram Bot Token (from @BotFather)" true
    prompt APP_TOKEN        "Pushover App Token (from pushover.net/apps)" true
    prompt DB_PASSWORD      "Database password" true "$DB_PASS_DEFAULT"
    prompt ADMIN_IDS        "Admin Telegram IDs, comma-separated (optional)" false

    cat > .env <<ENVEOF
BOT_TOKEN=${BOT_TOKEN}
PUSHOVER_APP_TOKEN=${APP_TOKEN}

DB_HOST=postgres
DB_PORT=5432
DB_NAME=pushover
DB_USER=dev
DB_PASSWORD=${DB_PASSWORD}

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

ADMIN_IDS=${ADMIN_IDS:-}

LOG_LEVEL=INFO
GM_RATE_LIMIT=3
GM_RATE_WINDOW=300
TEST_ALARM_RATE_LIMIT=1
TEST_ALARM_RATE_WINDOW=60

ARCHIVE_ENABLED=false
ARCHIVE_MEDIA_PATH=archive/media
ENVEOF

    echo ""
    echo ">>> .env created."
fi

# --- 4. Build and start ---

echo ">>> Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo ""
echo ">>> Service status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "=== Deploy complete ==="
echo "Logs:    docker compose -f $COMPOSE_FILE logs -f bot"
echo "Stop:    docker compose -f $COMPOSE_FILE down"
echo "Update:  git pull && docker compose -f $COMPOSE_FILE up -d --build"
