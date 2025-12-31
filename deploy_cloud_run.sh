#!/bin/bash
PROJECT="mobiusos-482817"
REGION="us-central1"

echo "Deploying Nexus (Backend)..."
gcloud run deploy mobius-nexus \
    --image gcr.io/$PROJECT/mobius-nexus \
    --project $PROJECT \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated

echo "Deploying Portal (Frontend)..."
gcloud run deploy mobius-portal \
    --image gcr.io/$PROJECT/mobius-portal \
    --project $PROJECT \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated

echo "Done!"
