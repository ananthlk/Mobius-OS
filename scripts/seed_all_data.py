#!/usr/bin/env python3
"""
Comprehensive data seeding script for Mobius OS
Seeds all essential data: prompts, tools, recipes, tasks, etc.
Run this after database migrations to restore system to working state.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from nexus.modules.database import connect_to_db, disconnect_from_db, database

async def seed_all():
    """Seed all essential data for the system."""
    print("🌱 Starting comprehensive data seeding for Mobius OS...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # 1. Seed Tool Library
        print("\n📦 [1/6] Seeding Tool Library...")
        try:
            from nexus.tools.library.seed_tools import seed_tools
            await seed_tools()
            print("   ✅ Tool library seeded")
        except Exception as e:
            print(f"   ⚠️  Tool library seeding failed: {e}")
        
        # 2. Register CRM Recipes (Workflows)
        print("\n🔄 [2/6] Registering CRM Recipes...")
        try:
            from nexus.recipes.crm_recipes import register_crm_recipes
            await register_crm_recipes()
            print("   ✅ CRM recipes registered")
        except Exception as e:
            print(f"   ⚠️  CRM recipes registration failed: {e}")
        
        # 3. Seed Prompts
        print("\n📝 [3/6] Seeding Prompts...")
        prompt_scripts = [
            ("TABULA_RASA", "nexus.scripts.seed_tabula_rasa_prompt"),
            ("Gate Prompt", "nexus.scripts.seed_gate_prompt"),
            ("Planner Prompt", "nexus.scripts.seed_planner_prompt"),
            ("Planner Template", "nexus.scripts.seed_planner_template"),
            ("Bounded Plan Prompts", "nexus.scripts.seed_bounded_plan_prompts"),
            ("Plan Implementation Prompt", "nexus.scripts.seed_plan_implementation_prompt"),
            ("Conversational Agent Prompt", "nexus.scripts.seed_conversational_agent_prompt"),
        ]
        
        for prompt_name, module_path in prompt_scripts:
            try:
                # Import the module
                module = __import__(module_path, fromlist=[''])
                
                # Check if module has seed functions that manage their own DB connection
                # If so, we need to ensure DB is connected before calling
                if not database.is_connected:
                    await database.connect()
                
                if hasattr(module, 'seed_prompt'):
                    # Some seed scripts disconnect DB, so reconnect if needed
                    result = await module.seed_prompt()
                    if not database.is_connected:
                        await database.connect()
                    print(f"   ✅ {prompt_name} seeded")
                elif hasattr(module, 'seed_all_prompts'):
                    result = await module.seed_all_prompts()
                    if not database.is_connected:
                        await database.connect()
                    print(f"   ✅ {prompt_name} seeded")
                elif hasattr(module, 'seed_gate_prompt'):
                    result = await module.seed_gate_prompt()
                    if not database.is_connected:
                        await database.connect()
                    print(f"   ✅ {prompt_name} seeded")
                elif hasattr(module, 'seed_planner_template'):
                    result = await module.seed_planner_template()
                    if not database.is_connected:
                        await database.connect()
                    print(f"   ✅ {prompt_name} seeded")
                else:
                    print(f"   ⚠️  {prompt_name}: No seed function found")
            except Exception as e:
                # Ensure DB is still connected after errors
                if not database.is_connected:
                    await database.connect()
                print(f"   ⚠️  {prompt_name} seeding failed: {e}")
        
        # 4. Seed Tasks from Template
        print("\n📋 [4/6] Seeding Tasks from Template...")
        try:
            from nexus.modules.task_registry import task_registry
            # Check if tasks already exist
            existing_task_count = await database.fetch_val(query="SELECT COUNT(*) FROM task_catalog")
            if existing_task_count == 0:
                # Import and run task seeding
                from nexus.scripts.seed_tasks_from_template import seed_tasks
                await seed_tasks()
                print("   ✅ Tasks seeded from template")
            else:
                print(f"   ℹ️  Task catalog already has {existing_task_count} tasks, skipping seed")
        except Exception as e:
            print(f"   ⚠️  Task seeding failed: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. Seed LLM Configurations
        print("\n🤖 [5/7] Seeding LLM Configurations...")
        try:
            from nexus.modules.llm_service import llm_service
            
            # Sync models (seeds known models for all providers)
            print("   Syncing LLM models...")
            await llm_service.sync_models()
            print("   ✅ LLM models synced")
            
            # Update LLM system rules
            print("   Setting LLM system rules...")
            # Import and run update_rules function
            from nexus.update_llm_rules import update_rules
            await update_rules()
            print("   ✅ LLM system rules set")
            
        except Exception as e:
            print(f"   ⚠️  LLM configuration failed: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. Check User Profiles
        print("\n👤 [6/7] Checking User Profiles...")
        try:
            # Check if user_profiles table exists
            user_count = await database.fetch_val(query="SELECT COUNT(*) FROM user_profiles")
            print(f"   ℹ️  User profiles table has {user_count} users")
            if user_count == 0:
                print("   ℹ️  User profiles will be created on first use")
        except Exception as e:
            print(f"   ⚠️  User profiles check failed: {e}")
        
        # 7. Verify Essential Data (before disconnecting)
        print("\n✅ [7/7] Verifying Essential Data...")
        try:
            # Check tool library (table is called 'tools', not 'tool_library')
            try:
                tool_count = await database.fetch_val(query="SELECT COUNT(*) FROM tools")
                print(f"   📦 Tool Library: {tool_count} tools")
            except Exception as e:
                print(f"   📦 Tool Library: Table not found or error: {e}")
            
            # Check prompts
            try:
                prompt_count = await database.fetch_val(query="SELECT COUNT(*) FROM prompt_templates")
                print(f"   📝 Prompts: {prompt_count} prompts")
            except Exception as e:
                print(f"   📝 Prompts: Error: {e}")
            
            # Check recipes
            try:
                recipe_count = await database.fetch_val(query="SELECT COUNT(*) FROM agent_recipes")
                print(f"   🔄 Recipes: {recipe_count} recipes")
            except Exception as e:
                print(f"   🔄 Recipes: Error: {e}")
            
            # Check task catalog
            try:
                task_count = await database.fetch_val(query="SELECT COUNT(*) FROM task_catalog")
                print(f"   📋 Tasks: {task_count} tasks")
            except Exception as e:
                print(f"   📋 Tasks: Table not found or empty")
            
            # Check user profiles (check users table instead)
            try:
                user_count = await database.fetch_val(query="SELECT COUNT(*) FROM users")
                print(f"   👤 Users: {user_count} users")
            except Exception as e:
                print(f"   👤 Users: Table not found or empty")
            
            # Check LLM models
            try:
                model_count = await database.fetch_val(query="SELECT COUNT(*) FROM llm_models")
                print(f"   🤖 LLM Models: {model_count} models")
            except Exception as e:
                print(f"   🤖 LLM Models: Error: {e}")
            
            # Check LLM system rules
            try:
                rule_count = await database.fetch_val(query="SELECT COUNT(*) FROM llm_system_rules")
                print(f"   📋 LLM Rules: {rule_count} rules")
            except Exception as e:
                print(f"   📋 LLM Rules: Error: {e}")
            
        except Exception as e:
            print(f"   ⚠️  Verification failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("🎉 Data seeding complete!")
        print("\nThe system should now be ready to use.")
        print("If any items show warnings, you may need to run individual seed scripts.")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(seed_all())

