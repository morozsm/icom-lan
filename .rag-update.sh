#!/bin/bash
cd /Users/moroz/Projects/icom-lan || exit 1

# Find and re-ingest all modified files in last 24h
find docs/ src/ frontend/src -type f \( -name '*.md' -o -name '*.py' -o -name '*.ts' -o -name '*.svelte' \) \
  ! -path '*/node_modules/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/.venv/*' \
  ! -path '*/__tests__/*' \
  ! -name '*.test.*' \
  ! -name '*.spec.*' \
  -mtime -1 2>/dev/null | while read f; do
    mcporter call local-rag.ingest_file filePath="$(pwd)/$f" 2>&1 | grep -q '"success":true' && echo "✓ $f" || echo "✗ $f"
done

# Print final status
echo "---"
mcporter call local-rag.status 2>&1 | grep -o '"documentCount":[0-9]*,"chunkCount":[0-9]*'
