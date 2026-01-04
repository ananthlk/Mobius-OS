"""
Plan State Manager (Reusable)

Manages workflow plan state, lifecycle, and agent enhancements.
Works with any module:domain:strategy:step pattern.
"""

import logging
from typing import Dict, Any, Optional, List
from nexus.modules.database import database
from nexus.core.plan_models import (
    WorkflowPlan, WorkflowPhase, WorkflowStep,
    PlanStatus, PhaseStatus, StepStatus,
    PlanMetadata, PhaseMetadata, StepMetadata,
    ToolDefinition
)
from nexus.core.tree_structure_manager import TreePath
import json
from datetime import datetime

logger = logging.getLogger("nexus.core.plan_state")

class PlanStateManager:
    """
    Manages workflow plan state, lifecycle, and agent enhancements.
    Reusable across different modules/domains.
    """
    
    async def save_plan(
        self,
        session_id: int,
        plan: WorkflowPlan,
        path: Optional[TreePath] = None,
        user_id: str = "system"
    ) -> int:
        """
        Save a workflow plan with full metadata.
        
        Args:
            session_id: Session ID
            plan: WorkflowPlan object
            path: Optional tree path for context
            user_id: User creating the plan
        """
        plan_dict = self._plan_to_dict(plan)
        
        # Build template key from path if provided
        template_key = None
        if path and plan.metadata.parent_template_key:
            template_key = plan.metadata.parent_template_key
        elif path:
            template_key = f"{path.module}:{path.domain}:{path.strategy}:template"
        
        query = """
            INSERT INTO workflow_plans 
            (session_id, plan_name, problem_statement, goal, plan_structure, 
             metadata, parent_template_key, status, created_by)
            VALUES (:session_id, :name, :problem, :goal, :structure, 
                    :metadata, :template, :status, :user)
            RETURNING id
        """
        
        plan_id = await database.fetch_val(query, {
            "session_id": session_id,
            "name": plan.name,
            "problem": plan.problem_statement,
            "goal": plan.goal,
            "structure": json.dumps(plan_dict),
            "metadata": json.dumps(self._metadata_to_dict(plan.metadata)),
            "template": template_key,
            "status": plan.metadata.status.value,
            "user": user_id
        })
        
        # Save phases and steps
        for phase_idx, phase in enumerate(plan.phases):
            phase_id = await self._save_phase(plan_id, phase, phase_idx)
            for step_idx, step in enumerate(phase.steps):
                await self._save_step(plan_id, phase_id, step, step_idx)
        
        logger.info(f"✅ Saved workflow plan (ID: {plan_id}) for session {session_id}")
        return plan_id
    
    async def _save_phase(
        self,
        plan_id: int,
        phase: WorkflowPhase,
        phase_idx: int
    ) -> int:
        """Save a phase."""
        phase_dict = {
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "tool_hint": step.tool_hint
                }
                for step in phase.steps
            ]
        }
        
        query = """
            INSERT INTO workflow_plan_phases
            (plan_id, phase_id, phase_name, description, phase_structure, metadata, status, execution_order)
            VALUES (:plan_id, :phase_id, :name, :desc, :structure, :metadata, :status, :order)
            RETURNING id
        """
        
        phase_id = await database.fetch_val(query, {
            "plan_id": plan_id,
            "phase_id": phase.id,
            "name": phase.name,
            "desc": phase.description,
            "structure": json.dumps(phase_dict),
            "metadata": json.dumps(self._phase_metadata_to_dict(phase.metadata)),
            "status": phase.metadata.status.value,
            "order": phase_idx
        })
        
        return phase_id
    
    async def _save_step(
        self,
        plan_id: int,
        phase_id: int,
        step: WorkflowStep,
        step_idx: int
    ):
        """Save a step."""
        tool_dict = self._tool_to_dict(step.tool) if step.tool else None
        
        query = """
            INSERT INTO workflow_plan_steps
            (plan_id, phase_id, step_id, description, tool_definition, metadata, status, execution_order)
            VALUES (:plan_id, :phase_id, :step_id, :desc, :tool, :metadata, :status, :order)
        """
        
        await database.execute(query, {
            "plan_id": plan_id,
            "phase_id": phase_id,
            "step_id": step.id,
            "desc": step.description,
            "tool": json.dumps(tool_dict) if tool_dict else None,
            "metadata": json.dumps(self._step_metadata_to_dict(step.metadata)),
            "status": step.metadata.status.value,
            "order": step_idx
        })
    
    async def update_plan_status(
        self,
        plan_id: int,
        new_status: PlanStatus,
        user_id: str = "system",
        notes: Optional[str] = None
    ):
        """
        Update plan status (e.g., DRAFT -> USER_APPROVED).
        """
        update_data = {
            "status": new_status.value,
            "last_modified_by": user_id,
            "updated_at": datetime.now()
        }
        
        if new_status == PlanStatus.USER_APPROVED:
            update_data["approved_at"] = datetime.now()
            update_data["approved_by"] = user_id
        elif new_status == PlanStatus.EXECUTING:
            update_data["execution_started_at"] = datetime.now()
        elif new_status in [PlanStatus.COMPLETED, PlanStatus.FAILED]:
            update_data["execution_completed_at"] = datetime.now()
        
        if notes:
            query = """
                UPDATE workflow_plans
                SET metadata = jsonb_set(metadata, '{notes}', :notes::jsonb),
                    status = :status,
                    approved_at = COALESCE(:approved_at, approved_at),
                    approved_by = COALESCE(:approved_by, approved_by),
                    execution_started_at = COALESCE(:exec_started, execution_started_at),
                    execution_completed_at = COALESCE(:exec_completed, execution_completed_at),
                    last_modified_by = :user,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :plan_id
            """
            await database.execute(query, {
                "plan_id": plan_id,
                "status": new_status.value,
                "user": user_id,
                "notes": json.dumps(notes),
                "approved_at": update_data.get("approved_at"),
                "approved_by": update_data.get("approved_by"),
                "exec_started": update_data.get("execution_started_at"),
                "exec_completed": update_data.get("execution_completed_at")
            })
        else:
            query = """
                UPDATE workflow_plans
                SET status = :status,
                    approved_at = COALESCE(:approved_at, approved_at),
                    approved_by = COALESCE(:approved_by, approved_by),
                    execution_started_at = COALESCE(:exec_started, execution_started_at),
                    execution_completed_at = COALESCE(:exec_completed, execution_completed_at),
                    last_modified_by = :user,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :plan_id
            """
            await database.execute(query, {
                "plan_id": plan_id,
                "status": new_status.value,
                "user": user_id,
                "approved_at": update_data.get("approved_at"),
                "approved_by": update_data.get("approved_by"),
                "exec_started": update_data.get("execution_started_at"),
                "exec_completed": update_data.get("execution_completed_at")
            })
    
    async def enhance_step_with_tool(
        self,
        plan_id: int,
        step_id: str,
        tool: ToolDefinition,
        enhanced_by: str,
        enhanced_by_type: str = "agent",
        reason: Optional[str] = None
    ):
        """
        Add or enhance a step with tool definition.
        Used by agents to build on the plan.
        """
        step_query = """
            SELECT id, tool_definition, metadata
            FROM workflow_plan_steps
            WHERE plan_id = :plan_id AND step_id = :step_id
        """
        step_row = await database.fetch_one(step_query, {
            "plan_id": plan_id,
            "step_id": step_id
        })
        
        if not step_row:
            raise ValueError(f"Step {step_id} not found in plan {plan_id}")
        
        tool_dict = self._tool_to_dict(tool)
        updated_metadata = dict(step_row["metadata"]) if step_row["metadata"] else {}
        updated_metadata["tool_configured"] = True
        updated_metadata["tool_configured_at"] = datetime.now().isoformat()
        updated_metadata["tool_configured_by"] = enhanced_by
        
        if "enhanced_by_agents" not in updated_metadata:
            updated_metadata["enhanced_by_agents"] = []
        if enhanced_by not in updated_metadata["enhanced_by_agents"]:
            updated_metadata["enhanced_by_agents"].append(enhanced_by)
        
        update_query = """
            UPDATE workflow_plan_steps
            SET tool_definition = :tool,
                metadata = :metadata::jsonb,
                status = 'tool_configured',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :step_db_id
        """
        await database.execute(update_query, {
            "step_db_id": step_row["id"],
            "tool": json.dumps(tool_dict),
            "metadata": json.dumps(updated_metadata)
        })
        
        enhancement_query = """
            INSERT INTO workflow_plan_enhancements
            (plan_id, step_id, enhancement_type, enhancement_data, 
             enhanced_by, enhanced_by_type, enhancement_reason)
            VALUES (:plan_id, :step_id, 'tool_added', :data, 
                    :by, :by_type, :reason)
        """
        await database.execute(enhancement_query, {
            "plan_id": plan_id,
            "step_id": step_row["id"],
            "data": json.dumps(tool_dict),
            "by": enhanced_by,
            "by_type": enhanced_by_type,
            "reason": reason
        })
        
        logger.info(f"✅ Enhanced step {step_id} with tool {tool.tool_name} by {enhanced_by}")
    
    async def map_step_inputs(
        self,
        plan_id: int,
        step_id: str,
        input_mapping: Dict[str, str],
        mapped_by: str
    ):
        """
        Map step inputs to data sources.
        """
        step_query = """
            SELECT id, tool_definition
            FROM workflow_plan_steps
            WHERE plan_id = :plan_id AND step_id = :step_id
        """
        step_row = await database.fetch_one(step_query, {
            "plan_id": plan_id,
            "step_id": step_id
        })
        
        if not step_row or not step_row["tool_definition"]:
            raise ValueError(f"Step {step_id} has no tool definition")
        
        tool_def = dict(step_row["tool_definition"])
        tool_def["inputs"] = input_mapping
        tool_def["input_sources"] = {k: "gate_state" for k in input_mapping.keys()}
        
        update_query = """
            UPDATE workflow_plan_steps
            SET tool_definition = :tool,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :step_db_id
        """
        await database.execute(update_query, {
            "step_db_id": step_row["id"],
            "tool": json.dumps(tool_def)
        })
        
        enhancement_query = """
            INSERT INTO workflow_plan_enhancements
            (plan_id, step_id, enhancement_type, enhancement_data, 
             enhanced_by, enhanced_by_type)
            VALUES (:plan_id, :step_id, 'input_mapped', :data, 
                    :by, 'agent')
        """
        await database.execute(enhancement_query, {
            "plan_id": plan_id,
            "step_id": step_row["id"],
            "data": json.dumps({"input_mapping": input_mapping}),
            "by": mapped_by
        })
    
    def _plan_to_dict(self, plan: WorkflowPlan) -> Dict[str, Any]:
        """Convert plan to dictionary for storage."""
        return {
            "phases": [
                {
                    "id": phase.id,
                    "name": phase.name,
                    "description": phase.description,
                    "steps": [
                        {
                            "id": step.id,
                            "description": step.description,
                            "tool_hint": step.tool_hint,
                            "timeline_estimate": step.timeline_estimate
                        }
                        for step in phase.steps
                    ]
                }
                for phase in plan.phases
            ]
        }
    
    def _metadata_to_dict(self, metadata: PlanMetadata) -> Dict[str, Any]:
        """Convert plan metadata to dictionary."""
        return {
            "status": metadata.status.value,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
            "approved_at": metadata.approved_at.isoformat() if metadata.approved_at else None,
            "approved_by": metadata.approved_by,
            "version": metadata.version,
            "parent_template_key": metadata.parent_template_key,
            "notes": metadata.notes
        }
    
    def _phase_metadata_to_dict(self, metadata: PhaseMetadata) -> Dict[str, Any]:
        """Convert phase metadata to dictionary."""
        return {
            "status": metadata.status.value,
            "execution_order": metadata.execution_order,
            "can_skip": metadata.can_skip,
            "skip_reason": metadata.skip_reason,
            "notes": metadata.notes
        }
    
    def _step_metadata_to_dict(self, metadata: StepMetadata) -> Dict[str, Any]:
        """Convert step metadata to dictionary."""
        return {
            "status": metadata.status.value,
            "execution_order": metadata.execution_order,
            "tool_configured": metadata.tool_configured,
            "tool_configured_at": metadata.tool_configured_at.isoformat() if metadata.tool_configured_at else None,
            "tool_configured_by": metadata.tool_configured_by,
            "depends_on_steps": metadata.depends_on_steps,
            "enhanced_by_agents": metadata.enhanced_by_agents,
            "notes": metadata.notes
        }
    
    def _tool_to_dict(self, tool: ToolDefinition) -> Dict[str, Any]:
        """Convert tool definition to dictionary."""
        return {
            "tool_name": tool.tool_name,
            "tool_id": tool.tool_id,
            "description": tool.description,
            "inputs": tool.inputs,
            "input_sources": tool.input_sources,
            "outputs": tool.outputs,
            "output_mapping": tool.output_mapping,
            "timeout_ms": tool.timeout_ms,
            "retry_count": tool.retry_count,
            "condition": tool.condition
        }

# Singleton
plan_state_manager = PlanStateManager()


