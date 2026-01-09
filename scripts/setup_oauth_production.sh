#!/bin/bash

# Setup Google OAuth for Production Portal
# This script helps you set the required OAuth environment variables in Cloud Run

set -e

PROJECT="mobiusos-482817"
REGION="us-central1"
SERVICE="mobius-portal"

echo "🔵 Setting up Google OAuth for Mobius Portal"
echo ""

# Get the current production URL
echo "📡 Fetching production URL..."
PROD_URL=$(gcloud run services describe $SERVICE \
  --project $PROJECT \
  --region $REGION \
  --format='value(status.url)' 2>/dev/null || echo "")

if [ -z "$PROD_URL" ]; then
    echo "❌ Error: Could not find Cloud Run service '$SERVICE'"
    echo "   Make sure the service is deployed first."
    exit 1
fi

echo "✅ Production URL: $PROD_URL"
echo ""

# Prompt for OAuth credentials
echo "Please provide your Google OAuth credentials:"
echo "(You can find these in Google Cloud Console > APIs & Services > Credentials)"
echo ""

read -p "Enter AUTH_GOOGLE_ID (OAuth Client ID): " CLIENT_ID
if [ -z "$CLIENT_ID" ]; then
    echo "❌ Error: AUTH_GOOGLE_ID is required"
    exit 1
fi

read -sp "Enter AUTH_GOOGLE_SECRET (OAuth Client Secret): " CLIENT_SECRET
echo ""
if [ -z "$CLIENT_SECRET" ]; then
    echo "❌ Error: AUTH_GOOGLE_SECRET is required"
    exit 1
fi

echo ""
echo "🔵 Updating Cloud Run service with OAuth credentials..."
echo ""

# Update the service with environment variables
gcloud run services update $SERVICE \
  --project $PROJECT \
  --region $REGION \
  --set-env-vars="AUTH_GOOGLE_ID=$CLIENT_ID,AUTH_GOOGLE_SECRET=$CLIENT_SECRET,AUTH_URL=$PROD_URL"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully updated OAuth configuration!"
    echo ""
    echo "📋 Summary:"
    echo "   - AUTH_GOOGLE_ID: Set"
    echo "   - AUTH_GOOGLE_SECRET: Set"
    echo "   - AUTH_URL: $PROD_URL"
    echo ""
    echo "⚠️  Important: Make sure your OAuth client in Google Cloud Console has this redirect URI:"
    echo "   $PROD_URL/api/auth/callback/google"
    echo ""
    echo "   To verify/update:"
    echo "   1. Go to https://console.cloud.google.com/apis/credentials"
    echo "   2. Click on your OAuth 2.0 Client ID"
    echo "   3. Add the redirect URI above if it's not already there"
    echo ""
else
    echo ""
    echo "❌ Error: Failed to update service"
    exit 1
fi



