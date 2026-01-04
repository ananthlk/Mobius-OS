"""
Template Manager (Reusable)

Generic template manager that works with any module:domain:strategy:step pattern.
Can be used for eligibility, CRM, or any other domain.
"""

import logging
from typing import Dict, Any, Optional, List
from nexus.modules.database import database
from nexus.core.tree_structure_manager import TreePath, tree_structure_manager
import json

logger = logging.getLogger("nexus.templates.manager")

class TemplateManager:
    """
    Reusable template manager following module:domain:strategy:step pattern.
    """
    
    def __init__(self, table_name: str = "plan_templates"):
        """
        Initialize template manager.
        
        Args:
            table_name: Database table name for templates (default: "plan_templates")
        """
        self.table_name = table_name
    
    def _build_template_key(self, path: TreePath) -> str:
        """Build template key from path."""
        return f"{path.module}:{path.domain}:{path.strategy}:template"
    
    async def save_template(
        self,
        path: TreePath,
        name: str,
        template_config: Dict[str, Any],
        match_pattern: Dict[str, Any],
        description: str = None,
        user_id: str = "system"
    ) -> int:
        """
        Save a template.
        
        Args:
            path: Tree path (module:domain:strategy:step)
            name: Template name
            template_config: Template configuration
            match_pattern: Pattern to match for this template
            description: Optional description
            user_id: User creating template
        """
        template_key = self._build_template_key(path)
        
        query = f"""
            INSERT INTO {self.table_name}
            (template_key, module_name, domain, strategy, step, name, description, 
             template_config, match_pattern, created_by, is_active)
            VALUES (:key, :module, :domain, :strategy, :step, :name, :desc, 
                    :config, :pattern, :user, true)
            RETURNING id
        """
        
        template_id = await database.fetch_val(query, {
            "key": template_key,
            "module": path.module,
            "domain": path.domain,
            "strategy": path.strategy,
            "step": path.step,
            "name": name,
            "desc": description,
            "config": json.dumps(template_config),
            "pattern": json.dumps(match_pattern),
            "user": user_id
        })
        
        logger.info(f"✅ Saved template: {template_key} (ID: {template_id})")
        return template_id
    
    async def get_template(
        self,
        path: TreePath
    ) -> Optional[Dict[str, Any]]:
        """
        Get a template by path.
        """
        template_key = self._build_template_key(path)
        
        query = f"""
            SELECT id, template_key, name, description, template_config, 
                   match_pattern, version, created_at, updated_at
            FROM {self.table_name}
            WHERE template_key = :key AND is_active = true
            ORDER BY version DESC
            LIMIT 1
        """
        
        row = await database.fetch_one(query, {"key": template_key})
        if not row:
            return None
        
        from nexus.modules.database import parse_jsonb
        row_dict = dict(row)
        
        return {
            "id": row_dict["id"],
            "template_key": row_dict["template_key"],
            "name": row_dict["name"],
            "description": row_dict.get("description"),
            "template_config": parse_jsonb(row_dict["template_config"]),
            "match_pattern": parse_jsonb(row_dict["match_pattern"]),
            "version": row_dict["version"],
            "created_at": row_dict["created_at"],
            "updated_at": row_dict.get("updated_at")
        }
    
    async def match_template(
        self,
        path: TreePath,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best matching template for a given context.
        
        Args:
            path: Tree path
            context: Context data to match against (e.g., gate_state)
        
        Returns:
            Matched template or None
        """
        query = f"""
            SELECT template_key, template_config, match_pattern
            FROM {self.table_name}
            WHERE module_name = :module 
              AND domain = :domain 
              AND strategy = :strategy
              AND is_active = true
        """
        
        rows = await database.fetch_all(query, {
            "module": path.module,
            "domain": path.domain,
            "strategy": path.strategy
        })
        
        best_match = None
        best_score = 0
        
        for row in rows:
            from nexus.modules.database import parse_jsonb
            pattern = parse_jsonb(row["match_pattern"])
            
            score = self._calculate_match_score(context, pattern)
            
            if score > best_score:
                best_score = score
                best_match = {
                    "template_key": row["template_key"],
                    "template_config": parse_jsonb(row["template_config"]),
                    "match_score": score
                }
        
        return best_match if best_score > 0.5 else None
    
    def _calculate_match_score(
        self,
        context: Dict[str, Any],
        pattern: Dict[str, Any]
    ) -> float:
        """
        Calculate how well context matches a template pattern.
        Returns score 0.0 to 1.0.
        """
        score = 0.0
        total_checks = 0
        
        # Match against pattern structure
        for key, expected_value in pattern.items():
            total_checks += 1
            if key in context:
                context_value = context[key]
                if context_value == expected_value:
                    score += 1.0
                elif isinstance(expected_value, str) and expected_value in str(context_value):
                    score += 0.5
        
        return score / total_checks if total_checks > 0 else 0.0
    
    async def list_templates(
        self,
        path: TreePath = None
    ) -> List[Dict[str, Any]]:
        """
        List templates, optionally filtered by path.
        """
        if path:
            query = f"""
                SELECT template_key, name, description, version, created_at
                FROM {self.table_name}
                WHERE module_name = :module 
                  AND domain = :domain 
                  AND strategy = :strategy
                  AND is_active = true
                ORDER BY created_at DESC
            """
            rows = await database.fetch_all(query, {
                "module": path.module,
                "domain": path.domain,
                "strategy": path.strategy
            })
        else:
            query = f"""
                SELECT template_key, name, description, version, created_at
                FROM {self.table_name}
                WHERE is_active = true
                ORDER BY created_at DESC
            """
            rows = await database.fetch_all(query)
        
        return [dict(r) for r in rows]

# Specialized instance for eligibility (can create others for different domains)
eligibility_template_manager = TemplateManager(table_name="eligibility_plan_templates")


