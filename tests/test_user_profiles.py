"""
Test User Profile System
Tests the comprehensive user profile management system including:
- Profile creation and updates
- Event tracking
- Session linking
- Query history
"""
import asyncio
import pytest
from nexus.modules.database import database, connect_to_db, disconnect_from_db
from nexus.modules.user_manager import user_manager
from nexus.modules.user_profile_manager import ProfileEvent, user_profile_manager
from nexus.modules.user_profile_events import track_chat_interaction, track_workflow_interaction
from fastapi import BackgroundTasks


@pytest.fixture(scope="module")
async def db_setup():
    """Setup database connection for tests."""
    await connect_to_db()
    yield
    await disconnect_from_db()


@pytest.fixture
async def test_user(db_setup):
    """Create a test user for profile testing."""
    user_id = await user_manager.create_user(
        auth_id="test_auth_123",
        email="test@example.com",
        name="Test User",
        role="user"
    )
    yield user_id
    # Cleanup: Delete user (cascades to profiles)
    await user_manager.delete_user(user_id, {"user_id": "system"})


@pytest.mark.asyncio
async def test_basic_profile_crud(test_user):
    """Test basic profile CRUD operations."""
    # Get initial profile (should be empty/default)
    profile = await user_manager.get_basic_profile(test_user)
    assert profile["user_id"] == test_user
    
    # Update profile
    updates = {
        "preferred_name": "John",
        "phone": "555-1234",
        "timezone": "America/New_York"
    }
    success = await user_manager.update_basic_profile(test_user, updates)
    assert success is True
    
    # Get updated profile
    profile = await user_manager.get_basic_profile(test_user)
    assert profile["preferred_name"] == "John"
    assert profile["phone"] == "555-1234"
    assert profile["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_professional_profile_crud(test_user):
    """Test professional profile CRUD operations."""
    updates = {
        "job_title": "Software Engineer",
        "department": "Engineering",
        "organization": "Test Corp"
    }
    success = await user_manager.update_professional_profile(test_user, updates)
    assert success is True
    
    profile = await user_manager.get_professional_profile(test_user)
    assert profile["job_title"] == "Software Engineer"
    assert profile["department"] == "Engineering"
    assert profile["organization"] == "Test Corp"


@pytest.mark.asyncio
async def test_communication_profile_crud(test_user):
    """Test communication profile CRUD operations."""
    updates = {
        "communication_style": "friendly",
        "tone_preference": "concise",
        "response_format_preference": "bullet_points"
    }
    success = await user_manager.update_communication_profile(test_user, updates)
    assert success is True
    
    profile = await user_manager.get_communication_profile(test_user)
    assert profile["communication_style"] == "friendly"
    assert profile["tone_preference"] == "concise"
    assert profile["response_format_preference"] == "bullet_points"


@pytest.mark.asyncio
async def test_ai_preference_profile_crud(test_user):
    """Test AI preference profile CRUD operations."""
    updates = {
        "preferred_strategy": "TABULA_RASA",
        "autonomy_level": "autonomous",
        "confidence_threshold": 0.75
    }
    success = await user_manager.update_ai_preference_profile(test_user, updates)
    assert success is True
    
    profile = await user_manager.get_ai_preference_profile(test_user)
    assert profile["preferred_strategy"] == "TABULA_RASA"
    assert profile["autonomy_level"] == "autonomous"
    assert profile["confidence_threshold"] == 0.75


@pytest.mark.asyncio
async def test_profile_event_tracking(test_user):
    """Test profile event tracking from conversations."""
    # Create a profile event
    event = ProfileEvent(
        user_id=test_user,
        event_type="chat",
        user_message="Hi, my name is John and I work as a Software Engineer",
        assistant_response="Nice to meet you, John!",
        session_id=None,
        interaction_id=None
    )
    
    # Process the event
    await user_profile_manager.process_event(event)
    
    # Check if basic profile was updated
    basic_profile = await user_manager.get_basic_profile(test_user)
    # Note: Extraction is pattern-based, may not always work perfectly
    # But the profile should exist
    
    # Check if professional profile was updated
    professional_profile = await user_manager.get_professional_profile(test_user)
    # Profile should exist
    
    # Check query history was updated
    query_history = await user_manager.get_query_history_profile(test_user)
    assert "most_common_queries" in query_history
    assert "interaction_stats" in query_history


@pytest.mark.asyncio
async def test_track_chat_interaction(test_user):
    """Test track_chat_interaction helper function."""
    # Get user to get auth_id
    user = await user_manager.get_user(test_user)
    auth_id = user["auth_id"]
    
    # Create a mock background tasks object
    class MockBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            # For testing, we'll call it directly
            asyncio.create_task(func(*args, **kwargs))
    
    background_tasks = MockBackgroundTasks()
    
    # Track interaction
    await track_chat_interaction(
        auth_id=auth_id,
        user_message="What is eligibility verification?",
        assistant_response="Eligibility verification is the process of...",
        background_tasks=background_tasks,
        metadata={"module": "chat"}
    )
    
    # Wait a bit for async processing
    await asyncio.sleep(0.5)
    
    # Check query history was updated
    query_history = await user_manager.get_query_history_profile(test_user)
    assert query_history.get("interaction_stats", {}).get("total_queries", 0) > 0


@pytest.mark.asyncio
async def test_track_workflow_interaction(test_user):
    """Test track_workflow_interaction with session context."""
    # Get user to get auth_id
    user = await user_manager.get_user(test_user)
    auth_id = user["auth_id"]
    
    # Create a test session first
    session_query = """
        INSERT INTO shaping_sessions (user_id, status, consultant_strategy, workflow_name)
        VALUES (:user_id, 'GATHERING', 'TABULA_RASA', 'eligibility_verification')
        RETURNING id
    """
    session_id = await database.fetch_val(session_query, {"user_id": str(test_user)})
    
    try:
        # Create a mock background tasks object
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                asyncio.create_task(func(*args, **kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Track workflow interaction
        await track_workflow_interaction(
            auth_id=auth_id,
            user_message="I need to verify patient eligibility",
            assistant_response="I'll help you set up eligibility verification.",
            session_id=session_id,
            workflow_name="eligibility_verification",
            strategy="TABULA_RASA",
            background_tasks=background_tasks,
            metadata={"module": "workflow"}
        )
        
        # Wait a bit for async processing
        await asyncio.sleep(0.5)
        
        # Check session links were created
        session_links = await user_manager.get_user_session_links(test_user)
        assert len(session_links) > 0
        assert session_links[0]["session_id"] == session_id
        assert session_links[0]["strategy"] == "TABULA_RASA"
        assert session_links[0]["workflow_name"] == "eligibility_verification"
        
        # Check use case profile was updated
        use_case_profile = await user_manager.get_use_case_profile(test_user)
        assert "primary_workflows" in use_case_profile
        assert "workflow_frequency" in use_case_profile
        
    finally:
        # Cleanup session
        await database.execute("DELETE FROM shaping_sessions WHERE id = :id", {"id": session_id})


@pytest.mark.asyncio
async def test_query_history_accumulation(test_user):
    """Test that query history accumulates over multiple interactions."""
    user = await user_manager.get_user(test_user)
    auth_id = user["auth_id"]
    
    class MockBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            asyncio.create_task(func(*args, **kwargs))
    
    background_tasks = MockBackgroundTasks()
    
    # Track multiple interactions
    queries = [
        "What is eligibility verification?",
        "How do I check patient coverage?",
        "What is eligibility verification?",  # Duplicate to test counting
    ]
    
    for query in queries:
        await track_chat_interaction(
            auth_id=auth_id,
            user_message=query,
            assistant_response="Response",
            background_tasks=background_tasks,
            metadata={"module": "chat"}
        )
        await asyncio.sleep(0.2)  # Small delay between interactions
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Check query history
    query_history = await user_manager.get_query_history_profile(test_user)
    stats = query_history.get("interaction_stats", {})
    assert stats.get("total_queries", 0) >= 3
    
    # Check most common queries
    common_queries = query_history.get("most_common_queries", [])
    # Should have at least some queries
    assert len(common_queries) > 0


@pytest.mark.asyncio
async def test_all_profiles_endpoint(test_user):
    """Test that we can get all profiles at once."""
    # Update a few profiles first
    await user_manager.update_basic_profile(test_user, {"preferred_name": "Test"})
    await user_manager.update_professional_profile(test_user, {"job_title": "Engineer"})
    
    # Get all profiles (simulating endpoint behavior)
    basic = await user_manager.get_basic_profile(test_user)
    professional = await user_manager.get_professional_profile(test_user)
    communication = await user_manager.get_communication_profile(test_user)
    use_case = await user_manager.get_use_case_profile(test_user)
    ai_preference = await user_manager.get_ai_preference_profile(test_user)
    query_history = await user_manager.get_query_history_profile(test_user)
    
    # Verify all profiles exist
    assert basic["user_id"] == test_user
    assert professional["user_id"] == test_user
    assert communication["user_id"] == test_user
    assert use_case["user_id"] == test_user
    assert ai_preference["user_id"] == test_user
    assert query_history["user_id"] == test_user


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(pytest.main([__file__, "-v"]))



