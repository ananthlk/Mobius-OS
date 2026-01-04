"""
Test script for Communication Tools
Tests: patient_email_sender, patient_sms_sender, patient_calendar_manager, patient_insurance_collector
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.communication.email_tool import PatientEmailSender
from nexus.tools.communication.sms_tool import PatientSMSSender
from nexus.tools.communication.calendar_tool import PatientCalendarManager
from nexus.tools.eligibility.gate1_data_retrieval import PatientInsuranceCollector


def test_patient_email_sender():
    """Test PatientEmailSender tool"""
    print("\n" + "=" * 80)
    print("Testing: PatientEmailSender")
    print("=" * 80)
    
    try:
        import os
        
        # Check for email credentials
        email_password = os.getenv("EMAIL_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD")
        has_credentials = bool(email_password)
        
        if not has_credentials:
            print("\n📧 Email Configuration Status:")
            print("   ⚠️  Email password not configured")
            print("   The tool will run in MOCK mode (no actual email sent)")
            print("\n   To enable SMTP email sending:")
            print("   1. Set environment variable: export EMAIL_PASSWORD='your-app-password'")
            print("   2. Or add to .env file: EMAIL_PASSWORD=your-app-password")
            print("   3. Use Gmail App Password (recommended):")
            print("      - Go to Google Account > Security > 2-Step Verification")
            print("      - Generate an App Password for 'Mail'")
            print("      - Use that password in EMAIL_PASSWORD")
            print("   4. System email: mobiushealthai@gmail.com")
            print("   5. Test recipient: ananth.lalithakumar@gmail.com")
            print()
        else:
            print("\n📧 Email Configuration Status:")
            print("   ✅ Email password configured - SMTP mode enabled")
            print(f"   System email: mobiushealthai@gmail.com")
            print(f"   Test recipient: ananth.lalithakumar@gmail.com")
            print()
        
        tool = PatientEmailSender()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            subject="Test Email - Appointment Reminder",
            body="This is a test email body. Please confirm your appointment.",
            priority="high"
        )
        
        print(f"✅ Email tool executed successfully")
        print(f"   Status: {result.get('status')}")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"   SMTP Used: {result.get('smtp_used', False)}")
        
        if result.get('smtp_used'):
            print(f"   ✅ Real email sent via SMTP")
            print(f"   Sender: {result.get('sender')}")
            print(f"   Recipient: {result.get('recipient')}")
        else:
            print(f"   ⚠️  Mock mode - no actual email sent")
            if result.get('warning'):
                print(f"   {result.get('warning')}")
        
        if result.get('error'):
            print(f"   ❌ Error: {result.get('error')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_sms_sender():
    """Test PatientSMSSender tool"""
    print("\n" + "=" * 80)
    print("Testing: PatientSMSSender")
    print("=" * 80)
    
    try:
        tool = PatientSMSSender()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            message="Your appointment is confirmed for tomorrow at 10:00 AM.",
            urgency="high"
        )
        
        print(f"✅ SMS tool executed successfully")
        print(f"   Status: {result.get('status')}")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"   Message Length: {result.get('message_length')} chars")
        print(f"   Estimated Segments: {result.get('estimated_segments')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_calendar_manager():
    """Test PatientCalendarManager tool"""
    print("\n" + "=" * 80)
    print("Testing: PatientCalendarManager")
    print("=" * 80)
    
    try:
        tool = PatientCalendarManager()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        start_time = (datetime.now() + timedelta(days=7)).isoformat()
        end_time = (datetime.now() + timedelta(days=7, hours=1)).isoformat()
        
        result = tool.run(
            patient_id="PATIENT_001",
            event_type="appointment",
            start_time=start_time,
            end_time=end_time,
            title="Annual Checkup",
            location="Main Clinic - Room 101",
            reminder_minutes=60
        )
        
        print(f"✅ Calendar tool executed successfully")
        print(f"   Status: {result.get('status')}")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Event Type: {result.get('event_type')}")
        print(f"   Duration: {result.get('duration_minutes')} minutes")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_insurance_collector():
    """Test PatientInsuranceCollector tool"""
    print("\n" + "=" * 80)
    print("Testing: PatientInsuranceCollector")
    print("=" * 80)
    
    try:
        tool = PatientInsuranceCollector()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            communication_method="email",
            urgency="medium"
        )
        
        print(f"✅ Insurance Collector tool executed successfully")
        print(f"   Status: {result.get('status')}")
        print(f"   Communication Sent: {result.get('communication_sent')}")
        print(f"   Method: {result.get('method')}")
        print(f"   Message ID: {result.get('message_id')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all communication tool tests"""
    print("=" * 80)
    print("COMMUNICATION TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_patient_email_sender,
        test_patient_sms_sender,
        test_patient_calendar_manager,
        test_patient_insurance_collector,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

