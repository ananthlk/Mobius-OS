#!/usr/bin/env python3
"""
Test the gate engine flow with: "can i check medicaid eligibility for this patient"
"""

import asyncio
import logging
import sys
import os

# Ensure we can import nexus
sys.path.append(os.getcwd())

from nexus.modules.shaping_manager import shaping_manager
from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

# Configure logging to stdout
root = logging.getLogger()
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s :: %(message)s"))
root.addHandler(handler)

async def test_query():
    query = "can i check medicaid eligibility for this patient"
    user_id = "test_user"
    
    print("=" * 80)
    print("TESTING GATE ENGINE FLOW")
    print("=" * 80)
    print(f"Query: {query}")
    print(f"User ID: {user_id}")
    print()
    
    try:
        # Connect to database
        print("[1] Connecting to database...")
        await database.connect()
        print("    ✓ Connected")
        print()
        
        # Check if prompt exists
        print("[2] Checking for prompt: workflow:eligibility:TABULA_RASA:gate")
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="gate"
        )
        
        if not prompt_data:
            print("    ✗ Prompt NOT FOUND!")
            print("    Expected key: workflow:eligibility:TABULA_RASA:gate")
            print()
            print("    This means the prompt has not been seeded into the database.")
            print("    The system will raise ValueError when trying to create session.")
            print()
            return
        
        print(f"    ✓ Prompt found (version: {prompt_data.get('version', 'unknown')})")
        config = prompt_data.get("config", {})
        
        # Check for GATE_ORDER
        if "GATE_ORDER" not in config:
            print("    ✗ Prompt does NOT have GATE_ORDER!")
            print("    This prompt is not configured for gates.")
            print("    The system will raise ValueError.")
            return
        
        gate_order = config.get("GATE_ORDER", [])
        gates = config.get("GATES", {})
        print(f"    ✓ Gate order: {gate_order}")
        print(f"    ✓ Number of gates: {len(gates)}")
        for gate_key, gate_def in gates.items():
            print(f"      - {gate_key}: {gate_def.get('question', 'N/A')[:60]}...")
        print()
        
        # Try to create session
        print("[3] Creating shaping session...")
        try:
            session_id = await shaping_manager.create_session(user_id, query)
            print(f"    ✓ Session created: {session_id}")
            print()
            
            # Get session data
            print("[4] Retrieving session data...")
            session = await shaping_manager.get_session(session_id)
            
            # Check gate_state
            gate_state = session.get("gate_state")
            if gate_state:
                if isinstance(gate_state, str):
                    import json
                    gate_state = json.loads(gate_state)
                
                print("    ✓ Gate state found in session:")
                print(f"      Summary: {gate_state.get('summary', 'N/A')}")
                gates_data = gate_state.get('gates', {})
                print(f"      Gates: {list(gates_data.keys())}")
                for gate_key, gate_value in gates_data.items():
                    raw = gate_value.get('raw', 'N/A')
                    classified = gate_value.get('classified', 'N/A')
                    print(f"        - {gate_key}:")
                    print(f"          raw: {raw[:50] if raw else 'None'}...")
                    print(f"          classified: {classified}")
                
                status = gate_state.get('status', {})
                print(f"      Status.pass: {status.get('pass', False)}")
                print(f"      Status.next_gate: {status.get('next_gate', 'N/A')}")
                print(f"      Status.next_query: {status.get('next_query', 'N/A')}")
            else:
                print("    ✗ No gate_state found in session")
            
            # Check transcript
            transcript = session.get("transcript", [])
            if isinstance(transcript, str):
                import json
                transcript = json.loads(transcript)
            
            print()
            print("    Transcript:")
            for msg in transcript:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if len(content) > 100:
                    content = content[:100] + "..."
                print(f"      [{role}]: {content}")
            
        except ValueError as e:
            print(f"    ✗ ValueError: {e}")
            print("    This is expected if prompt is not found or not configured for gates.")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print("[5] Disconnecting from database...")
        await database.disconnect()
        print("    ✓ Disconnected")
        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_query())


