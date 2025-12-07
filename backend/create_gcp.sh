#!/bin/bash
# Create GCS folder structure for web platform

BUCKET_NAME="medscan-pipeline-medscanai-476500"

echo "Creating platform folders in gs://$BUCKET_NAME/"
echo ""

TMP_PLACEHOLDER="/tmp/.gcskeep"
echo "" > "$TMP_PLACEHOLDER"

# Create folder prefixes by uploading a placeholder file
gsutil cp "$TMP_PLACEHOLDER" gs://$BUCKET_NAME/platform/.gcskeep
gsutil cp "$TMP_PLACEHOLDER" gs://$BUCKET_NAME/platform/raw_scans/.gcskeep
gsutil cp "$TMP_PLACEHOLDER" gs://$BUCKET_NAME/platform/raw_scans/patients/.gcskeep
gsutil cp "$TMP_PLACEHOLDER" gs://$BUCKET_NAME/platform/reports/.gcskeep

echo "Created platform folder structure"
echo ""

# List structure
echo "Current structure:"
gsutil ls -r gs://$BUCKET_NAME/platform/

echo ""
echo "GCS Platform Setup Complete!"