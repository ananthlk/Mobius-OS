"""
User Repository

Handles all database operations for users table.
"""
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from nexus.modules.database import database

logger = logging.getLogger("nexus.users.repository")


class UserRepository:
    """Repository for user data access."""
    
    def __init__(self):
        self._parse_jsonb = self._create_jsonb_parser()
    
    @staticmethod
    def _create_jsonb_parser():
        """Create JSONB parser function."""
        def parse_jsonb(value: Any) -> Any:
            """Parse JSONB value from database."""
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return {}
            elif value is None:
                return {}
            return value
        return parse_jsonb
    
    async def create(
        self,
        auth_id: str,
        email: str,
        name: Optional[str] = None,
        role: str = "user"
    ) -> int:
        """Create a new user and return user_id."""
        query = """
            INSERT INTO users (auth_id, email, name, role)
            VALUES (:auth_id, :email, :name, :role)
            RETURNING id
        """
        user_id = await database.fetch_val(query, {
            "auth_id": auth_id,
            "email": email,
            "name": name,
            "role": role
        })
        return user_id
    
    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = """
            SELECT id, auth_id, email, name, role, is_active, created_at, updated_at
            FROM users
            WHERE id = :user_id
        """
        row = await database.fetch_one(query, {"user_id": user_id})
        if not row:
            return None
        return dict(row)
    
    async def get_by_auth_id(self, auth_id: str) -> Optional[Dict[str, Any]]:
        """Get user by auth_id."""
        query = """
            SELECT id, auth_id, email, name, role, is_active, created_at, updated_at
            FROM users
            WHERE auth_id = :auth_id
        """
        row = await database.fetch_one(query, {"auth_id": auth_id})
        if not row:
            return None
        return dict(row)
    
    async def update(
        self,
        user_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """Update user fields."""
        allowed_fields = ["email", "name", "role", "is_active"]
        set_clauses = []
        values = {"user_id": user_id}
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = :{field}")
                values[field] = updates[field]
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = :user_id"
        await database.execute(query, values)
        return True
    
    async def delete(self, user_id: int) -> bool:
        """Soft delete user (set is_active = false)."""
        query = """
            UPDATE users
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id
        """
        await database.execute(query, {"user_id": user_id})
        return True
    
    async def list(
        self,
        role_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List users with optional filtering."""
        query = """
            SELECT id, auth_id, email, name, role, is_active, created_at, updated_at
            FROM users
            WHERE 1=1
        """
        values = {}
        
        if active_only:
            query += " AND is_active = true"
        
        if role_filter:
            query += " AND role = :role"
            values["role"] = role_filter
        
        query += " ORDER BY created_at DESC"
        
        rows = await database.fetch_all(query, values)
        return [dict(row) for row in rows]
    
    async def get_role(self, user_id: int) -> Optional[str]:
        """Get user role."""
        query = "SELECT role FROM users WHERE id = :user_id"
        role = await database.fetch_val(query, {"user_id": user_id})
        return role



