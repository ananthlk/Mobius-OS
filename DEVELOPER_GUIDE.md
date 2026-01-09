# Mobius OS - Developer Workflows

This guide outlines the standard operating procedures for developing, testing, and deploying the Mobius Operating System.

## 🟢 1. Local Development (The "Continuum" State)

To run the full stack locally, you need two terminal sessions.

### **Lane 1: Nexus (Backend Brain)**
The Python FastAPI service that powers logic and context.
```bash
# 1. Activate Virtual Environment
source venv311/bin/activate

# 2. Run with Hot Reload
cd nexus
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
*Health Check: http://localhost:8000/*

### **Lane 2: Portal (Frontend Surface)**
The Next.js dashboard for user interaction.
```bash
cd surfaces/portal
npm run dev
```
*Access: http://localhost:3000/*

### **Lane 3: Spectacles (Extension Surface)**
1. Open Chrome/Brave to `chrome://extensions`.
2. Toggle **Developer Mode** (top right).
3. Click **"Load Unpacked"**.
4. Select the `surfaces/spectacles` folder.
*Note: You must reload the extension manually (Refresh icon) if you change `sidepanel.js` or HTML.*

---

## 🚀 2. Production Build Flow

We use **GitOps** principles. Your `git push` is the trigger for all production pipelines.

### **The Pipeline**
1. **Commit**: You push code to the `main` branch.
2. **Trigger**: Google Cloud Build detects the push.
3. **Build**: It reads `cloudbuild.yaml` and executes:
   - Builds `mobius-nexus` Docker image.
   - Builds `mobius-portal` (optimized standalone) Docker image.
4. **Registry**: Images are pushed to Google Consola Artifact Registry (`gcr.io`).

### **Manual Deploy Step (One-Time)**
After the images are built, you update the running services:
```bash
# Update Backend
gcloud run deploy mobius-nexus --image gcr.io/$PROJECT_ID/mobius-nexus

# Update Frontend
gcloud run deploy mobius-portal --image gcr.io/$PROJECT_ID/mobius-portal
```

---

## 🔑 3. Environment Variables (Config Management)

We maintain strict separation between generic config and secrets.

### **Local (Dev)**
- **Nexus**: Create `nexus/.env` (Copy from `.env.example`).
  - Contains `DATABASE_URL`, `OPENAI_API_KEY`, etc.
- **Portal**: Create `surfaces/portal/.env.local`.
  - Contains `NEXTSERVER_URL`, `NEXTAUTH_SECRET`.

### **Production (GCP)**
DO NOT commit `.env` files. Instead:

1. Go to **Google Cloud Console > Cloud Run**.
2. Click on the Service (`mobius-nexus` or `mobius-portal`).
3. Click **"Edit & Deploy New Revision"**.
4. Go to the **Variables & Secrets** tab.
5. Add variables there (e.g., `DATABASE_URL` pointing to Cloud SQL).

**⚠️ OAuth Setup Required for Portal:**
The Portal service requires Google OAuth credentials for user authentication. If you see "OAuth client was not found" errors, see **[OAUTH_SETUP_GUIDE.md](../OAUTH_SETUP_GUIDE.md)** for complete setup instructions.

Quick setup:
```bash
./scripts/setup_oauth_production.sh
```

---

## 🛠️ 4. Common Tasks

### **A. Adding a New Dependency**
- **Python**:
  ```bash
  pip install package_name
  pip freeze > nexus/requirements.txt  # CRITICAL: Do not forget this!
  ```
- **Node**:
  ```bash
  cd surfaces/portal
  npm install package_name
  # package.json updates automatically
  ```

### **B. Database Migrations**
Currently, `nexus` runs `init_db()` on startup. For schema changes:
1. Edit `nexus/modules/database.py`.
2. Restart Nexus.
*(Future state: We will move to `alembic` for formal migrations).*
