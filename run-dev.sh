#!/bin/bash
# Development server runner with DEBUG logging to file

set -e

cd "$(dirname "$0")"

# Colors for console output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

LOG_FILE="${ICOM_LOG_FILE:-logs/icom-lan.log}"
HOST="${ICOM_HOST:-192.168.55.40}"
USER="${ICOM_USER:-moroz}"
PASS="${ICOM_PASS:-q1w2e3asda3}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8080}"

echo -e "${CYAN}🚀 Starting icom-lan web server (DEBUG mode)${NC}"
echo -e "${GREEN}   Radio:${NC} ${HOST}"
echo -e "${GREEN}   Web:${NC}   http://${WEB_HOST}:${WEB_PORT}"
echo -e "${GREEN}   Logs:${NC}  ${LOG_FILE}"
echo ""

# Run with debug logging
ICOM_DEBUG=1 ICOM_LOG_FILE="${LOG_FILE}" uv run icom-lan \
  --host "${HOST}" \
  --user "${USER}" \
  --pass "${PASS}" \
  web \
  --host "${WEB_HOST}" \
  --port "${WEB_PORT}"
