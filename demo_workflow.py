import asyncio
from nexus.core.base_agent import NexusAgentFactory
from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool
from nexus.recipes.crm_recipes import ASSURANCE_RECIPE
import json

async def main():
    print("🚀 Initializing Agent Engine...")
    tools = [ScheduleScannerTool(), RiskCalculatorTool()]
    factory = NexusAgentFactory(available_tools=tools)
    
    print(f"📖 Loading Recipe: {ASSURANCE_RECIPE.name}")
    print(f"🎯 Goal: {ASSURANCE_RECIPE.goal}")
    
    initial_context = {"days_to_plan": 14}
    
    print("\n▶️ Running Workflow...")
    result = await factory.run_recipe(ASSURANCE_RECIPE, initial_context)
    
    print("\n✅ Workflow Complete!")
    print("--- Final Context Report ---")
    
    # The factory merges dict results into the context
    # So we look for 'summary' which the RiskCalculator returns
    print("\n📊 Workflow Summary:")
    print(json.dumps(result.get("summary", "No Summary Found"), indent=2))
    
    print("\n🚩 High Risk Appointments:")
    appointments = result.get("appointments", [])
    high_risk = [a for a in appointments if a.get("flags")]
    print(json.dumps(high_risk, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
