#!/bin/bash

# Mobius OS - GCP Setup Helper
# This script enables necessary APIs and checks configuration.

echo "🔵 Initializing GCP Setup for Mobius OS..."

# 1. Check Auth
AUTH_ACCOUNT=$(gcloud config get-value account)
echo "✅ Authenticated as: $AUTH_ACCOUNT"

# 2. Get Project ID
CURRENT_PROJECT=$(gcloud config get-value project)
echo "❓ The current project is set to: $CURRENT_PROJECT"
read -p "   Is this correct? (y/n): " confirm
if [[ $confirm != "y" ]]; then
    read -p "   Enter your GCP Project ID: " NEW_PROJECT
    gcloud config set project $NEW_PROJECT
    CURRENT_PROJECT=$NEW_PROJECT
fi

echo "🚀 Using Project: $CURRENT_PROJECT"

# 3. Enable APIs
echo "🔵 Enabling Required APIs (this may take a minute)..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    logging.googleapis.com

echo "✅ APIs Enabled."

# 4. Check Permissions (Basic Check)
echo "🔵 Verifying Cloud Build permissions..."
PROJECT_NUMBER=$(gcloud projects describe $CURRENT_PROJECT --format='value(projectNumber)')
CLOUDBUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Grant Cloud Build permission to deploy to Cloud Run
gcloud projects add-iam-policy-binding $CURRENT_PROJECT \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/run.admin"

# Grant Cloud Build permission to act as Service Account (for running the services)
gcloud projects add-iam-policy-binding $CURRENT_PROJECT \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/iam.serviceAccountUser"

echo "✅ Cloud Build Service Account ($CLOUDBUILD_SA) granted Deploy permissions."

echo "--------------------------------------------------------"
echo "🎉 Infrastructure Setup Complete!"
echo "--------------------------------------------------------"
echo "Next Steps:"
echo "1. Connect your GitHub Repo: https://console.cloud.google.com/cloud-build/triggers"
echo "2. Create a Trigger pointing to 'cloudbuild.yaml' in the root."
echo "3. Push a commit to watch the build start!"
