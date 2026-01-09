# Google OAuth Setup Guide for Production

## Problem
You're seeing the error: **"Access blocked: Authorization Error - The OAuth client was not found. Error 401: invalid_client"**

This happens when the Google OAuth client credentials are missing or incorrectly configured in your Cloud Run service.

## Solution Steps

### 1. Create a Google OAuth Client (if you don't have one)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `mobiusos-482817` (or your project ID)
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen first:
   - User Type: **External** (for public access)
   - App name: **Mobius OS**
   - User support email: `mobiushealthai@gmail.com`
   - Developer contact: `mobiushealthai@gmail.com`
   - Click **Save and Continue** through the scopes and test users steps
6. Back in Credentials, select **OAuth client ID**
7. Application type: **Web application**
8. Name: **Mobius Portal OAuth Client**
9. **Authorized redirect URIs** - Add these:
   ```
   https://mobius-portal-<hash>-uc.a.run.app/api/auth/callback/google
   http://localhost:3000/api/auth/callback/google
   ```
   > **Note**: Replace `<hash>` with your actual Cloud Run service URL. You can find it in Cloud Run console or by running:
   > ```bash
   > gcloud run services describe mobius-portal --region us-central1 --format='value(status.url)'
   > ```
10. Click **Create**
11. **Copy the Client ID and Client Secret** - you'll need these in the next step

### 2. Set Environment Variables in Cloud Run

You need to set these environment variables in your `mobius-portal` Cloud Run service:

- `AUTH_GOOGLE_ID` - Your Google OAuth Client ID
- `AUTH_GOOGLE_SECRET` - Your Google OAuth Client Secret  
- `AUTH_URL` - Your production URL (e.g., `https://mobius-portal-<hash>-uc.a.run.app`)

#### Option A: Using Google Cloud Console (Recommended)

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on **mobius-portal** service
3. Click **EDIT & DEPLOY NEW REVISION**
4. Expand **Variables & Secrets** section
5. Click **ADD VARIABLE** and add:
   - Name: `AUTH_GOOGLE_ID`, Value: `<your-client-id>`
   - Name: `AUTH_GOOGLE_SECRET`, Value: `<your-client-secret>`
   - Name: `AUTH_URL`, Value: `<your-production-url>` (e.g., `https://mobius-portal-xxxxx-uc.a.run.app`)
6. Click **DEPLOY**

#### Option B: Using gcloud CLI

```bash
# Get your production URL first
PROD_URL=$(gcloud run services describe mobius-portal \
  --region us-central1 \
  --format='value(status.url)')

# Deploy with environment variables
gcloud run services update mobius-portal \
  --region us-central1 \
  --set-env-vars="AUTH_GOOGLE_ID=YOUR_CLIENT_ID,AUTH_GOOGLE_SECRET=YOUR_CLIENT_SECRET,AUTH_URL=$PROD_URL"
```

Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` with your actual OAuth credentials.

### 3. Verify the Configuration

1. After deployment, wait a minute for the service to update
2. Visit your production URL
3. Try signing in with Google
4. The error should be resolved

### 4. Troubleshooting

If you still see errors:

1. **Check redirect URI matches exactly**: 
   - In Google Cloud Console > Credentials > Your OAuth Client
   - The redirect URI must be: `https://your-actual-url/api/auth/callback/google`
   - No trailing slashes, exact match required

2. **Verify environment variables are set**:
   ```bash
   gcloud run services describe mobius-portal \
     --region us-central1 \
     --format='value(spec.template.spec.containers[0].env)'
   ```

3. **Check service logs**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mobius-portal" \
     --limit 50 \
     --format json
   ```

4. **Ensure OAuth consent screen is configured**:
   - Go to APIs & Services > OAuth consent screen
   - Make sure it's published (or add test users if in testing mode)

## Quick Reference

### Required Environment Variables for Portal
- `AUTH_GOOGLE_ID` - Google OAuth Client ID
- `AUTH_GOOGLE_SECRET` - Google OAuth Client Secret
- `AUTH_URL` - Production URL (for NextAuth callbacks)

### Required Redirect URI Format
```
https://<your-cloud-run-url>/api/auth/callback/google
```

### Finding Your Cloud Run URL
```bash
gcloud run services describe mobius-portal \
  --region us-central1 \
  --format='value(status.url)'
```



