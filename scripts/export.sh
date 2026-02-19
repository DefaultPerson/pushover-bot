#!/bin/bash
# Export archived messages to HTML with media
# Usage: ./scripts/export.sh [output_dir] [--group GROUP_ID]

set -e

OUTPUT_DIR="${1:-.}"
HTML_NAME="archive.html"
MEDIA_DIR="archive_media"

# Parse additional arguments
shift || true
EXTRA_ARGS="$@"

echo "=== Telegram Archive Export ==="

# Auto-detect bot service name (pushover-bot or bot)
BOT_SVC=""
for name in pushover-bot bot; do
    if docker compose ps --status running 2>/dev/null | grep -q "$name"; then
        BOT_SVC="$name"
        break
    fi
done

if [ -z "$BOT_SVC" ]; then
    echo "Error: Bot container is not running. Start it with: docker compose up -d"
    exit 1
fi

echo "Using service: $BOT_SVC"

# Copy latest script to container
echo "Updating export script in container..."
docker compose exec "$BOT_SVC" mkdir -p /app/scripts 2>/dev/null || true
docker compose cp scripts/export_archive.py "$BOT_SVC":/app/scripts/ 2>/dev/null

# Run export inside container
echo "Running export..."
docker compose exec "$BOT_SVC" python /app/scripts/export_archive.py \
    -o /app/export/${HTML_NAME} \
    ${EXTRA_ARGS}

# Copy files from container
echo "Copying files..."
mkdir -p "${OUTPUT_DIR}"
docker compose cp "$BOT_SVC":/app/export/${HTML_NAME} "${OUTPUT_DIR}/${HTML_NAME}"

# Copy media folder if it exists
if docker compose exec "$BOT_SVC" test -d /app/export/${MEDIA_DIR} 2>/dev/null; then
    rm -rf "${OUTPUT_DIR}/${MEDIA_DIR}"
    docker compose cp "$BOT_SVC":/app/export/${MEDIA_DIR} "${OUTPUT_DIR}/"
    MEDIA_COUNT=$(ls -1 "${OUTPUT_DIR}/${MEDIA_DIR}" 2>/dev/null | wc -l)
    echo "Copied ${MEDIA_COUNT} media files"
fi

# Cleanup container temp files
docker compose exec "$BOT_SVC" rm -rf /app/export 2>/dev/null || true

echo ""
echo "=== Export complete ==="
echo "HTML: ${OUTPUT_DIR}/${HTML_NAME}"
if [ -d "${OUTPUT_DIR}/${MEDIA_DIR}" ]; then
    echo "Media: ${OUTPUT_DIR}/${MEDIA_DIR}/"
fi
echo ""
echo "Open in browser: file://$(realpath "${OUTPUT_DIR}/${HTML_NAME}")"
