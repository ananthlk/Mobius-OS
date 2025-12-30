from typing import Dict, List, Optional
import json
import logging
from nexus.modules.database import database
from nexus.core.base_agent import AgentRecipe, AgentStep

class WorkflowRegistry:
    """
    Database-backed Store for Agent Recipes.
    Uses 'nexus.modules.database' for async queries.
    """
    def __init__(self):
        self.logger = logging.getLogger("WorkflowRegistry")

    async def register_recipe(self, recipe: AgentRecipe):
        """
        Saves a recipe to the DB (Upsert logic).
        For V1, simplistic upsert based on name.
        """
        query_check = "SELECT id, version FROM agent_recipes WHERE name = :name"
        existing = await database.fetch_one(query=query_check, values={"name": recipe.name})
        
        steps_json = json.dumps({
            step_id: {
                "step_id": s.step_id,
                "tool_name": s.tool_name,
                "description": s.description,
                "args_mapping": s.args_mapping,
                "transition_success": s.transition_success,
                "transition_fail": s.transition_fail
            } for step_id, s in recipe.steps.items()
        })

        if existing:
            # Update (Increment Version)
            new_version = existing["version"] + 1
            query_update = """
            UPDATE agent_recipes 
            SET goal=:goal, steps=:steps, start_step_id=:start, version=:ver, updated_at=CURRENT_TIMESTAMP
            WHERE name=:name
            """
            await database.execute(query=query_update, values={
                "name": recipe.name,
                "goal": recipe.goal,
                "steps": steps_json,
                "start": recipe.start_step_id,
                "ver": new_version
            })
            self.logger.info(f"🔄 Updated Workflow: {recipe.name} (v{new_version})")
        else:
            # Insert
            query_insert = """
            INSERT INTO agent_recipes (name, goal, steps, start_step_id, version, status)
            VALUES (:name, :goal, :steps, :start, 1, 'ACTIVE')
            """
            await database.execute(query=query_insert, values={
                "name": recipe.name,
                "goal": recipe.goal,
                "steps": steps_json,
                "start": recipe.start_step_id
            })
            self.logger.info(f"✅ Created Workflow: {recipe.name} (v1)")

    async def get_recipe(self, name: str) -> Optional[AgentRecipe]:
        """
        Retrieves active recipe by name.
        """
        query = "SELECT * FROM agent_recipes WHERE name = :name"
        row = await database.fetch_one(query=query, values={"name": name})
        
        if not row:
            return None
            
        # Parse JSON steps back to Objects
        steps_raw = json.loads(row["steps"])
        steps = {}
        for sid, sdata in steps_raw.items():
            steps[sid] = AgentStep(
                step_id=sdata["step_id"],
                tool_name=sdata["tool_name"],
                description=sdata.get("description", ""),
                args_mapping=sdata.get("args_mapping", {}),
                transition_success=sdata.get("transition_success"),
                transition_fail=sdata.get("transition_fail")
            )
            
        return AgentRecipe(
            name=row["name"],
            goal=row["goal"],
            steps=steps,
            start_step_id=row["start_step_id"]
        )

    async def list_recipes(self) -> List[str]:
        query = "SELECT name FROM agent_recipes WHERE status='ACTIVE'"
        rows = await database.fetch_all(query=query)
        return [r["name"] for r in rows]

# Singleton
registry = WorkflowRegistry()
