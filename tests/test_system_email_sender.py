#!/usr/bin/env python3
"""
Test System Email Sender
Tests sending email from system account (mobiushealthai@gmail.com)

Usage:
    # Set environment variable first:
    export EMAIL_PASSWORD='your-app-password'
    python tests/test_system_email_sender.py
"""
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.communication.system_email_sender import SystemEmailSender


def test_system_email_sender():
    """Test SystemEmailSender tool"""
    print("\n" + "=" * 90)
    print("Testing: SystemEmailSender")
    print("=" * 90)
    print()
    
    # Check if password is set
    email_password = os.getenv('EMAIL_PASSWORD') or os.getenv('EMAIL_APP_PASSWORD')
    if not email_password:
        print("❌ ERROR: EMAIL_PASSWORD environment variable not set")
        print()
        print("Please set it before running:")
        print("  export EMAIL_PASSWORD='your-app-password'")
        print("  python tests/test_system_email_sender.py")
        return False
    
    print("📧 Configuration:")
    print(f"   System Email: mobiushealthai@gmail.com")
    print(f"   Recipient: ananth.lalithakumar@gmail.com")
    print(f"   Email Password: SET (from environment variable)")
    print()
    
    try:
        tool = SystemEmailSender()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        print()
        
        # Test sending email
        print("📤 Sending test email...")
        result = tool.run(
            to="ananth.lalithakumar@gmail.com",
            subject="Test Email from Mobius OS System Account",
            message="This is a test email sent from the Mobius OS system account (mobiushealthai@gmail.com).\n\nIf you received this, the system email sender is working correctly!\n\nBest regards,\nMobius OS"
        )
        
        print(f"✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"   From: {result.get('from')}")
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
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_system_email_sender()
    sys.exit(0 if success else 1)

