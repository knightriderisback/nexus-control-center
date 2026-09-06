#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${1:-http://localhost:8000}"
echo "Running system verification on: $ENDPOINT"

echo -n "Checking /api/health ... "
curl -sf "${ENDPOINT}/api/health" | grep -q "ONLINE" && echo "PASS" || (echo "FAIL"; exit 1)

echo -n "Checking /api/v1/overview ... "
curl -sf "${ENDPOINT}/api/v1/overview" | grep -q "fleet" && echo "PASS" || (echo "FAIL"; exit 1)

echo -n "Checking /api/v1/projects ... "
curl -sf "${ENDPOINT}/api/v1/projects" | grep -q "personal-engineering-os-2026" && echo "PASS" || (echo "FAIL"; exit 1)

echo -n "Checking /api/v1/cost/status ... "
curl -sf "${ENDPOINT}/api/v1/cost/status" | grep -q "strict_zero_cost_enforced" && echo "PASS" || (echo "FAIL"; exit 1)

echo "✓ All core system verification probes passed successfully."
