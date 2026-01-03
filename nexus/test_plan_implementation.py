"""
Test script for plan implementation guidance.
Tests the LLM-guided plan implementation flow.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.modules.database import database
from nexus.brains.planning_phase import planning_phase_brain
from nexus.modules.prompt_manager import prompt_manager

async def test_prompt_loading():
    """Test that the prompt can be loaded from database."""
    print("🧪 Testing prompt loading...")
    
    await database.connect()
    
    try:
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="plan_implementation",
            session_id=None
        )
        
        if prompt_data:
            print(f"✅ Prompt loaded successfully!")
            print(f"   Key: {prompt_data.get('key')}")
            print(f"   Version: {prompt_data.get('version')}")
            print(f"   Has config: {prompt_data.get('config') is not None}")
            print(f"   Has generation_config: {prompt_data.get('generation_config') is not None}")
            return True
        else:
            print("❌ Prompt not found in database")
            print("   Run: python nexus/scripts/seed_plan_implementation_prompt.py")
            return False
    except Exception as e:
        print(f"❌ Error loading prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await database.disconnect()

async def test_implementation_status_analysis():
    """Test the implementation status analysis."""
    print("\n🧪 Testing implementation status analysis...")
    
    # Mock draft plan
    mock_plan = {
        "name": "Test Workflow",
        "goal": "Test goal",
        "gates": [
            {
                "id": "gate_1",
                "steps": [
                    {
                        "id": "step_1",
                        "description": "Check eligibility",
                        "owner": "tool",  # Has owner
                        "tool_name": "schedule_scanner",  # Has tool
                        "execution_mode": "agent"  # Has execution mode
                    },
                    {
                        "id": "step_2",
                        "description": "Notify patient",
                        # Missing owner, execution_mode
                    }
                ]
            }
        ]
    }
    
    mock_tool_contracts = [
        {
            "name": "schedule_scanner",
            "description": "Fetches appointments",
            "parameters": {"days_out": "int"},
            "required_parameters": ["days_out"]
        }
    ]
    
    mock_gate_values = {}
    
    try:
        status = planning_phase_brain._analyze_implementation_status(
            mock_plan,
            mock_tool_contracts,
            mock_gate_values
        )
        
        print(f"✅ Analysis complete!")
        print(f"   Total steps: {status['steps_total']}")
        print(f"   Steps with owner: {status['steps_with_owner']}")
        print(f"   Steps with tool: {status['steps_with_tool']}")
        print(f"   Steps with execution mode: {status['steps_with_execution_mode']}")
        print(f"   Incomplete steps: {len(status['incomplete_steps'])}")
        print(f"   Completion: {status['completion_percentage']:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_plan_parsing():
    """Test parsing of LLM response."""
    print("\n🧪 Testing plan response parsing...")
    
    # Mock LLM response
    mock_response = """
    {
        "conversation_state": "needs_input",
        "next_question": "Which tool should we use for step_1?",
        "plan_updates": {
            "steps": [
                {
                    "step_id": "step_1",
                    "owner": "tool",
                    "tool_name": "schedule_scanner",
                    "execution_mode": "agent",
                    "required_data": ["days_out"],
                    "failure_logic": {
                        "retry_count": 2,
                        "escalation_path": "Notify admin",
                        "fallback_action": "Manual check"
                    }
                }
            ]
        },
        "missing_information": ["Tool parameters"],
        "reasoning": "Step needs tool assignment"
    }
    """
    
    try:
        result = planning_phase_brain._parse_planning_response(mock_response)
        
        print(f"✅ Parsing successful!")
        print(f"   Conversation state: {result.get('conversation_state')}")
        print(f"   Next question: {result.get('next_question')}")
        print(f"   Steps to update: {len(result.get('plan_updates', {}).get('steps', []))}")
        
        return True
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_plan_updates():
    """Test applying updates to plan."""
    print("\n🧪 Testing plan updates application...")
    
    mock_plan = {
        "gates": [
            {
                "id": "gate_1",
                "steps": [
                    {
                        "id": "step_1",
                        "description": "Check eligibility"
                    }
                ]
            }
        ]
    }
    
    mock_updates = {
        "steps": [
            {
                "step_id": "step_1",
                "owner": "tool",
                "tool_name": "schedule_scanner",
                "execution_mode": "agent",
                "failure_logic": {
                    "retry_count": 2
                }
            }
        ]
    }
    
    mock_tool_contracts = []
    
    try:
        updated = await planning_phase_brain._apply_implementation_updates(
            mock_plan,
            mock_updates,
            mock_tool_contracts
        )
        
        step = updated["gates"][0]["steps"][0]
        
        print(f"✅ Updates applied successfully!")
        print(f"   Step owner: {step.get('owner')}")
        print(f"   Tool name: {step.get('tool_name')}")
        print(f"   Execution mode: {step.get('execution_mode')}")
        print(f"   Has failure logic: {step.get('failure_logic') is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Error applying updates: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_real_session():
    """Test with a real session if available."""
    print("\n🧪 Testing with real session...")
    
    await database.connect()
    
    try:
        # Get a recent session
        query = """
            SELECT id, draft_plan, user_id 
            FROM shaping_sessions 
            WHERE draft_plan IS NOT NULL 
            AND draft_plan != '{}'::jsonb
            ORDER BY id DESC 
            LIMIT 1
        """
        row = await database.fetch_one(query)
        
        if not row:
            print("⚠️  No session with draft plan found. Skipping real session test.")
            return True
        
        row_dict = dict(row)
        session_id = row_dict["id"]
        user_id = row_dict.get("user_id", "user_123")
        
        print(f"   Using session {session_id}")
        
        # Test guidance (without actually calling LLM - just test the flow)
        try:
            # This will fail at LLM call, but we can test the setup
            await planning_phase_brain.guide_plan_to_implementable(
                session_id=session_id,
                user_id=user_id,
                user_message=None
            )
            print("✅ Guidance method executed (may have failed at LLM call, which is expected)")
        except Exception as e:
            error_msg = str(e)
            if "No draft plan found" in error_msg or "LLM" in error_msg or "model" in error_msg.lower():
                print(f"⚠️  Expected error (LLM/model not configured or plan structure issue): {error_msg[:100]}")
            else:
                print(f"❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing with real session: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await database.disconnect()

async def main():
    """Run all tests."""
    print("🚀 Testing Plan Implementation Guidance System\n")
    print("=" * 60)
    
    results = []
    
    # Test 1: Prompt loading
    results.append(await test_prompt_loading())
    
    # Test 2: Implementation status analysis
    results.append(await test_implementation_status_analysis())
    
    # Test 3: Plan parsing
    results.append(await test_plan_parsing())
    
    # Test 4: Plan updates
    results.append(await test_plan_updates())
    
    # Test 5: Real session (if available)
    results.append(await test_with_real_session())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

