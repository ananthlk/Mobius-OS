"""
Test Workflow Interaction Profile Integration
Tests that workflow interactions properly update user profiles.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

async def test_workflow_profile_integration():
    """Test that workflow interactions update user profiles."""
    print("=" * 60)
    print("Testing Workflow Interaction Profile Integration")
    print("=" * 60)
    print()
    
    from nexus.modules.database import database, connect_to_db, disconnect_from_db
    from nexus.modules.user_manager import user_manager
    from nexus.modules.user_profile_events import track_workflow_interaction
    
    await connect_to_db()
    
    try:
        # ============================================================
        # Setup: Create test user
        # ============================================================
        print("[Setup] Creating test user...")
        test_auth_id = "test_workflow_integration_123"
        test_email = "test_workflow_integration@example.com"
        
        existing_user = await user_manager.get_user_by_auth_id(test_auth_id)
        if existing_user:
            test_user_id = existing_user['id']
            print(f"   ⚠️  User already exists, using existing user ID: {test_user_id}")
        else:
            test_user_id = await user_manager.create_user(
                auth_id=test_auth_id,
                email=test_email,
                name="Test Workflow Integration User",
                role="user"
            )
            print(f"   ✅ Created user ID: {test_user_id}")
        
        # ============================================================
        # Test 1: Create a workflow session and track interaction
        # ============================================================
        print("\n[Test 1] Creating workflow session and tracking interaction...")
        
        # Create a test session
        session_query = """
            INSERT INTO shaping_sessions (user_id, status, consultant_strategy, transcript, draft_plan)
            VALUES (:user_id, 'GATHERING', 'TABULA_RASA', '[]'::jsonb, '{}'::jsonb)
            RETURNING id
        """
        session_id = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id}")
        
        # Mock BackgroundTasks
        class MockBackgroundTasks:
            tasks = []
            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Track a workflow interaction (simulating "Check Eligibility" workflow)
        # Note: interaction_id should be a UUID or None
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to check eligibility for a patient",
            assistant_response="I'll help you check eligibility. Please provide the patient's information.",
            session_id=session_id,
            workflow_name="Check Eligibility",
            strategy="TABULA_RASA",
            background_tasks=background_tasks,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        # Wait for async processing
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 2: Verify use case profile was updated
        # ============================================================
        print("\n[Test 2] Verifying use case profile was updated...")
        use_case_profile = await user_manager.get_use_case_profile(test_user_id)
        
        # Parse JSONB fields if they're strings
        import json
        primary_workflows = use_case_profile.get("primary_workflows", [])
        if isinstance(primary_workflows, str):
            primary_workflows = json.loads(primary_workflows) if primary_workflows else []
        
        assert isinstance(primary_workflows, list), "primary_workflows should be a list"
        
        # Check if "Check Eligibility" workflow is in the list
        eligibility_found = any(
            wf.get("name") == "Check Eligibility" 
            for wf in primary_workflows
        )
        assert eligibility_found, "Check Eligibility workflow not found in use case profile"
        print("   ✅ Use case profile updated with 'Check Eligibility' workflow")
        
        # Verify workflow count
        eligibility_wf = next(
            (wf for wf in primary_workflows if wf.get("name") == "Check Eligibility"),
            None
        )
        assert eligibility_wf is not None, "Check Eligibility workflow not found"
        assert eligibility_wf.get("count", 0) >= 1, f"Expected count >= 1, got {eligibility_wf.get('count', 0)}"
        print(f"   ✅ Workflow count: {eligibility_wf.get('count', 0)}")
        
        # ============================================================
        # Test 3: Track another workflow interaction (Insurance Billing)
        # ============================================================
        print("\n[Test 3] Tracking another workflow interaction (Insurance Billing)...")
        
        # Create another session
        session_id_2 = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id_2}")
        
        background_tasks_2 = MockBackgroundTasks()
        
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to process insurance billing",
            assistant_response="I'll help you process insurance billing. Let me gather the necessary information.",
            session_id=session_id_2,
            workflow_name="Insurance Billing",
            strategy="EVIDENCE_BASED",
            background_tasks=background_tasks_2,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked Insurance Billing workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks_2.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 4: Verify both workflows are in use case profile
        # ============================================================
        print("\n[Test 4] Verifying both workflows are in use case profile...")
        use_case_profile_2 = await user_manager.get_use_case_profile(test_user_id)
        
        primary_workflows_2 = use_case_profile_2.get("primary_workflows", [])
        if isinstance(primary_workflows_2, str):
            primary_workflows_2 = json.loads(primary_workflows_2) if primary_workflows_2 else []
        
        workflow_names = [wf.get("name") for wf in primary_workflows_2]
        assert "Check Eligibility" in workflow_names, "Check Eligibility not found"
        assert "Insurance Billing" in workflow_names, "Insurance Billing not found"
        print(f"   ✅ Found workflows: {', '.join(workflow_names)}")
        
        # ============================================================
        # Test 5: Verify session links were created
        # ============================================================
        print("\n[Test 5] Verifying session links were created...")
        session_links = await user_manager.get_user_session_links(test_user_id, limit=10)
        
        assert len(session_links) >= 2, f"Expected at least 2 session links, got {len(session_links)}"
        
        session_ids = [link["session_id"] for link in session_links]
        assert session_id in session_ids, f"Session {session_id} not found in links"
        assert session_id_2 in session_ids, f"Session {session_id_2} not found in links"
        print(f"   ✅ Found {len(session_links)} session links")
        
        # Verify workflow names in session links
        eligibility_link = next((link for link in session_links if link.get("workflow_name") == "Check Eligibility"), None)
        billing_link = next((link for link in session_links if link.get("workflow_name") == "Insurance Billing"), None)
        
        assert eligibility_link is not None, "Check Eligibility session link not found"
        assert billing_link is not None, "Insurance Billing session link not found"
        print("   ✅ Session links contain workflow names")
        
        # ============================================================
        # Test 6: Verify query history was updated
        # ============================================================
        print("\n[Test 6] Verifying query history was updated...")
        query_history = await user_manager.get_query_history_profile(test_user_id)
        
        interaction_stats = query_history.get("interaction_stats", {})
        if isinstance(interaction_stats, str):
            interaction_stats = json.loads(interaction_stats) if interaction_stats else {}
        
        total_queries = interaction_stats.get("total_queries", 0)
        assert total_queries >= 2, f"Expected at least 2 queries, got {total_queries}"
        print(f"   ✅ Total queries tracked: {total_queries}")
        
        # Clean up test sessions
        await database.execute("DELETE FROM shaping_sessions WHERE id IN (:id1, :id2)", {
            "id1": session_id,
            "id2": session_id_2
        })
        print("   ✅ Cleaned up test sessions")
        
        print("\n" + "=" * 60)
        print("✅ ALL WORKFLOW INTEGRATION TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(test_workflow_profile_integration())


Tests that workflow interactions properly update user profiles.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

async def test_workflow_profile_integration():
    """Test that workflow interactions update user profiles."""
    print("=" * 60)
    print("Testing Workflow Interaction Profile Integration")
    print("=" * 60)
    print()
    
    from nexus.modules.database import database, connect_to_db, disconnect_from_db
    from nexus.modules.user_manager import user_manager
    from nexus.modules.user_profile_events import track_workflow_interaction
    
    await connect_to_db()
    
    try:
        # ============================================================
        # Setup: Create test user
        # ============================================================
        print("[Setup] Creating test user...")
        test_auth_id = "test_workflow_integration_123"
        test_email = "test_workflow_integration@example.com"
        
        existing_user = await user_manager.get_user_by_auth_id(test_auth_id)
        if existing_user:
            test_user_id = existing_user['id']
            print(f"   ⚠️  User already exists, using existing user ID: {test_user_id}")
        else:
            test_user_id = await user_manager.create_user(
                auth_id=test_auth_id,
                email=test_email,
                name="Test Workflow Integration User",
                role="user"
            )
            print(f"   ✅ Created user ID: {test_user_id}")
        
        # ============================================================
        # Test 1: Create a workflow session and track interaction
        # ============================================================
        print("\n[Test 1] Creating workflow session and tracking interaction...")
        
        # Create a test session
        session_query = """
            INSERT INTO shaping_sessions (user_id, status, consultant_strategy, transcript, draft_plan)
            VALUES (:user_id, 'GATHERING', 'TABULA_RASA', '[]'::jsonb, '{}'::jsonb)
            RETURNING id
        """
        session_id = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id}")
        
        # Mock BackgroundTasks
        class MockBackgroundTasks:
            tasks = []
            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Track a workflow interaction (simulating "Check Eligibility" workflow)
        # Note: interaction_id should be a UUID or None
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to check eligibility for a patient",
            assistant_response="I'll help you check eligibility. Please provide the patient's information.",
            session_id=session_id,
            workflow_name="Check Eligibility",
            strategy="TABULA_RASA",
            background_tasks=background_tasks,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        # Wait for async processing
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 2: Verify use case profile was updated
        # ============================================================
        print("\n[Test 2] Verifying use case profile was updated...")
        use_case_profile = await user_manager.get_use_case_profile(test_user_id)
        
        # Parse JSONB fields if they're strings
        import json
        primary_workflows = use_case_profile.get("primary_workflows", [])
        if isinstance(primary_workflows, str):
            primary_workflows = json.loads(primary_workflows) if primary_workflows else []
        
        assert isinstance(primary_workflows, list), "primary_workflows should be a list"
        
        # Check if "Check Eligibility" workflow is in the list
        eligibility_found = any(
            wf.get("name") == "Check Eligibility" 
            for wf in primary_workflows
        )
        assert eligibility_found, "Check Eligibility workflow not found in use case profile"
        print("   ✅ Use case profile updated with 'Check Eligibility' workflow")
        
        # Verify workflow count
        eligibility_wf = next(
            (wf for wf in primary_workflows if wf.get("name") == "Check Eligibility"),
            None
        )
        assert eligibility_wf is not None, "Check Eligibility workflow not found"
        assert eligibility_wf.get("count", 0) >= 1, f"Expected count >= 1, got {eligibility_wf.get('count', 0)}"
        print(f"   ✅ Workflow count: {eligibility_wf.get('count', 0)}")
        
        # ============================================================
        # Test 3: Track another workflow interaction (Insurance Billing)
        # ============================================================
        print("\n[Test 3] Tracking another workflow interaction (Insurance Billing)...")
        
        # Create another session
        session_id_2 = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id_2}")
        
        background_tasks_2 = MockBackgroundTasks()
        
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to process insurance billing",
            assistant_response="I'll help you process insurance billing. Let me gather the necessary information.",
            session_id=session_id_2,
            workflow_name="Insurance Billing",
            strategy="EVIDENCE_BASED",
            background_tasks=background_tasks_2,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked Insurance Billing workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks_2.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 4: Verify both workflows are in use case profile
        # ============================================================
        print("\n[Test 4] Verifying both workflows are in use case profile...")
        use_case_profile_2 = await user_manager.get_use_case_profile(test_user_id)
        
        primary_workflows_2 = use_case_profile_2.get("primary_workflows", [])
        if isinstance(primary_workflows_2, str):
            primary_workflows_2 = json.loads(primary_workflows_2) if primary_workflows_2 else []
        
        workflow_names = [wf.get("name") for wf in primary_workflows_2]
        assert "Check Eligibility" in workflow_names, "Check Eligibility not found"
        assert "Insurance Billing" in workflow_names, "Insurance Billing not found"
        print(f"   ✅ Found workflows: {', '.join(workflow_names)}")
        
        # ============================================================
        # Test 5: Verify session links were created
        # ============================================================
        print("\n[Test 5] Verifying session links were created...")
        session_links = await user_manager.get_user_session_links(test_user_id, limit=10)
        
        assert len(session_links) >= 2, f"Expected at least 2 session links, got {len(session_links)}"
        
        session_ids = [link["session_id"] for link in session_links]
        assert session_id in session_ids, f"Session {session_id} not found in links"
        assert session_id_2 in session_ids, f"Session {session_id_2} not found in links"
        print(f"   ✅ Found {len(session_links)} session links")
        
        # Verify workflow names in session links
        eligibility_link = next((link for link in session_links if link.get("workflow_name") == "Check Eligibility"), None)
        billing_link = next((link for link in session_links if link.get("workflow_name") == "Insurance Billing"), None)
        
        assert eligibility_link is not None, "Check Eligibility session link not found"
        assert billing_link is not None, "Insurance Billing session link not found"
        print("   ✅ Session links contain workflow names")
        
        # ============================================================
        # Test 6: Verify query history was updated
        # ============================================================
        print("\n[Test 6] Verifying query history was updated...")
        query_history = await user_manager.get_query_history_profile(test_user_id)
        
        interaction_stats = query_history.get("interaction_stats", {})
        if isinstance(interaction_stats, str):
            interaction_stats = json.loads(interaction_stats) if interaction_stats else {}
        
        total_queries = interaction_stats.get("total_queries", 0)
        assert total_queries >= 2, f"Expected at least 2 queries, got {total_queries}"
        print(f"   ✅ Total queries tracked: {total_queries}")
        
        # Clean up test sessions
        await database.execute("DELETE FROM shaping_sessions WHERE id IN (:id1, :id2)", {
            "id1": session_id,
            "id2": session_id_2
        })
        print("   ✅ Cleaned up test sessions")
        
        print("\n" + "=" * 60)
        print("✅ ALL WORKFLOW INTEGRATION TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(test_workflow_profile_integration())


Tests that workflow interactions properly update user profiles.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

async def test_workflow_profile_integration():
    """Test that workflow interactions update user profiles."""
    print("=" * 60)
    print("Testing Workflow Interaction Profile Integration")
    print("=" * 60)
    print()
    
    from nexus.modules.database import database, connect_to_db, disconnect_from_db
    from nexus.modules.user_manager import user_manager
    from nexus.modules.user_profile_events import track_workflow_interaction
    
    await connect_to_db()
    
    try:
        # ============================================================
        # Setup: Create test user
        # ============================================================
        print("[Setup] Creating test user...")
        test_auth_id = "test_workflow_integration_123"
        test_email = "test_workflow_integration@example.com"
        
        existing_user = await user_manager.get_user_by_auth_id(test_auth_id)
        if existing_user:
            test_user_id = existing_user['id']
            print(f"   ⚠️  User already exists, using existing user ID: {test_user_id}")
        else:
            test_user_id = await user_manager.create_user(
                auth_id=test_auth_id,
                email=test_email,
                name="Test Workflow Integration User",
                role="user"
            )
            print(f"   ✅ Created user ID: {test_user_id}")
        
        # ============================================================
        # Test 1: Create a workflow session and track interaction
        # ============================================================
        print("\n[Test 1] Creating workflow session and tracking interaction...")
        
        # Create a test session
        session_query = """
            INSERT INTO shaping_sessions (user_id, status, consultant_strategy, transcript, draft_plan)
            VALUES (:user_id, 'GATHERING', 'TABULA_RASA', '[]'::jsonb, '{}'::jsonb)
            RETURNING id
        """
        session_id = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id}")
        
        # Mock BackgroundTasks
        class MockBackgroundTasks:
            tasks = []
            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Track a workflow interaction (simulating "Check Eligibility" workflow)
        # Note: interaction_id should be a UUID or None
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to check eligibility for a patient",
            assistant_response="I'll help you check eligibility. Please provide the patient's information.",
            session_id=session_id,
            workflow_name="Check Eligibility",
            strategy="TABULA_RASA",
            background_tasks=background_tasks,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        # Wait for async processing
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 2: Verify use case profile was updated
        # ============================================================
        print("\n[Test 2] Verifying use case profile was updated...")
        use_case_profile = await user_manager.get_use_case_profile(test_user_id)
        
        # Parse JSONB fields if they're strings
        import json
        primary_workflows = use_case_profile.get("primary_workflows", [])
        if isinstance(primary_workflows, str):
            primary_workflows = json.loads(primary_workflows) if primary_workflows else []
        
        assert isinstance(primary_workflows, list), "primary_workflows should be a list"
        
        # Check if "Check Eligibility" workflow is in the list
        eligibility_found = any(
            wf.get("name") == "Check Eligibility" 
            for wf in primary_workflows
        )
        assert eligibility_found, "Check Eligibility workflow not found in use case profile"
        print("   ✅ Use case profile updated with 'Check Eligibility' workflow")
        
        # Verify workflow count
        eligibility_wf = next(
            (wf for wf in primary_workflows if wf.get("name") == "Check Eligibility"),
            None
        )
        assert eligibility_wf is not None, "Check Eligibility workflow not found"
        assert eligibility_wf.get("count", 0) >= 1, f"Expected count >= 1, got {eligibility_wf.get('count', 0)}"
        print(f"   ✅ Workflow count: {eligibility_wf.get('count', 0)}")
        
        # ============================================================
        # Test 3: Track another workflow interaction (Insurance Billing)
        # ============================================================
        print("\n[Test 3] Tracking another workflow interaction (Insurance Billing)...")
        
        # Create another session
        session_id_2 = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id_2}")
        
        background_tasks_2 = MockBackgroundTasks()
        
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to process insurance billing",
            assistant_response="I'll help you process insurance billing. Let me gather the necessary information.",
            session_id=session_id_2,
            workflow_name="Insurance Billing",
            strategy="EVIDENCE_BASED",
            background_tasks=background_tasks_2,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked Insurance Billing workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks_2.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 4: Verify both workflows are in use case profile
        # ============================================================
        print("\n[Test 4] Verifying both workflows are in use case profile...")
        use_case_profile_2 = await user_manager.get_use_case_profile(test_user_id)
        
        primary_workflows_2 = use_case_profile_2.get("primary_workflows", [])
        if isinstance(primary_workflows_2, str):
            primary_workflows_2 = json.loads(primary_workflows_2) if primary_workflows_2 else []
        
        workflow_names = [wf.get("name") for wf in primary_workflows_2]
        assert "Check Eligibility" in workflow_names, "Check Eligibility not found"
        assert "Insurance Billing" in workflow_names, "Insurance Billing not found"
        print(f"   ✅ Found workflows: {', '.join(workflow_names)}")
        
        # ============================================================
        # Test 5: Verify session links were created
        # ============================================================
        print("\n[Test 5] Verifying session links were created...")
        session_links = await user_manager.get_user_session_links(test_user_id, limit=10)
        
        assert len(session_links) >= 2, f"Expected at least 2 session links, got {len(session_links)}"
        
        session_ids = [link["session_id"] for link in session_links]
        assert session_id in session_ids, f"Session {session_id} not found in links"
        assert session_id_2 in session_ids, f"Session {session_id_2} not found in links"
        print(f"   ✅ Found {len(session_links)} session links")
        
        # Verify workflow names in session links
        eligibility_link = next((link for link in session_links if link.get("workflow_name") == "Check Eligibility"), None)
        billing_link = next((link for link in session_links if link.get("workflow_name") == "Insurance Billing"), None)
        
        assert eligibility_link is not None, "Check Eligibility session link not found"
        assert billing_link is not None, "Insurance Billing session link not found"
        print("   ✅ Session links contain workflow names")
        
        # ============================================================
        # Test 6: Verify query history was updated
        # ============================================================
        print("\n[Test 6] Verifying query history was updated...")
        query_history = await user_manager.get_query_history_profile(test_user_id)
        
        interaction_stats = query_history.get("interaction_stats", {})
        if isinstance(interaction_stats, str):
            interaction_stats = json.loads(interaction_stats) if interaction_stats else {}
        
        total_queries = interaction_stats.get("total_queries", 0)
        assert total_queries >= 2, f"Expected at least 2 queries, got {total_queries}"
        print(f"   ✅ Total queries tracked: {total_queries}")
        
        # Clean up test sessions
        await database.execute("DELETE FROM shaping_sessions WHERE id IN (:id1, :id2)", {
            "id1": session_id,
            "id2": session_id_2
        })
        print("   ✅ Cleaned up test sessions")
        
        print("\n" + "=" * 60)
        print("✅ ALL WORKFLOW INTEGRATION TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(test_workflow_profile_integration())


Tests that workflow interactions properly update user profiles.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

async def test_workflow_profile_integration():
    """Test that workflow interactions update user profiles."""
    print("=" * 60)
    print("Testing Workflow Interaction Profile Integration")
    print("=" * 60)
    print()
    
    from nexus.modules.database import database, connect_to_db, disconnect_from_db
    from nexus.modules.user_manager import user_manager
    from nexus.modules.user_profile_events import track_workflow_interaction
    
    await connect_to_db()
    
    try:
        # ============================================================
        # Setup: Create test user
        # ============================================================
        print("[Setup] Creating test user...")
        test_auth_id = "test_workflow_integration_123"
        test_email = "test_workflow_integration@example.com"
        
        existing_user = await user_manager.get_user_by_auth_id(test_auth_id)
        if existing_user:
            test_user_id = existing_user['id']
            print(f"   ⚠️  User already exists, using existing user ID: {test_user_id}")
        else:
            test_user_id = await user_manager.create_user(
                auth_id=test_auth_id,
                email=test_email,
                name="Test Workflow Integration User",
                role="user"
            )
            print(f"   ✅ Created user ID: {test_user_id}")
        
        # ============================================================
        # Test 1: Create a workflow session and track interaction
        # ============================================================
        print("\n[Test 1] Creating workflow session and tracking interaction...")
        
        # Create a test session
        session_query = """
            INSERT INTO shaping_sessions (user_id, status, consultant_strategy, transcript, draft_plan)
            VALUES (:user_id, 'GATHERING', 'TABULA_RASA', '[]'::jsonb, '{}'::jsonb)
            RETURNING id
        """
        session_id = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id}")
        
        # Mock BackgroundTasks
        class MockBackgroundTasks:
            tasks = []
            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Track a workflow interaction (simulating "Check Eligibility" workflow)
        # Note: interaction_id should be a UUID or None
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to check eligibility for a patient",
            assistant_response="I'll help you check eligibility. Please provide the patient's information.",
            session_id=session_id,
            workflow_name="Check Eligibility",
            strategy="TABULA_RASA",
            background_tasks=background_tasks,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        # Wait for async processing
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 2: Verify use case profile was updated
        # ============================================================
        print("\n[Test 2] Verifying use case profile was updated...")
        use_case_profile = await user_manager.get_use_case_profile(test_user_id)
        
        # Parse JSONB fields if they're strings
        import json
        primary_workflows = use_case_profile.get("primary_workflows", [])
        if isinstance(primary_workflows, str):
            primary_workflows = json.loads(primary_workflows) if primary_workflows else []
        
        assert isinstance(primary_workflows, list), "primary_workflows should be a list"
        
        # Check if "Check Eligibility" workflow is in the list
        eligibility_found = any(
            wf.get("name") == "Check Eligibility" 
            for wf in primary_workflows
        )
        assert eligibility_found, "Check Eligibility workflow not found in use case profile"
        print("   ✅ Use case profile updated with 'Check Eligibility' workflow")
        
        # Verify workflow count
        eligibility_wf = next(
            (wf for wf in primary_workflows if wf.get("name") == "Check Eligibility"),
            None
        )
        assert eligibility_wf is not None, "Check Eligibility workflow not found"
        assert eligibility_wf.get("count", 0) >= 1, f"Expected count >= 1, got {eligibility_wf.get('count', 0)}"
        print(f"   ✅ Workflow count: {eligibility_wf.get('count', 0)}")
        
        # ============================================================
        # Test 3: Track another workflow interaction (Insurance Billing)
        # ============================================================
        print("\n[Test 3] Tracking another workflow interaction (Insurance Billing)...")
        
        # Create another session
        session_id_2 = await database.fetch_val(session_query, {"user_id": str(test_user_id)})
        print(f"   ✅ Created test session ID: {session_id_2}")
        
        background_tasks_2 = MockBackgroundTasks()
        
        await track_workflow_interaction(
            auth_id=test_auth_id,
            user_message="I need to process insurance billing",
            assistant_response="I'll help you process insurance billing. Let me gather the necessary information.",
            session_id=session_id_2,
            workflow_name="Insurance Billing",
            strategy="EVIDENCE_BASED",
            background_tasks=background_tasks_2,
            interaction_id=None  # Set to None since we don't have a real interaction ID
        )
        print("   ✅ Tracked Insurance Billing workflow interaction")
        
        # Execute background tasks
        for func, args, kwargs in background_tasks_2.tasks:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                print(f"   ⚠️  Background task error: {e}")
        
        await asyncio.sleep(1)
        
        # ============================================================
        # Test 4: Verify both workflows are in use case profile
        # ============================================================
        print("\n[Test 4] Verifying both workflows are in use case profile...")
        use_case_profile_2 = await user_manager.get_use_case_profile(test_user_id)
        
        primary_workflows_2 = use_case_profile_2.get("primary_workflows", [])
        if isinstance(primary_workflows_2, str):
            primary_workflows_2 = json.loads(primary_workflows_2) if primary_workflows_2 else []
        
        workflow_names = [wf.get("name") for wf in primary_workflows_2]
        assert "Check Eligibility" in workflow_names, "Check Eligibility not found"
        assert "Insurance Billing" in workflow_names, "Insurance Billing not found"
        print(f"   ✅ Found workflows: {', '.join(workflow_names)}")
        
        # ============================================================
        # Test 5: Verify session links were created
        # ============================================================
        print("\n[Test 5] Verifying session links were created...")
        session_links = await user_manager.get_user_session_links(test_user_id, limit=10)
        
        assert len(session_links) >= 2, f"Expected at least 2 session links, got {len(session_links)}"
        
        session_ids = [link["session_id"] for link in session_links]
        assert session_id in session_ids, f"Session {session_id} not found in links"
        assert session_id_2 in session_ids, f"Session {session_id_2} not found in links"
        print(f"   ✅ Found {len(session_links)} session links")
        
        # Verify workflow names in session links
        eligibility_link = next((link for link in session_links if link.get("workflow_name") == "Check Eligibility"), None)
        billing_link = next((link for link in session_links if link.get("workflow_name") == "Insurance Billing"), None)
        
        assert eligibility_link is not None, "Check Eligibility session link not found"
        assert billing_link is not None, "Insurance Billing session link not found"
        print("   ✅ Session links contain workflow names")
        
        # ============================================================
        # Test 6: Verify query history was updated
        # ============================================================
        print("\n[Test 6] Verifying query history was updated...")
        query_history = await user_manager.get_query_history_profile(test_user_id)
        
        interaction_stats = query_history.get("interaction_stats", {})
        if isinstance(interaction_stats, str):
            interaction_stats = json.loads(interaction_stats) if interaction_stats else {}
        
        total_queries = interaction_stats.get("total_queries", 0)
        assert total_queries >= 2, f"Expected at least 2 queries, got {total_queries}"
        print(f"   ✅ Total queries tracked: {total_queries}")
        
        # Clean up test sessions
        await database.execute("DELETE FROM shaping_sessions WHERE id IN (:id1, :id2)", {
            "id1": session_id,
            "id2": session_id_2
        })
        print("   ✅ Cleaned up test sessions")
        
        print("\n" + "=" * 60)
        print("✅ ALL WORKFLOW INTEGRATION TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(test_workflow_profile_integration())

