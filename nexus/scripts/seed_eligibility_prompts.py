"""
Seed eligibility workflow prompts into prompt_templates table.

This script seeds the LLM prompts needed for the structured eligibility workflow:
- insurance_tool_selection: LLM-guided tool selection for insurance resolution
- insurance_multi_step_planning: LLM-guided multi-step tool chain planning
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager


async def seed_insurance_tool_selection_prompt():
    """Seed the Insurance Tool Selection prompt."""
    
    prompt_config = {
        "ROLE": """You are a tool selection expert for healthcare insurance information retrieval. Your task is to analyze available tools and select the best ones to resolve insurance information (insurance_id and insurance_name) based on the provided patient information.""",
        
        "CONTEXT": """You receive:
- Patient Information: {FORM_DATA} (name, DOB, MRN, insurance_name, insurance_id)
- Available Tools: {TOOL_SCHEMAS} (list of tool schemas with descriptions and parameters)
- Priority: {PRIORITY} (internal = only internal systems, external = only external systems, any = all tools)

Priority Levels:
1. **internal**: Tools that access internal systems (EMR, user_profiles, internal databases)
2. **external**: Tools that access external systems (HIE, previous providers, external databases)
3. **any**: Consider all available tools""",
        
        "ANALYSIS": """Tool Selection Criteria:
- Match tool capabilities to the available patient information (name, DOB, MRN, insurance_name, insurance_id)
- Consider tool reliability, latency, and data source (internal vs external)
- Prefer tools that can directly provide insurance_id and insurance_name
- If no direct tools exist, consider tools that can provide intermediate data (e.g., patient_id) for multi-step resolution

For "internal" priority, only select tools that access internal systems.
For "external" priority, only select tools that access external systems.""",
        
        "OUTPUT": {
            "schema": {
                "description": "Return JSON with selected tools and execution plan",
                "structure": {
                    "selected_tools": [
                        {
                            "tool_key": "tool_name",
                            "reasoning": "Why this tool is selected",
                            "expected_output": "What this tool will provide (e.g., 'insurance_id', 'patient_id', 'insurance_info')"
                        }
                    ],
                    "execution_plan": "string - either 'sequential' or 'parallel'",
                    "tool_sequence": ["tool_key_1", "tool_key_2"],
                    "reasoning": "Overall strategy for tool selection"
                }
            }
        },
        
        "CONSTRAINTS": [
            "Return ONLY valid JSON - no markdown, no code blocks",
            "Only select tools that are actually available in the TOOL_SCHEMAS",
            "For 'internal' priority, only select tools that access internal systems",
            "For 'external' priority, only select tools that access external systems"
        ],
        
        "GENERATION_CONFIG": {
            "temperature": 0.2,
            "max_output_tokens": 2000,
            "top_p": 0.95,
            "top_k": 40
        }
    }
    
    await database.connect()
    
    try:
        prompt_id = await prompt_manager.create_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="insurance_tool_selection",
            prompt_config=prompt_config,
            description="LLM-guided tool selection for insurance resolution",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded Insurance Tool Selection prompt (ID: {prompt_id})")
        print(f"   Key: workflow:eligibility:TABULA_RASA:insurance_tool_selection")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        raise
    finally:
        await database.disconnect()


async def seed_insurance_multi_step_planning_prompt():
    """Seed the Insurance Multi-Step Planning prompt."""
    
    prompt_config = {
        "ROLE": """You are a workflow planner for healthcare insurance information retrieval. Your task is to design a multi-step tool execution chain to resolve insurance information when single tools are insufficient.""",
        
        "CONTEXT": """You receive:
- Patient Information: {FORM_DATA} (name, DOB, MRN, insurance_name, insurance_id)
- Available Tools: {TOOL_SCHEMAS} (list of tool schemas)
- Partial Results: {PARTIAL_RESULTS} (Results from previous attempts, e.g., "We have patient_id but need insurance_id")

Multi-Step Chain Design:
- Step 1: Tool A provides intermediate data X (e.g., patient_id from name+DOB)
- Step 2: Tool B uses X to provide Y (e.g., insurance_id from patient_id)
- Step 3: Tool C uses Y to provide final insurance info (e.g., insurance_name from insurance_id)""",
        
        "ANALYSIS": """Design a chain where each step uses the output from the previous step:
1. Identify what data is available (from FORM_DATA and PARTIAL_RESULTS)
2. Identify what data is needed (insurance_id and insurance_name)
3. Plan a sequence of tool calls that bridges the gap
4. Use placeholders like "<from_step_1>" to reference outputs from previous steps""",
        
        "OUTPUT": {
            "schema": {
                "description": "Return JSON with resolution chain",
                "structure": {
                    "resolution_chain": [
                        {
                            "step": 1,
                            "tool_key": "tool_name",
                            "input": {"name": "string", "dob": "string"},
                            "expected_output": "patient_id",
                            "reasoning": "First, get patient_id from name+DOB"
                        },
                        {
                            "step": 2,
                            "tool_key": "tool_name",
                            "input": {"patient_id": "<from_step_1>"},
                            "expected_output": "insurance_id",
                            "reasoning": "Then, use patient_id to get insurance_id"
                        }
                    ],
                    "reasoning": "Overall strategy for the multi-step chain"
                }
            }
        },
        
        "CONSTRAINTS": [
            "Return ONLY valid JSON - no markdown, no code blocks",
            "Use placeholders like '<from_step_1>' to reference outputs from previous steps",
            "Each step should use the expected_output from the previous step",
            "Only use tools that are actually available in the TOOL_SCHEMAS"
        ],
        
        "GENERATION_CONFIG": {
            "temperature": 0.2,
            "max_output_tokens": 2000,
            "top_p": 0.95,
            "top_k": 40
        }
    }
    
    await database.connect()
    
    try:
        prompt_id = await prompt_manager.create_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="insurance_multi_step_planning",
            prompt_config=prompt_config,
            description="LLM-guided multi-step tool chain planning for insurance resolution",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded Insurance Multi-Step Planning prompt (ID: {prompt_id})")
        print(f"   Key: workflow:eligibility:TABULA_RASA:insurance_multi_step_planning")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        raise
    finally:
        await database.disconnect()


async def seed_all_prompts():
    """Seed all eligibility workflow prompts."""
    print("🌱 Seeding Eligibility Workflow prompts...")
    print("")
    
    await seed_insurance_tool_selection_prompt()
    print("")
    
    await seed_insurance_multi_step_planning_prompt()
    print("")
    
    print("✅ All Eligibility Workflow prompts seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_all_prompts())

