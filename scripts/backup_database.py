#!/usr/bin/env python3
"""
Database Backup Script for Mobius OS
Creates a timestamped SQL dump of the mobius_db database.
"""
import os
import sys
import subprocess
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local")

def get_backup_dir():
    """Get or create backup directory."""
    backup_dir = PROJECT_ROOT / "backups" / "database"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def create_backup():
    """Create a PostgreSQL backup."""
    # Get database connection info from environment
    database_url = os.getenv("DATABASE_URL")
    parsed = None
    password = None
    
    if not database_url:
        # Try to construct from common defaults
        db_user = os.getenv("PGUSER", "ananth")
        db_host = os.getenv("PGHOST", "localhost")
        db_port = os.getenv("PGPORT", "5432")
        db_name = "mobius_db"
        password = os.getenv("PGPASSWORD")
        print(f"⚠️  DATABASE_URL not set, using defaults: {db_user}@{db_host}:{db_port}/{db_name}")
    else:
        # Parse DATABASE_URL
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip('/')
        db_user = parsed.username or 'postgres'
        db_host = parsed.hostname or 'localhost'
        db_port = parsed.port or 5432
        password = parsed.password
    
    # Create backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    backup_file = backup_dir / f"mobius_db_backup_{timestamp}.sql"
    
    print(f"📦 Creating backup of database '{db_name}'...")
    print(f"   Host: {db_host}:{db_port}")
    print(f"   User: {db_user}")
    print(f"   Backup file: {backup_file}")
    
    # Create pg_dump command
    # Note: password should be in .pgpass or PGPASSWORD env var
    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-d", db_name,
        "-F", "p",  # Plain text format
        "-f", str(backup_file),
        "--verbose"
    ]
    
    try:
        # Set PGPASSWORD if password is available
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Get file size
        file_size = backup_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"✅ Backup created successfully!")
        print(f"   Size: {file_size_mb:.2f} MB")
        print(f"   Location: {backup_file}")
        
        # Clean up old backups (keep last 30 days)
        cleanup_old_backups(backup_dir, days=30)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Backup failed")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ ERROR: pg_dump not found. Please install PostgreSQL client tools.")
        print("   macOS: brew install postgresql@14")
        return False

def cleanup_old_backups(backup_dir, days=30):
    """Remove backup files older than specified days."""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    removed_count = 0
    
    for backup_file in backup_dir.glob("mobius_db_backup_*.sql"):
        try:
            file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_time < cutoff_date:
                backup_file.unlink()
                removed_count += 1
        except Exception as e:
            print(f"⚠️  Warning: Could not remove old backup {backup_file}: {e}")
    
    if removed_count > 0:
        print(f"🧹 Cleaned up {removed_count} old backup(s) (older than {days} days)")

def list_backups():
    """List all available backups."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("mobius_db_backup_*.sql"), reverse=True)
    
    if not backups:
        print("📭 No backups found")
        return
    
    print(f"📦 Available backups ({len(backups)}):")
    for backup in backups:
        file_size = backup.stat().st_size / (1024 * 1024)
        file_time = datetime.datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"   {backup.name} - {file_size:.2f} MB - {file_time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mobius OS Database Backup Tool")
    parser.add_argument("--list", action="store_true", help="List available backups")
    args = parser.parse_args()
    
    if args.list:
        list_backups()
    else:
        success = create_backup()
        sys.exit(0 if success else 1)

