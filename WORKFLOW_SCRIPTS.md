# Mobius OS Workflow Scripts

Quick reference for the development workflow scripts. All scripts work from any directory.

## Scripts

### `MobiusOSRun`
Starts the development environment (backend + frontend).

```bash
MobiusOSRun
```

**What it does:**
- Kills existing processes on ports 3000 and 8000
- Starts PostgreSQL (if using Homebrew)
- Starts Nexus backend (FastAPI) on port 8000
- Starts Portal frontend (Next.js) on port 3000
- Saves PIDs to `.mobius_pids` for easy stopping

**Output:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Logs: `nexus.log` and `portal.log`

---

### `MobiusOSGIT`
Commits and pushes all changes to git.

```bash
MobiusOSGIT "Your commit message"
# Or without message (will prompt)
MobiusOSGIT
```

**What it does:**
- Stages all changes (`git add -A`)
- Commits with your message
- Pushes to remote

---

### `MobiusOSBuild`
Builds and deploys to production (Google Cloud Run).

```bash
MobiusOSBuild
```

**What it does:**
- Builds Docker images via Cloud Build
- Pushes images to GCR
- Deploys to Cloud Run

**Requirements:**
- `gcloud` CLI installed and authenticated
- GCP project configured (default: `mobiusos-482817`)

---

### `MobiusOSDiary`
Updates the development diary with LLM-generated prose.

```bash
MobiusOSDiary
```

**What it does:**
- Collects development metrics (commits, file changes, LOC)
- Generates beautiful prose using LLM (DiaryBrain)
- Appends to daily diary file in `continuum/stream/`
- Tracks timestamp for next run

**Output:**
- Diary file: `continuum/stream/diary_YYYY-MM-DD.md`
- Last run timestamp: `.mobius_diary_last_run`

**Features:**
- Tracks changes since last invocation
- LLM-generated reflective prose
- Structured data (commits, new files, deleted files)
- Code metrics (Python/TypeScript lines)

---

## Setup

### Make Scripts Available Anywhere

**Option 1: Add to PATH**
Add this to your `~/.zshrc` or `~/.bashrc`:
```bash
export PATH="$PATH:/Users/ananth/Personal AI Projects/Mobius OS"
```

**Option 2: Create Symlinks**
```bash
sudo ln -s "/Users/ananth/Personal AI Projects/Mobius OS/MobiusOSRun" /usr/local/bin/MobiusOSRun
sudo ln -s "/Users/ananth/Personal AI Projects/Mobius OS/MobiusOSGIT" /usr/local/bin/MobiusOSGIT
sudo ln -s "/Users/ananth/Personal AI Projects/Mobius OS/MobiusOSBuild" /usr/local/bin/MobiusOSBuild
sudo ln -s "/Users/ananth/Personal AI Projects/Mobius OS/MobiusOSDiary" /usr/local/bin/MobiusOSDiary
```

### Dependencies

- `jq` (for JSON parsing in diary script)
  ```bash
  brew install jq
  ```

- Python virtual environment at `venv311/`
- Node.js and npm (for frontend)

---

## Usage Examples

```bash
# Start development
MobiusOSRun

# Make some changes, then commit
MobiusOSGIT "Added new feature"

# Update diary
MobiusOSDiary

# Build for production
MobiusOSBuild
```

---

## Troubleshooting

**Scripts not found:**
- Make sure they're in your PATH or use full path
- Check they're executable: `ls -la MobiusOS*`

**MobiusOSRun fails:**
- Check virtual environment exists: `ls venv311/bin/activate`
- Check PostgreSQL is running: `brew services list`

**MobiusOSDiary fails:**
- Check virtual environment is activated
- Check LLM service is configured (for prose generation)
- Falls back to simple prose if LLM unavailable

**MobiusOSBuild fails:**
- Check `gcloud auth list` shows active account
- Check `cloudbuild.yaml` exists
- Check GCP project is set correctly





