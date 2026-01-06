# Database Backups

This directory contains automated backups of the Mobius OS database.

## Backup System

### Manual Backup

To create a backup manually:

```bash
cd "/Users/ananth/Personal AI Projects/Mobius OS"
source venv311/bin/activate
python scripts/backup_database.py
```

### List Backups

To see all available backups:

```bash
python scripts/backup_database.py --list
```

### Automated Backups

Automated backups run daily at 2:00 AM via macOS launchd.

**To activate automated backups:**

```bash
cd "/Users/ananth/Personal AI Projects/Mobius OS"
./scripts/setup_automated_backups.sh
launchctl load ~/Library/LaunchAgents/com.mobiusos.database-backup.plist
```

**To deactivate:**

```bash
launchctl unload ~/Library/LaunchAgents/com.mobiusos.database-backup.plist
```

**To check status:**

```bash
launchctl list | grep mobiusos
```

### Backup Retention

- Backups are automatically cleaned up after 30 days
- Backups are stored in: `backups/database/`
- Backup files are named: `mobius_db_backup_YYYYMMDD_HHMMSS.sql`

### Restoring from Backup

To restore a backup:

```bash
# 1. List available backups
python scripts/backup_database.py --list

# 2. Restore using psql
psql -U ananth -d mobius_db < backups/database/mobius_db_backup_YYYYMMDD_HHMMSS.sql
```

**⚠️ WARNING:** Restoring will overwrite existing data. Make a backup first!

### Backup Logs

- Backup output: `backups/database/backup.log`
- Backup errors: `backups/database/backup_error.log`

## Data Loss Prevention

The application now includes safeguards to prevent accidental data loss:

1. **Production Database Protection**: The application will NOT auto-create production databases (`mobius_db`, `mobius_prod`, `mobius_production`). If these databases are missing, the application will fail with a clear error message.

2. **Database Existence Checks**: The application checks if databases exist before attempting to create them.

3. **Automated Backups**: Daily backups ensure data can be recovered if lost.

## Recovery from Data Loss

If data is lost:

1. **Check Backups**: List available backups using `python scripts/backup_database.py --list`

2. **Check PostgreSQL WAL**: If Write-Ahead Logging is enabled, data might be recoverable from WAL files

3. **Check for Database Dumps**: Look for `.sql` or `.dump` files in the project directory

4. **Check Other Databases**: Verify if data exists in another PostgreSQL instance or database

5. **Restore from Backup**: Use the most recent backup to restore data

