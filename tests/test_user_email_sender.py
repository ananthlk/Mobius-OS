#!/usr/bin/env python3
"""
Test User Email Sender
Tests sending email from user's Gmail account via OAuth2

Usage:
    # Requires OAuth setup first:
    # 1. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET
    # 2. Authorize Gmail access via /api/gmail/oauth/authorize
    # 3. Then run:
    python tests/test_user_email_sender.py
"""
import sys
import os
import json
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.communication.user_email_sender import UserEmailSender


async def test_user_email_sender_async():
    """Test UserEmailSender tool (async version)"""
    print("\n" + "=" * 90)
    print("Testing: UserEmailSender")
    print("=" * 90)
    print()
    
    # Check OAuth configuration
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("⚠️  WARNING: Gmail OAuth not configured")
        print("   Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables")
        print("   This test requires OAuth setup to work")
        print()
    
    print("📧 Configuration:")
    print(f"   Sender: User's Gmail account (via OAuth)")
    print(f"   Recipient: ananth.lalithakumar@gmail.com")
    print(f"   OAuth Client ID: {'SET' if client_id else 'NOT SET'}")
    print(f"   OAuth Client Secret: {'SET' if client_secret else 'NOT SET'}")
    print()
    
    try:
        tool = UserEmailSender()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        print()
        
        if not client_id or not client_secret:
            print("⏭️  Skipping send test - OAuth not configured")
            print("   Tool is ready but requires OAuth authorization")
            return True
        
        # Test sending email
        print("📤 Sending test email from user account...")
        print("   (This requires user to have authorized Gmail access)")
        print()
        
        result = await tool.run_async(
            to="ananth.lalithakumar@gmail.com",
            subject="Test Email from Mobius OS User Account",
            message="This is a test email sent from a user's Gmail account via OAuth2.\n\nIf you received this, the user email sender is working correctly!\n\nBest regards,\nMobius OS",
            user_id="system"  # Default user ID
        )
        
        print(f"✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"   To: {result.get('to')}")
        print(f"   Subject: {result.get('subject')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Method: {result.get('method')}")
        print(f"   Sent At: {result.get('sent_at')}")
        print()
        
        print("📄 Full Result:")
        print(json.dumps(result, indent=2))
        print()
        
        return True
        
    except ValueError as e:
        error_msg = str(e)
        if "No Gmail OAuth credentials" in error_msg:
            print("⚠️  OAuth credentials not found for user")
            print("   User needs to authorize Gmail access first:")
            print("   GET /api/gmail/oauth/authorize?user_id=system")
            print("   Then complete the OAuth flow")
            return True  # Not a test failure, just needs setup
        else:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_email_sender():
    """Test UserEmailSender tool (sync wrapper)"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(test_user_email_sender_async())


if __name__ == "__main__":
    success = test_user_email_sender()
    sys.exit(0 if success else 1)






