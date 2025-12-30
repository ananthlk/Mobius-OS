# Mobius OS - Sprint 1 Walkthrough

**The First Thread** is now established. This guide explains how to boot up the entire system.

## Prerequisites
- **Node.js**: [Install v20+](https://nodejs.org/)
- **Python**: [Install v3.11+](https://python.org/)
- **PostgreSQL**: [Install](https://postgresql.org/) or use Docker.

## 1. Ignite the Strata (Database)
Ensure Postgres is running locally on port `5432`. Create the database:
```bash
createdb mobius_db
```
Apply the schema:
```bash
psql -d mobius_db -f strata/postgres/schema.sql
```

## 2. Awaken the Nexus (Backend)
Navigate to the core logic and start the brain:
```bash
cd nexus
pip install -r requirements.txt
# Set your environment variables in .env (copy from .env.example)
uvicorn app:app --reload --port 8000
```
*Verification*: Visit `http://localhost:8000`. You should see `{"status": "online"}`.

## 3. Launch the Surfaces (Frontend)

### Portal (Web Interface)
```bash
cd surfaces/portal
npm install
npm run dev
```
*Verification*: Visit `http://localhost:3000`. Login with Google (if configured) or browse as guest. Talk to the chat interface.

### Spectacles (Chrome Extension)
1. Open Chrome and go to `chrome://extensions`.
2. Enable **Developer Mode** (top right).
3. Click **Load unpacked**.
4. Select the folder `mobius-os/surfaces/spectacles`.
*Verification*: Open the Side Panel in Chrome. You should see the Mobius chat interface.

## 4. Verify the Thread
1. Type "Hello" in the Portal.
2. Check `http://localhost:8000/api/chat/history?user_id=...` to see if it was logged.
3. Type "Hello" in the Extension.
4. Verify both share the same "Brain" (Nexus).
