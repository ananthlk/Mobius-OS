# GCP Deployment Guide for Mobius OS

## 1. Initial Setup
We have provided a helper script to enable the necessary APIs and permissions.
Run from the root directory:
```bash
chmod +x machinery/setup_gcp_infra.sh
./machinery/setup_gcp_infra.sh
```

## 2. Connect GitHub Repository
Since automated repository connection requires OAuth permissions, you must do this in the Console:

1. Go to **[Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)**.
2. Select your project.
3. Click **"Connect Configuration"** (or "Connect Repository").
4. Select **GitHub (Cloud Build GitHub App)**.
5. Authorize and select your repository: `AnanthLK/Mobius-OS`.

## 3. Create the Trigger
1. Click **"Create Trigger"**.
2. **Name**: `mobius-os-main`
3. **Event**: "Push to a branch"
4. **Source**:
   - Repository: `AnanthLK/Mobius-OS` (selected above)
   - Branch: `^main$`
5. **Configuration**:
   - Type: `Cloud Build configuration file (yaml or json)`
   - Location: `cloudbuild.yaml` (Default)
6. Click **Create**.

## 4. Run the Build
- You can manually click **"Run"** on the trigger to start the first build.
- OR push a commit to main.

## 5. Deploy to Cloud Run (One-time Setup)
Once the images (`gcr.io/...`) actully exist after the first build, creating the Cloud Run services is easy.

### Nexus (Backend)
```bash
gcloud run deploy mobius-nexus \
  --image gcr.io/YOUR_PROJECT_ID/mobius-nexus \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

### Portal (Frontend)
```bash
gcloud run deploy mobius-portal \
  --image gcr.io/YOUR_PROJECT_ID/mobius-portal \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 3000
```
