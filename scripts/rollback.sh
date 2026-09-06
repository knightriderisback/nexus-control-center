#!/usr/bin/env bash
set -euo pipefail

echo "======================================================================"
echo "⚠️  NEXUS // PRODUCTION ROLLBACK PROTOCOL"
echo "======================================================================"

PROJECT_ID="personal-engineering-os-2026"
REGION="asia-south1"
SERVICE_NAME="nexus-control-center"

echo "[1/3] Querying previous stable Cloud Run revision..."
# Attempt rollback to previous known revision if available
if gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" &>/dev/null; then
    PREV_REVISION=$(gcloud run revisions list --service="$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format="value(name)" --limit=2 | tail -n 1)
    if [ -n "$PREV_REVISION" ]; then
        echo "[2/3] Rolling back traffic 100% to revision: $PREV_REVISION"
        gcloud run services update-traffic "$SERVICE_NAME" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --to-revisions="${PREV_REVISION}=100"
        echo "[3/3] Rollback complete. Service traffic restored to $PREV_REVISION."
    else
        echo "No previous revision found to rollback to."
    fi
else
    echo "Cloud Run service not currently provisioned. Local state remains intact."
fi

echo "======================================================================"
