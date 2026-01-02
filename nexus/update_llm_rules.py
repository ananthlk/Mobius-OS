import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from nexus.modules.database import database

async def update_rules():
    print("🔌 Connecting to DB...")
    await database.connect()
    
    try:
        # 1. Find Gemini Flash Model ID
        print("🔍 Finding Gemini 1.5 Flash...")
        model = await database.fetch_one("SELECT id FROM llm_models WHERE model_id = 'gemini-1.5-flash'")
        
        if not model:
            print("❌ Gemini 1.5 Flash not found in llm_models! Do you need to run discovery?")
            return
            
        gemini_id = model["id"]
        print(f"✅ Found Gemini ID: {gemini_id}")
        
        # 2. Update Global Rule
        print("🛠️  Updating GLOBAL Rule...")
        await database.execute(
            "UPDATE llm_system_rules SET model_id = :mid WHERE rule_type = 'GLOBAL'", 
            {"mid": gemini_id}
        )
        
        # 3. Update 'chat' Module Rule
        print("🛠️  Updating 'chat' Module Rule...")
        await database.execute(
            "UPDATE llm_system_rules SET model_id = :mid WHERE rule_type = 'MODULE' AND module_id = 'chat'",
            {"mid": gemini_id}
        )

         # 4. Insert/Update 'workflow' Module Rule (Use Pro for planning if available, else Flash)
        print("🔍 Finding Gemini 1.5 Pro for Workflow...")
        pro_model = await database.fetch_one("SELECT id FROM llm_models WHERE model_id = 'gemini-1.5-pro'")
        workflow_model_id = pro_model["id"] if pro_model else gemini_id
        
        print(f"✅ Workflow Model ID: {workflow_model_id}")
        
        # Upsert workflow rule
        existing = await database.fetch_one("SELECT id FROM llm_system_rules WHERE rule_type = 'MODULE' AND module_id = 'workflow'")
        if existing:
             await database.execute(
                "UPDATE llm_system_rules SET model_id = :mid WHERE id = :id",
                {"mid": workflow_model_id, "id": existing["id"]}
            )
        else:
            await database.execute(
                "INSERT INTO llm_system_rules (rule_type, module_id, model_id) VALUES ('MODULE', 'workflow', :mid)",
                {"mid": workflow_model_id}
            )

        print("✨ Rules updated successfully.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(update_rules())
