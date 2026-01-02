"""
Integration tests for Workflow Orchestrator.
Tests the full flow with mocked dependencies.
"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_start_shaping_session_flow():
    """Test the full start_shaping_session flow."""
    print("Testing start_shaping_session integration...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        from nexus.brains.diagnosis import SolutionCandidate
        
        orchestrator = WorkflowOrchestrator()
        
        # Mock dependencies
        mock_session_id = 123
        mock_candidates = [
            SolutionCandidate(
                recipe_name="test_recipe",
                goal="Test goal",
                match_score=0.85,
                missing_info=["param1"],
                reasoning="Good match",
                origin="standard"
            )
        ]
        
        mock_session_data = {
            "id": mock_session_id,
            "user_id": "user1",
            "transcript": [{"role": "user", "content": "test query"}],
            "rag_citations": []
        }
        
        with patch.object(orchestrator.shaping_manager, 'create_session', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_session_id
            
            with patch.object(orchestrator.shaping_manager, 'get_session', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_session_data
                
                with patch.object(orchestrator.diagnosis_brain, 'diagnose', new_callable=AsyncMock) as mock_diagnose:
                    mock_diagnose.return_value = mock_candidates
                    
                    with patch.object(orchestrator, '_set_state', new_callable=AsyncMock):
                        with patch.object(orchestrator, '_validate_session_id', new_callable=AsyncMock) as mock_validate:
                            mock_validate.return_value = True
                            
                            from nexus.core.base_agent import BaseAgent
                            mock_agent = MagicMock(spec=BaseAgent)
                            mock_agent.emit_artifact = AsyncMock()
                            
                            with patch.object(orchestrator, '_get_agent_for_session', new_callable=AsyncMock) as mock_get_agent:
                                mock_get_agent.return_value = mock_agent
                                
                                result = await orchestrator.start_shaping_session("user1", "test query")
                                
                                assert result["session_id"] == mock_session_id
                                assert len(result["candidates"]) == 1
                                assert result["candidates"][0]["recipe_name"] == "test_recipe"
                                assert "transcript" in result
                                
                                # Verify methods were called
                                mock_create.assert_called_once_with("user1", "test query")
                                mock_diagnose.assert_called_once_with("test query")
                                
                                print("✅ start_shaping_session integration: PASS")
                                return True
    except Exception as e:
        print(f"❌ start_shaping_session integration: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_handle_chat_message_flow():
    """Test the full handle_chat_message flow."""
    print("Testing handle_chat_message integration...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        mock_session_id = 123
        mock_transcript = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "Hi there", "trace_id": "trace123"}
        ]
        
        mock_session = {
            "id": mock_session_id,
            "transcript": mock_transcript,
            "rag_citations": []
        }
        
        with patch.object(orchestrator.shaping_manager, 'append_message', new_callable=AsyncMock):
            with patch.object(orchestrator.shaping_manager, 'get_session', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_session
                
                with patch.object(orchestrator, '_trigger_workflow_analysis', new_callable=AsyncMock):
                    with patch.object(orchestrator, '_trigger_planner_update', new_callable=AsyncMock):
                        
                        result = await orchestrator.handle_chat_message(
                            session_id=mock_session_id,
                            message="Hello",
                            user_id="user1"
                        )
                        
                        assert "reply" in result
                        assert result["reply"] == "Hi there"
                        assert result.get("trace_id") == "trace123"
                        
                        print("✅ handle_chat_message integration: PASS")
                        return True
    except Exception as e:
        print(f"❌ handle_chat_message integration: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_execute_workflow_flow():
    """Test the full execute_workflow flow."""
    print("Testing execute_workflow integration...")
    try:
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
        
        mock_execution_id = 456
        
        with patch.object(registry, 'get_recipe', new_callable=AsyncMock) as mock_get_recipe:
            mock_get_recipe.return_value = mock_recipe
            
            # Mock database
            mock_db = MagicMock()
            mock_db.fetch_one = AsyncMock(return_value={"id": 1})
            mock_db.fetch_val = AsyncMock(return_value=mock_execution_id)
            
            with patch.object(orchestrator, '_get_database', return_value=mock_db):
                with patch.object(orchestrator, '_execute_db_write', new_callable=AsyncMock):
                    # Mock factory
                    with patch('nexus.conductors.workflows.orchestrator.NexusAgentFactory') as MockFactory:
                        mock_factory_instance = MagicMock()
                        mock_factory_instance.run_recipe = AsyncMock(return_value={"result": "success", "data": "test"})
                        MockFactory.return_value = mock_factory_instance
                        
                        result = await orchestrator.execute_workflow(
                            recipe_name="test_recipe",
                            initial_context={"user_id": "user1"},
                            session_id=None
                        )
                        
                        assert result["status"] == "success"
                        assert result["execution_id"] == mock_execution_id
                        assert "result" in result
                        assert "duration_ms" in result
                        
                        print("✅ execute_workflow integration: PASS")
                        return True
    except Exception as e:
        print(f"❌ execute_workflow integration: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analyze_workflows_with_caching():
    """Test that workflow analysis uses caching."""
    print("Testing analyze_workflows with caching...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        from nexus.brains.diagnosis import SolutionCandidate
        
        orchestrator = WorkflowOrchestrator()
        
        mock_candidates = [
            SolutionCandidate(
                recipe_name="cached_recipe",
                goal="Cached goal",
                match_score=0.9,
                missing_info=[],
                reasoning="Cached",
                origin="standard"
            )
        ]
        
        # First call - should call diagnose
        with patch.object(orchestrator.diagnosis_brain, 'diagnose', new_callable=AsyncMock) as mock_diagnose:
            mock_diagnose.return_value = mock_candidates
            
            with patch.object(orchestrator, '_validate_session_id', new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = True
                
                from nexus.core.base_agent import BaseAgent
                mock_agent = MagicMock(spec=BaseAgent)
                mock_agent.emit_artifact = AsyncMock()
                
                with patch.object(orchestrator, '_get_agent_for_session', new_callable=AsyncMock) as mock_get_agent:
                    mock_get_agent.return_value = mock_agent
                    
                    result1 = await orchestrator.analyze_existing_workflows(1, "test query")
                    assert len(result1) == 1
                    assert mock_diagnose.call_count == 1
                    
                    # Second call with same query - should use cache
                    result2 = await orchestrator.analyze_existing_workflows(1, "test query")
                    assert len(result2) == 1
                    # Should still be 1 call (cached)
                    assert mock_diagnose.call_count == 1
                    
                    print("✅ analyze_workflows caching: PASS")
                    return True
    except Exception as e:
        print(f"❌ analyze_workflows caching: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """Test that orchestrator handles errors gracefully."""
    print("Testing error handling...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        # Test that errors are caught and handled
        with patch.object(orchestrator.shaping_manager, 'create_session', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError("Test error")
            
            with patch.object(orchestrator, '_handle_error', new_callable=AsyncMock) as mock_handle:
                try:
                    await orchestrator.start_shaping_session("user1", "test")
                    assert False, "Should have raised an exception"
                except ValueError:
                    # Error should be handled
                    mock_handle.assert_called()
                    print("✅ Error handling: PASS")
                    return True
    except Exception as e:
        print(f"❌ Error handling: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Orchestrator Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_start_shaping_session_flow,
        test_handle_chat_message_flow,
        test_execute_workflow_flow,
        test_analyze_workflows_with_caching,
        test_error_handling,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
            print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("✅ All integration tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_integration_tests())
    sys.exit(exit_code)


