"""
Test User Account Profile System
Tests the comprehensive user profile management system.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

async def test_user_profile_system():
    """Test the complete user profile system."""
    print("=" * 60)
    print("Testing User Account Profile System")
    print("=" * 60)
    print()
    
    from nexus.modules.database import database, connect_to_db, disconnect_from_db
    from nexus.modules.user_manager import user_manager
    from nexus.modules.user_profile_manager import ProfileEvent, user_profile_manager
    from nexus.modules.user_profile_events import track_chat_interaction, track_workflow_interaction
    
    await connect_to_db()
    
    try:
        # ============================================================
        # Test 1: Create User
        # ============================================================
        print("[Test 1] Creating test user...")
        test_auth_id = "test_profile_auth_123"
        test_email = "test_profile@example.com"
        
        # Check if user already exists
        existing_user = await user_manager.get_user_by_auth_id(test_auth_id)
        if existing_user:
            print(f"   ⚠️  User already exists, using existing user ID: {existing_user['id']}")
            test_user_id = existing_user['id']
        else:
            test_user_id = await user_manager.create_user(
                auth_id=test_auth_id,
                email=test_email,
                name="Test Profile User",
                role="user"
            )
            print(f"   ✅ Created user ID: {test_user_id}")
        
        # ============================================================
        # Test 2: Basic Profile CRUD
        # ============================================================
        print("\n[Test 2] Testing Basic Profile CRUD...")
        basic_updates = {
            "preferred_name": "John",
            "phone": "555-1234",
            "mobile": "555-5678",
            "timezone": "America/New_York"
        }
        success = await user_manager.update_basic_profile(test_user_id, basic_updates)
        assert success, "Failed to update basic profile"
        print("   ✅ Updated basic profile")
        
        basic_profile = await user_manager.get_basic_profile(test_user_id)
        assert basic_profile["preferred_name"] == "John", "Preferred name not set"
        assert basic_profile["phone"] == "555-1234", "Phone not set"
        print("   ✅ Retrieved basic profile - all fields correct")
        
        # ============================================================
        # Test 3: Professional Profile CRUD
        # ============================================================
        print("\n[Test 3] Testing Professional Profile CRUD...")
        professional_updates = {
            "job_title": "Software Engineer",
            "department": "Engineering",
            "organization": "Test Corp"
        }
        success = await user_manager.update_professional_profile(test_user_id, professional_updates)
        assert success, "Failed to update professional profile"
        print("   ✅ Updated professional profile")
        
        professional_profile = await user_manager.get_professional_profile(test_user_id)
        assert professional_profile["job_title"] == "Software Engineer", "Job title not set"
        print("   ✅ Retrieved professional profile - all fields correct")
        
        # ============================================================
        # Test 4: Communication Profile CRUD
        # ============================================================
        print("\n[Test 4] Testing Communication Profile CRUD...")
        communication_updates = {
            "communication_style": "friendly",
            "tone_preference": "concise",
            "response_format_preference": "bullet_points"
        }
        success = await user_manager.update_communication_profile(test_user_id, communication_updates)
        assert success, "Failed to update communication profile"
        print("   ✅ Updated communication profile")
        
        communication_profile = await user_manager.get_communication_profile(test_user_id)
        assert communication_profile["communication_style"] == "friendly", "Communication style not set"
        print("   ✅ Retrieved communication profile - all fields correct")
        
        # ============================================================
        # Test 5: AI Preference Profile CRUD
        # ============================================================
        print("\n[Test 5] Testing AI Preference Profile CRUD...")
        ai_updates = {
            "preferred_strategy": "TABULA_RASA",
            "autonomy_level": "autonomous",
            "confidence_threshold": 0.75
        }
        success = await user_manager.update_ai_preference_profile(test_user_id, ai_updates)
        assert success, "Failed to update AI preference profile"
        print("   ✅ Updated AI preference profile")
        
        ai_profile = await user_manager.get_ai_preference_profile(test_user_id)
        assert ai_profile["preferred_strategy"] == "TABULA_RASA", "Preferred strategy not set"
        assert ai_profile["autonomy_level"] == "autonomous", "Autonomy level not set"
        print("   ✅ Retrieved AI preference profile - all fields correct")
        
        # ============================================================
        # Test 6: Profile Event Tracking
        # ============================================================
        print("\n[Test 6] Testing Profile Event Tracking...")
        event = ProfileEvent(
            user_id=test_user_id,
            event_type="chat",
            user_message="Hi, my name is John and I work as a Software Engineer at Test Corp",
            assistant_response="Nice to meet you, John!",
            session_id=None,
            interaction_id=None
        )
        
        await user_profile_manager.process_event(event)
        print("   ✅ Processed profile event")
        
        # Wait a bit for async processing
        await asyncio.sleep(0.5)
        
        # Check query history was updated
        query_history = await user_manager.get_query_history_profile(test_user_id)
        assert "most_common_queries" in query_history, "Query history not created"
        assert "interaction_stats" in query_history, "Interaction stats not created"
        stats = query_history.get("interaction_stats", {})
        # Handle case where stats might be a string (JSONB)
        if isinstance(stats, str):
            import json
            stats = json.loads(stats) if stats else {}
        assert stats.get("total_queries", 0) > 0, "Total queries not incremented"
        print("   ✅ Query history updated correctly")
        
        # ============================================================
        # Test 7: Track Chat Interaction
        # ============================================================
        print("\n[Test 7] Testing track_chat_interaction helper...")
        
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                asyncio.create_task(func(*args, **kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        await track_chat_interaction(
            auth_id=test_auth_id,
            user_message="What is eligibility verification?",
            assistant_response="Eligibility verification is the process of checking...",
            background_tasks=background_tasks,
            metadata={"module": "chat"}
        )
        
        await asyncio.sleep(0.5)
        
        query_history = await user_manager.get_query_history_profile(test_user_id)
        stats = query_history.get("interaction_stats", {})
        # Handle case where stats might be a string (JSONB)
        if isinstance(stats, str):
            import json
            stats = json.loads(stats) if stats else {}
        assert stats.get("total_queries", 0) > 0, "Chat interaction not tracked"
        print("   ✅ Chat interaction tracked successfully")
        
        # ============================================================
        # Test 8: Track Workflow Interaction with Session
        # ============================================================
        print("\n[Test 8] Testing track_workflow_interaction with session...")
        
        # Create a test session (workflow_name doesn't exist in shaping_sessions, we'll pass it in metadata)
        session_query = """
            INSERT INTO shaping_sessions (user_id, status, consultant_strategy)
            VALUES (:user_id, 'GATHERING', 'TABULA_RASA')
            RETURNING id
        """
        session_id = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id}")
        
        try:
            await track_workflow_interaction(
                auth_id=test_auth_id,
                user_message="I need to verify patient eligibility",
                assistant_response="I'll help you set up eligibility verification.",
                session_id=session_id,
                workflow_name="eligibility_verification",
                strategy="TABULA_RASA",
                background_tasks=background_tasks,
                metadata={"module": "workflow"}
            )
            
            await asyncio.sleep(0.5)
            
            # Check session links
            session_links = await user_manager.get_user_session_links(test_user_id)
            assert len(session_links) > 0, "Session links not created"
            assert session_links[0]["session_id"] == session_id, "Session ID mismatch"
            assert session_links[0]["strategy"] == "TABULA_RASA", "Strategy not set"
            print("   ✅ Session links created correctly")
            
            # Check use case profile
            use_case_profile = await user_manager.get_use_case_profile(test_user_id)
            assert "primary_workflows" in use_case_profile, "Use case profile not updated"
            workflows = use_case_profile.get("primary_workflows", [])
            assert len(workflows) > 0, "Workflows not tracked"
            print("   ✅ Use case profile updated with workflow")
            
        finally:
            # Cleanup session
            await database.execute("DELETE FROM shaping_sessions WHERE id = :id", {"id": session_id})
            print("   ✅ Cleaned up test session")
        
        # ============================================================
        # Test 9: Get All Profiles
        # ============================================================
        print("\n[Test 9] Testing get all profiles...")
        basic = await user_manager.get_basic_profile(test_user_id)
        professional = await user_manager.get_professional_profile(test_user_id)
        communication = await user_manager.get_communication_profile(test_user_id)
        use_case = await user_manager.get_use_case_profile(test_user_id)
        ai_preference = await user_manager.get_ai_preference_profile(test_user_id)
        query_history = await user_manager.get_query_history_profile(test_user_id)
        
        assert all(p["user_id"] == test_user_id for p in [basic, professional, communication, use_case, ai_preference, query_history]), "Profile user IDs don't match"
        print("   ✅ All profiles retrieved successfully")
        
        # ============================================================
        # Test 10: Query History Accumulation
        # ============================================================
        print("\n[Test 10] Testing query history accumulation...")
        initial_stats = query_history.get("interaction_stats", {})
        # Handle case where stats might be a string (JSONB)
        if isinstance(initial_stats, str):
            import json
            initial_stats = json.loads(initial_stats) if initial_stats else {}
        initial_count = initial_stats.get("total_queries", 0)
        
        # Track multiple interactions
        queries = [
            "How do I check patient coverage?",
            "What documents are needed?",
        ]
        
        for query in queries:
            await track_chat_interaction(
                auth_id=test_auth_id,
                user_message=query,
                assistant_response="Response",
                background_tasks=background_tasks,
                metadata={"module": "chat"}
            )
            await asyncio.sleep(0.2)
        
        await asyncio.sleep(1)
        
        final_query_history = await user_manager.get_query_history_profile(test_user_id)
        final_stats = final_query_history.get("interaction_stats", {})
        # Handle case where stats might be a string (JSONB)
        if isinstance(final_stats, str):
            import json
            final_stats = json.loads(final_stats) if final_stats else {}
        final_count = final_stats.get("total_queries", 0)
        
        assert final_count >= initial_count + 2, f"Query count didn't increase (initial: {initial_count}, final: {final_count})"
        print(f"   ✅ Query history accumulated (initial: {initial_count}, final: {final_count})")
        
        # ============================================================
        # Summary
        # ============================================================
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\nTest User ID: {test_user_id}")
        print(f"Test Auth ID: {test_auth_id}")
        print(f"Test Email: {test_email}")
        print("\nNote: Test user was created/used. You may want to clean it up manually.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await disconnect_from_db()


if __name__ == "__main__":
    success = asyncio.run(test_user_profile_system())
    exit(0 if success else 1)

