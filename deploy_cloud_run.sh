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

echo ""
echo "⚠️  IMPORTANT: If this is a new deployment or OAuth is not working,"
echo "   you need to set OAuth environment variables:"
echo ""
echo "   Option 1: Run the setup script:"
echo "   ./scripts/setup_oauth_production.sh"
echo ""
echo "   Option 2: See OAUTH_SETUP_GUIDE.md for manual setup"
echo ""

echo "Done!"
