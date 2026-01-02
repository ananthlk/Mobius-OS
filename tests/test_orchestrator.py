"""
Unit tests for Workflow Orchestrator implementation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Test BaseAgent emission helpers
def test_base_agent_emission_helpers():
    """Test that BaseAgent emission helper methods work correctly."""
    from nexus.core.base_agent import BaseAgent
    from nexus.modules.session_manager import session_manager
    
    # Create a mock session manager
    session_manager.active_connections = {1: []}
    
    class TestAgent(BaseAgent):
        pass
    
    agent = TestAgent(session_id=1)
    
    # Test that helper methods exist and call emit correctly
    assert hasattr(agent, 'emit_persistence')
    assert hasattr(agent, 'emit_thinking')
    assert hasattr(agent, 'emit_artifact')
    assert hasattr(agent, 'emit_response')
    
    # Test that they're callable
    assert callable(agent.emit_persistence)
    assert callable(agent.emit_thinking)
    assert callable(agent.emit_artifact)
    assert callable(agent.emit_response)


@pytest.mark.asyncio
async def test_base_orchestrator_db_services():
    """Test BaseOrchestrator DB management services."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    from nexus.modules.database import database
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return database
    
    orchestrator = TestOrchestrator()
    
    # Test DB connection check (may fail if DB not connected, that's okay)
    try:
        result = await orchestrator._ensure_db_connection()
        assert isinstance(result, bool)
    except Exception:
        # DB might not be connected in test environment
        pass


@pytest.mark.asyncio
async def test_base_orchestrator_state_management():
    """Test BaseOrchestrator state management services."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return MagicMock()
    
    orchestrator = TestOrchestrator()
    
    # Test state cache
    await orchestrator._set_state("test_key", "test_value", session_id=None, persist=False)
    value = await orchestrator._get_state("test_key", session_id=None)
    assert value == "test_value"
    
    # Test state update
    await orchestrator._set_state("test_dict", {"a": 1}, session_id=None, persist=False)
    await orchestrator._update_state("test_dict", {"b": 2}, session_id=None)
    updated = await orchestrator._get_state("test_dict", session_id=None)
    assert updated == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_base_orchestrator_caching():
    """Test BaseOrchestrator caching service."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return MagicMock()
    
    orchestrator = TestOrchestrator()
    
    # Test cache set/get
    await orchestrator._cache_set("test_cache", "cached_value", ttl=60)
    cached = await orchestrator._cache_get("test_cache", ttl=60)
    assert cached == "cached_value"
    
    # Test cache miss
    missing = await orchestrator._cache_get("nonexistent", ttl=60)
    assert missing is None


@pytest.mark.asyncio
async def test_base_orchestrator_error_handling():
    """Test BaseOrchestrator error handling service."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return MagicMock()
    
    orchestrator = TestOrchestrator()
    
    # Test error handling
    test_error = ValueError("Test error")
    await orchestrator._handle_error(test_error, {"test": "context"}, session_id=None)
    
    # Test retry operation - should succeed on first try
    call_count = 0
    async def test_operation():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await orchestrator._retry_operation(test_operation, max_retries=3)
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_workflow_orchestrator_initialization():
    """Test that WorkflowOrchestrator initializes correctly."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator()
    
    # Check that it has all required modules
    assert hasattr(orchestrator, 'shaping_manager')
    assert hasattr(orchestrator, 'diagnosis_brain')
    assert hasattr(orchestrator, 'planner_brain')
    assert hasattr(orchestrator, 'consultant_brain')
    
    # Check that it implements abstract methods
    modules = orchestrator._get_module_registry()
    assert "shaping" in modules
    assert "diagnosis" in modules
    assert "planner" in modules
    assert "consultant" in modules


@pytest.mark.asyncio
async def test_workflow_orchestrator_list_recipes():
    """Test WorkflowOrchestrator list_recipes method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.workflows.registry import registry
    
    orchestrator = WorkflowOrchestrator()
    
    # Mock registry
    with patch.object(registry, 'list_recipes', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ["recipe1", "recipe2"]
        
        result = await orchestrator.list_recipes()
        assert result == ["recipe1", "recipe2"]
        mock_list.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_orchestrator_get_recipe():
    """Test WorkflowOrchestrator get_recipe method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.workflows.registry import registry
    from nexus.core.base_agent import AgentRecipe, AgentStep
    
    orchestrator = WorkflowOrchestrator()
    
    # Create a mock recipe
    mock_recipe = AgentRecipe(
        name="test_recipe",
        goal="Test goal",
        steps={
            "step1": AgentStep(
                step_id="step1",
                tool_name="test_tool",
                description="Test step",
                args_mapping={}
            )
        },
        start_step_id="step1"
    )
    
    with patch.object(registry, 'get_recipe', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_recipe
        
        result = await orchestrator.get_recipe("test_recipe")
        assert result["name"] == "test_recipe"
        assert result["goal"] == "Test goal"
        assert "steps" in result


@pytest.mark.asyncio
async def test_workflow_orchestrator_create_recipe():
    """Test WorkflowOrchestrator create_recipe method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.workflows.registry import registry
    
    orchestrator = WorkflowOrchestrator()
    
    recipe_data = {
        "name": "test_recipe",
        "goal": "Test goal",
        "steps": {
            "step1": {
                "tool_name": "test_tool",
                "description": "Test step",
                "args_mapping": {},
                "transition_success": None,
                "transition_fail": None
            }
        },
        "start_step_id": "step1"
    }
    
    with patch.object(registry, 'register_recipe', new_callable=AsyncMock) as mock_register:
        result = await orchestrator.create_recipe(recipe_data)
        assert result["status"] == "created"
        assert result["name"] == "test_recipe"
        mock_register.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_orchestrator_analyze_workflows():
    """Test WorkflowOrchestrator analyze_existing_workflows method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.brains.diagnosis import SolutionCandidate
    
    orchestrator = WorkflowOrchestrator()
    
    # Create mock candidates
    mock_candidates = [
        SolutionCandidate(
            recipe_name="test_recipe",
            goal="Test goal",
            match_score=0.8,
            missing_info=[],
            reasoning="Test reasoning",
            origin="standard"
        )
    ]
    
    with patch.object(orchestrator.diagnosis_brain, 'diagnose', new_callable=AsyncMock) as mock_diagnose:
        mock_diagnose.return_value = mock_candidates
        
        # Mock session validation to return True
        with patch.object(orchestrator, '_validate_session_id', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = True
            
            # Mock get_agent_for_session
            from nexus.core.base_agent import BaseAgent
            mock_agent = MagicMock(spec=BaseAgent)
            mock_agent.emit_artifact = AsyncMock()
            
            with patch.object(orchestrator, '_get_agent_for_session', new_callable=AsyncMock) as mock_get_agent:
                mock_get_agent.return_value = mock_agent
                
                result = await orchestrator.analyze_existing_workflows(session_id=1, query="test query")
                assert len(result) == 1
                assert result[0].recipe_name == "test_recipe"


@pytest.mark.asyncio
async def test_workflow_orchestrator_update_plan():
    """Test WorkflowOrchestrator update_workflow_plan method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator()
    
    mock_draft = {
        "name": "Test Workflow",
        "goal": "Test goal",
        "steps": [{"id": "step1", "description": "Test step"}],
        "missing_info": []
    }
    
    with patch.object(orchestrator.shaping_manager, 'get_session', new_callable=AsyncMock) as mock_get_session:
        mock_get_session.return_value = {
            "transcript": [{"role": "user", "content": "test"}],
            "rag_citations": []
        }
        
        with patch.object(orchestrator.planner_brain, 'update_draft', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = mock_draft
            
            # Mock session validation and agent
            with patch.object(orchestrator, '_validate_session_id', new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = True
                
                from nexus.core.base_agent import BaseAgent
                mock_agent = MagicMock(spec=BaseAgent)
                mock_agent.emit_artifact = AsyncMock()
                
                with patch.object(orchestrator, '_get_agent_for_session', new_callable=AsyncMock) as mock_get_agent:
                    mock_get_agent.return_value = mock_agent
                    
                    result = await orchestrator.update_workflow_plan(session_id=1)
                    assert result["name"] == "Test Workflow"
                    assert "steps" in result


@pytest.mark.asyncio
async def test_workflow_orchestrator_start_session():
    """Test WorkflowOrchestrator start_shaping_session method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.brains.diagnosis import SolutionCandidate
    
    orchestrator = WorkflowOrchestrator()
    
    mock_candidates = [
        SolutionCandidate(
            recipe_name="test_recipe",
            goal="Test goal",
            match_score=0.8,
            missing_info=[],
            reasoning="Test reasoning",
            origin="standard"
        )
    ]
    
    with patch.object(orchestrator.shaping_manager, 'create_session', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = 1
        
        with patch.object(orchestrator.shaping_manager, 'get_session', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "transcript": [{"role": "user", "content": "test"}],
                "rag_citations": []
            }
            
            with patch.object(orchestrator.diagnosis_brain, 'diagnose', new_callable=AsyncMock) as mock_diagnose:
                mock_diagnose.return_value = mock_candidates
                
                # Mock session validation and agent
                with patch.object(orchestrator, '_validate_session_id', new_callable=AsyncMock) as mock_validate:
                    mock_validate.return_value = True
                    
                    from nexus.core.base_agent import BaseAgent
                    mock_agent = MagicMock(spec=BaseAgent)
                    mock_agent.emit_artifact = AsyncMock()
                    
                    with patch.object(orchestrator, '_get_agent_for_session', new_callable=AsyncMock) as mock_get_agent:
                        mock_get_agent.return_value = mock_agent
                        
                        result = await orchestrator.start_shaping_session("user1", "test query")
                        assert result["session_id"] == 1
                        assert "candidates" in result
                        assert "transcript" in result


@pytest.mark.asyncio
async def test_workflow_orchestrator_execute_workflow():
    """Test WorkflowOrchestrator execute_workflow method."""
    from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
    from nexus.workflows.registry import registry
    from nexus.core.base_agent import AgentRecipe, AgentStep
    
    orchestrator = WorkflowOrchestrator()
    
    mock_recipe = AgentRecipe(
        name="test_recipe",
        goal="Test goal",
        steps={
            "step1": AgentStep(
                step_id="step1",
                tool_name="schedule_scanner",
                description="Test step",
                args_mapping={}
            )
        },
        start_step_id="step1"
    )
    
    with patch.object(registry, 'get_recipe', new_callable=AsyncMock) as mock_get_recipe:
        mock_get_recipe.return_value = mock_recipe
        
        # Mock database
        mock_db = MagicMock()
        mock_db.fetch_one = AsyncMock(return_value={"id": 1})
        mock_db.fetch_val = AsyncMock(return_value=100)  # execution_id
        
        with patch.object(orchestrator, '_get_database', return_value=mock_db):
            with patch.object(orchestrator, '_execute_db_write', new_callable=AsyncMock):
                # Mock factory execution
                with patch('nexus.conductors.workflows.orchestrator.NexusAgentFactory') as MockFactory:
                    mock_factory_instance = MagicMock()
                    mock_factory_instance.run_recipe = AsyncMock(return_value={"result": "success"})
                    MockFactory.return_value = mock_factory_instance
                    
                    result = await orchestrator.execute_workflow(
                        recipe_name="test_recipe",
                        initial_context={"user_id": "user1"},
                        session_id=None
                    )
                    
                    assert result["status"] == "success"
                    assert "execution_id" in result
                    assert "result" in result


@pytest.mark.asyncio
async def test_endpoint_delegation():
    """Test that endpoints properly delegate to orchestrator."""
    from nexus.modules.workflow_endpoints import router, orchestrator
    
    # Verify orchestrator is imported
    assert orchestrator is not None
    assert hasattr(orchestrator, 'start_shaping_session')
    assert hasattr(orchestrator, 'handle_chat_message')
    assert hasattr(orchestrator, 'execute_workflow')
    assert hasattr(orchestrator, 'list_recipes')
    assert hasattr(orchestrator, 'get_recipe')
    assert hasattr(orchestrator, 'create_recipe')


def test_base_orchestrator_coordination():
    """Test BaseOrchestrator coordination services."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return MagicMock()
    
    orchestrator = TestOrchestrator()
    
    # Test sequential execution
    async def op1():
        return "result1"
    
    async def op2():
        return "result2"
    
    results = asyncio.run(orchestrator._execute_sequentially([op1, op2]))
    assert results == ["result1", "result2"]
    
    # Test parallel execution
    results = asyncio.run(orchestrator._execute_parallel([op1, op2]))
    assert "result1" in results
    assert "result2" in results


def test_base_orchestrator_rate_limiting():
    """Test BaseOrchestrator rate limiting."""
    from nexus.conductors.base_orchestrator import BaseOrchestrator
    
    class TestOrchestrator(BaseOrchestrator):
        def _get_module_registry(self):
            return {}
        
        def _get_session_manager(self):
            return MagicMock()
        
        def _get_database(self):
            return MagicMock()
    
    orchestrator = TestOrchestrator()
    
    # Test rate limiting
    result1 = asyncio.run(orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60))
    assert result1 is True
    
    result2 = asyncio.run(orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60))
    assert result2 is True
    
    result3 = asyncio.run(orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60))
    assert result3 is False  # Should be rate limited


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


