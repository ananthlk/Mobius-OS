#!/bin/bash
# Setup automated database backups for Mobius OS
# This creates a launchd plist for macOS to run backups daily

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_ROOT/scripts/backup_database.py"
PLIST_NAME="com.mobiusos.database-backup"
PLIST_FILE="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "🔧 Setting up automated database backups..."

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ ERROR: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

# Create launchd plist
cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_ROOT/venv311/bin/python</string>
        <string>$BACKUP_SCRIPT</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/backups/database/backup.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/backups/database/backup_error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ Created launchd plist: $PLIST_FILE"
echo ""
echo "To activate the backup schedule:"
echo "  launchctl load $PLIST_FILE"
echo ""
echo "To deactivate:"
echo "  launchctl unload $PLIST_FILE"
echo ""
echo "To run a backup manually:"
echo "  cd $PROJECT_ROOT && source venv311/bin/activate && python scripts/backup_database.py"
echo ""
echo "To list backups:"
echo "  python scripts/backup_database.py --list"


