"""
Simple unit tests for Workflow Orchestrator implementation.
Runs without pytest dependencies.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_base_agent_emission_helpers():
    """Test that BaseAgent emission helper methods exist."""
    print("Testing BaseAgent emission helpers...")
    try:
        from nexus.core.base_agent import BaseAgent
        
        class TestAgent(BaseAgent):
            pass
        
        agent = TestAgent(session_id=1)
        
        # Check methods exist
        assert hasattr(agent, 'emit_persistence'), "emit_persistence missing"
        assert hasattr(agent, 'emit_thinking'), "emit_thinking missing"
        assert hasattr(agent, 'emit_artifact'), "emit_artifact missing"
        assert hasattr(agent, 'emit_response'), "emit_response missing"
        
        print("✅ BaseAgent emission helpers: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseAgent emission helpers: FAIL - {e}")
        return False


async def test_base_orchestrator_initialization():
    """Test BaseOrchestrator can be instantiated."""
    print("Testing BaseOrchestrator initialization...")
    try:
        from nexus.conductors.base_orchestrator import BaseOrchestrator
        
        class TestOrchestrator(BaseOrchestrator):
            def _get_module_registry(self):
                return {}
            
            def _get_session_manager(self):
                return None
            
            def _get_database(self):
                return None
        
        orchestrator = TestOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, '_state_cache')
        assert hasattr(orchestrator, '_resource_registry')
        
        print("✅ BaseOrchestrator initialization: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseOrchestrator initialization: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_base_orchestrator_state_management():
    """Test BaseOrchestrator state management."""
    print("Testing BaseOrchestrator state management...")
    try:
        from nexus.conductors.base_orchestrator import BaseOrchestrator
        
        class TestOrchestrator(BaseOrchestrator):
            def _get_module_registry(self):
                return {}
            
            def _get_session_manager(self):
                return None
            
            def _get_database(self):
                return None
        
        orchestrator = TestOrchestrator()
        
        # Test state cache
        await orchestrator._set_state("test_key", "test_value", session_id=None, persist=False)
        value = await orchestrator._get_state("test_key", session_id=None)
        assert value == "test_value", f"Expected 'test_value', got {value}"
        
        # Test state update
        await orchestrator._set_state("test_dict", {"a": 1}, session_id=None, persist=False)
        await orchestrator._update_state("test_dict", {"b": 2}, session_id=None)
        updated = await orchestrator._get_state("test_dict", session_id=None)
        assert updated == {"a": 1, "b": 2}, f"Expected {{'a': 1, 'b': 2}}, got {updated}"
        
        print("✅ BaseOrchestrator state management: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseOrchestrator state management: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_base_orchestrator_caching():
    """Test BaseOrchestrator caching."""
    print("Testing BaseOrchestrator caching...")
    try:
        from nexus.conductors.base_orchestrator import BaseOrchestrator
        
        class TestOrchestrator(BaseOrchestrator):
            def _get_module_registry(self):
                return {}
            
            def _get_session_manager(self):
                return None
            
            def _get_database(self):
                return None
        
        orchestrator = TestOrchestrator()
        
        # Test cache set/get
        await orchestrator._cache_set("test_cache", "cached_value", ttl=60)
        cached = await orchestrator._cache_get("test_cache", ttl=60)
        assert cached == "cached_value", f"Expected 'cached_value', got {cached}"
        
        # Test cache miss
        missing = await orchestrator._cache_get("nonexistent", ttl=60)
        assert missing is None, f"Expected None, got {missing}"
        
        print("✅ BaseOrchestrator caching: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseOrchestrator caching: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_orchestrator_initialization():
    """Test WorkflowOrchestrator initialization."""
    print("Testing WorkflowOrchestrator initialization...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        # Check modules
        assert hasattr(orchestrator, 'shaping_manager'), "shaping_manager missing"
        assert hasattr(orchestrator, 'diagnosis_brain'), "diagnosis_brain missing"
        assert hasattr(orchestrator, 'planner_brain'), "planner_brain missing"
        assert hasattr(orchestrator, 'consultant_brain'), "consultant_brain missing"
        
        # Check abstract methods implemented
        modules = orchestrator._get_module_registry()
        assert "shaping" in modules, "shaping module missing"
        assert "diagnosis" in modules, "diagnosis module missing"
        assert "planner" in modules, "planner module missing"
        assert "consultant" in modules, "consultant module missing"
        
        print("✅ WorkflowOrchestrator initialization: PASS")
        return True
    except Exception as e:
        print(f"❌ WorkflowOrchestrator initialization: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_orchestrator_methods_exist():
    """Test that WorkflowOrchestrator has all required methods."""
    print("Testing WorkflowOrchestrator methods...")
    try:
        from nexus.conductors.workflows.orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        # Check public API methods
        required_methods = [
            'start_shaping_session',
            'get_session_state',
            'handle_chat_message',
            'analyze_existing_workflows',
            'update_workflow_plan',
            'execute_workflow',
            'create_recipe',
            'get_recipe',
            'list_recipes'
        ]
        
        for method in required_methods:
            assert hasattr(orchestrator, method), f"Method {method} missing"
            assert callable(getattr(orchestrator, method)), f"Method {method} not callable"
        
        print("✅ WorkflowOrchestrator methods: PASS")
        return True
    except Exception as e:
        print(f"❌ WorkflowOrchestrator methods: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_endpoint_imports():
    """Test that endpoints can import orchestrator."""
    print("Testing endpoint imports...")
    try:
        from nexus.modules.workflow_endpoints import orchestrator, router
        
        assert orchestrator is not None, "Orchestrator not imported"
        assert router is not None, "Router not imported"
        
        # Check orchestrator has required methods
        assert hasattr(orchestrator, 'start_shaping_session'), "start_shaping_session missing"
        assert hasattr(orchestrator, 'handle_chat_message'), "handle_chat_message missing"
        
        print("✅ Endpoint imports: PASS")
        return True
    except Exception as e:
        print(f"❌ Endpoint imports: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_base_orchestrator_coordination():
    """Test BaseOrchestrator coordination services."""
    print("Testing BaseOrchestrator coordination...")
    try:
        from nexus.conductors.base_orchestrator import BaseOrchestrator
        
        class TestOrchestrator(BaseOrchestrator):
            def _get_module_registry(self):
                return {}
            
            def _get_session_manager(self):
                return None
            
            def _get_database(self):
                return None
        
        orchestrator = TestOrchestrator()
        
        # Test sequential execution
        async def op1():
            return "result1"
        
        async def op2():
            return "result2"
        
        results = await orchestrator._execute_sequentially([op1, op2])
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert results[0] == "result1", f"Expected 'result1', got {results[0]}"
        assert results[1] == "result2", f"Expected 'result2', got {results[1]}"
        
        # Test parallel execution
        results = await orchestrator._execute_parallel([op1, op2])
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert "result1" in results, "result1 not in parallel results"
        assert "result2" in results, "result2 not in parallel results"
        
        print("✅ BaseOrchestrator coordination: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseOrchestrator coordination: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_base_orchestrator_rate_limiting():
    """Test BaseOrchestrator rate limiting."""
    print("Testing BaseOrchestrator rate limiting...")
    try:
        from nexus.conductors.base_orchestrator import BaseOrchestrator
        import time
        
        class TestOrchestrator(BaseOrchestrator):
            def _get_module_registry(self):
                return {}
            
            def _get_session_manager(self):
                return None
            
            def _get_database(self):
                return None
        
        orchestrator = TestOrchestrator()
        
        # Test rate limiting
        result1 = await orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60)
        assert result1 is True, "First request should be allowed"
        
        result2 = await orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60)
        assert result2 is True, "Second request should be allowed"
        
        result3 = await orchestrator._rate_limit("test_key", max_requests=2, window_seconds=60)
        assert result3 is False, "Third request should be rate limited"
        
        print("✅ BaseOrchestrator rate limiting: PASS")
        return True
    except Exception as e:
        print(f"❌ BaseOrchestrator rate limiting: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Orchestrator Unit Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_base_agent_emission_helpers,
        test_base_orchestrator_initialization,
        test_base_orchestrator_state_management,
        test_base_orchestrator_caching,
        test_workflow_orchestrator_initialization,
        test_workflow_orchestrator_methods_exist,
        test_endpoint_imports,
        test_base_orchestrator_coordination,
        test_base_orchestrator_rate_limiting,
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
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)



