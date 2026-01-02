#!/usr/bin/env python3
"""
Manual script to sync Cursor IDE conversations to Mobius OS.
Can be run directly or called from MobiusOSSync.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
try:
    import httpx
except ImportError:
    print("⚠️  httpx not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

# Configuration
API_URL = os.getenv("MOBIUS_API_URL", "http://localhost:8000")
USER_ID = os.getenv("USER", "unknown")
SOURCE = "cursor"

async def find_cursor_chat_sessions():
    """Find and parse Cursor chat session files."""
    cursor_base = Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    
    if not cursor_base.exists():
        print(f"❌ Cursor storage not found at {cursor_base}")
        return []
    
    # Find all chat session directories
    chat_dirs = list(cursor_base.glob("*/chatSessions"))
    if not chat_dirs:
        print(f"⚠️  No Cursor chat sessions found")
        return []
    
    all_messages = []
    
    # Process each workspace's chat sessions
    for chat_dir in chat_dirs:
        if not chat_dir.is_dir():
            continue
            
        # Look for session files
        session_files = []
        for item in chat_dir.iterdir():
            if item.is_file() and item.stat().st_size > 0:
                session_files.append(item)
        
        # Sort by modification time (most recent first)
        session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Process most recent sessions
        for session_file in session_files[:10]:  # Limit to 10 most recent per workspace
            try:
                # Skip if file is too large (likely corrupted or old)
                if session_file.stat().st_size > 50 * 1024 * 1024:  # 50MB limit
                    continue
                    
                with open(session_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(content)
                        messages = extract_messages(data)
                        if messages:
                            print(f"   ✓ Found {len(messages)} messages in {session_file.name}")
                            all_messages.extend(messages)
                    except json.JSONDecodeError as e:
                        # Try to find JSON-like structures
                        messages = extract_messages_from_text(content)
                        if messages:
                            all_messages.extend(messages)
            except Exception as e:
                continue
    
    return all_messages

def extract_messages(data):
    """Extract messages from parsed JSON data."""
    messages = []
    
    if isinstance(data, dict):
        # Cursor format: requests array with message and response
        if 'requests' in data:
            for request in data['requests']:
                # Extract user message
                if 'message' in request:
                    msg_data = request['message']
                    user_text = msg_data.get('text', '')
                    if user_text:
                        messages.append({
                            "role": "user",
                            "content": user_text[:2000],  # Limit length
                            "timestamp": None
                        })
                
                # Extract assistant response
                if 'response' in request:
                    response = request['response']
                    if isinstance(response, list):
                        for resp_item in response:
                            if isinstance(resp_item, dict) and 'value' in resp_item:
                                assistant_text = resp_item['value']
                                if assistant_text:
                                    messages.append({
                                        "role": "assistant",
                                        "content": str(assistant_text)[:2000],
                                        "timestamp": None
                                    })
                    elif isinstance(response, dict) and 'value' in response:
                        assistant_text = response['value']
                        if assistant_text:
                            messages.append({
                                "role": "assistant",
                                "content": str(assistant_text)[:2000],
                                "timestamp": None
                            })
        
        # Standard format: messages array
        elif 'messages' in data:
            for msg in data['messages']:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append({
                        "role": msg['role'],
                        "content": str(msg['content'])[:2000],
                        "timestamp": msg.get('timestamp') or msg.get('created_at')
                    })
        
        # Look for nested message structures
        for key, value in data.items():
            if isinstance(value, (dict, list)) and key not in ['requests', 'messages']:
                messages.extend(extract_messages(value))
    elif isinstance(data, list):
        for item in data:
            messages.extend(extract_messages(item))
    
    return messages

def extract_messages_from_text(text):
    """Try to extract messages from text content."""
    messages = []
    # Simple pattern matching for common chat formats
    # This is a fallback - actual format may vary
    import re
    
    # Look for role: content patterns
    patterns = [
        r'"role"\s*:\s*"(\w+)"\s*,\s*"content"\s*:\s*"([^"]+)"',
        r'role["\']\s*:\s*["\'](\w+)["\']\s*,\s*content["\']\s*:\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            role = match.group(1)
            content = match.group(2)[:2000]
            if role in ['user', 'assistant', 'system']:
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": None
                })
    
    return messages

async def sync_to_mobius(messages):
    """Sync messages to Mobius OS API."""
    if not messages:
        print("⚠️  No messages to sync")
        return
    
    print(f"📝 Found {len(messages)} messages to sync")
    
    # Remove duplicates (same role + content)
    seen = set()
    unique_messages = []
    for msg in messages:
        key = (msg['role'], msg['content'][:100])  # First 100 chars as key
        if key not in seen:
            seen.add(key)
            unique_messages.append(msg)
    
    if len(unique_messages) < len(messages):
        print(f"   (Removed {len(messages) - len(unique_messages)} duplicates)")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_URL}/api/external/log-conversation",
                json={
                    "user_id": USER_ID,
                    "source": SOURCE,
                    "messages": unique_messages,
                    "metadata": {
                        "synced_at": datetime.now().isoformat(),
                        "synced_from": "cursor_ide_manual"
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully synced {result.get('message_count', 0)} messages to Mobius OS")
                return True
            else:
                print(f"❌ Sync failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except httpx.ConnectError:
        print(f"❌ Cannot connect to Mobius OS at {API_URL}")
        print(f"   Make sure it's running: MobiusOSRun")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🔄 Syncing Cursor IDE conversations to Mobius OS...")
    print(f"   API: {API_URL}")
    print(f"   User: {USER_ID}")
    print("")
    
    messages = await find_cursor_chat_sessions()
    
    if not messages:
        print("⚠️  No messages found. This could mean:")
        print("   - Cursor chat sessions are in a different format")
        print("   - No recent conversations in Cursor")
        print("   - Chat sessions are stored elsewhere")
        print("")
        print("💡 You can manually log conversations using:")
        print(f"   curl -X POST {API_URL}/api/external/log-conversation \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"user_id\": \"{USER_ID}\", \"source\": \"cursor\", \"messages\": [...]}'")
        return
    
    success = await sync_to_mobius(messages)
    
    if success:
        print("")
        print("💡 Run MobiusOSDiary to see these conversations in your diary!")

if __name__ == "__main__":
    asyncio.run(main())

