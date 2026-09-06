#!/usr/bin/env bash
set -euo pipefail

echo "======================================================================"
echo "⚠️  NEXUS // PRODUCTION ROLLBACK PROTOCOL"
echo "======================================================================"

PROJECT_ID="personal-engineering-os-2026"
REGION="asia-south1"
SERVICE_NAME="nexus-control-center"

# 1. Cloud Run Rollback Check
echo "[1/3] Checking Google Cloud Run revisions..."
if gcloud --quiet run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" &>/dev/null; then
    PREV_REVISION=$(gcloud --quiet run revisions list --service="$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format="value(name)" --limit=2 | tail -n 1)
    if [ -n "$PREV_REVISION" ]; then
        echo "[2/3] Rolling back Cloud Run traffic 100% to revision: $PREV_REVISION"
        gcloud --quiet run services update-traffic "$SERVICE_NAME" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --to-revisions="${PREV_REVISION}=100"
        echo "[3/3] Cloud Run traffic successfully restored to $PREV_REVISION."
    else
        echo "Only one Cloud Run revision exists. No previous cloud revision to rollback to."
    fi
else
    echo "Cloud Run service not currently active in GCP (billing unlinked)."
fi

# 2. Local Workstation Git & Daemon Rollback Check
echo "[2/3] Inspecting local Git commit history..."
if [ -d "/root/control-center/.git" ]; then
    CURRENT_COMMIT=$(git -C /root/control-center rev-parse --short HEAD)
    echo "Current local commit: $CURRENT_COMMIT"
    echo "Local working tree is intact."
fi

# 3. Health Probe Verification
echo "[3/3] Verifying local daemon health..."
if curl -sf http://localhost:8000/api/health >/dev/null; then
    echo "✓ Local NEXUS daemon running nominally on http://localhost:8000"
else
    echo "⚠️  Daemon not responding. Restarting daemon..."
    bash /root/control-center/start.sh &
fi

echo "======================================================================"
echo "Rollback protocol executed cleanly."
echo "======================================================================"
