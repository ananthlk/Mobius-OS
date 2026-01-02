"""
Communication Preferences Module

Manages user preferences for conversational formatting (tone, style, engagement level).
Defaults: professional, brief, engaging
"""
import logging
from typing import Dict, Any, Optional
from nexus.modules.database import database

logger = logging.getLogger("nexus.communication_preferences")

# Default preferences
DEFAULT_PREFERENCES = {
    "tone": "professional",
    "style": "brief",
    "engagement_level": "engaging"
}


class CommunicationPreferences:
    """
    Manages user communication preferences for conversational agent formatting.
    """
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        """
        Get user communication preferences, or return defaults if not set.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with keys: tone, style, engagement_level
        """
        query = """
            SELECT tone, style, engagement_level
            FROM user_communication_preferences
            WHERE user_id = :user_id
        """
        
        try:
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                return {
                    "tone": row["tone"],
                    "style": row["style"],
                    "engagement_level": row["engagement_level"]
                }
        except Exception as e:
            logger.warning(f"Error fetching user preferences for {user_id}: {e}")
            # Fall through to defaults
        
        # Return defaults if user not found or error occurred
        return DEFAULT_PREFERENCES.copy()
    
    async def set_user_preferences(
        self, 
        user_id: str, 
        tone: Optional[str] = None,
        style: Optional[str] = None,
        engagement_level: Optional[str] = None
    ) -> None:
        """
        Set user communication preferences.
        
        Args:
            user_id: User identifier
            tone: Optional tone preference
            style: Optional style preference
            engagement_level: Optional engagement level preference
        """
        # Get current preferences (or defaults)
        current = await self.get_user_preferences(user_id)
        
        # Merge with new values (only update provided ones)
        final_tone = tone if tone is not None else current["tone"]
        final_style = style if style is not None else current["style"]
        final_engagement = engagement_level if engagement_level is not None else current["engagement_level"]
        
        # Use INSERT ... ON CONFLICT to upsert
        query = """
            INSERT INTO user_communication_preferences (user_id, tone, style, engagement_level, updated_at)
            VALUES (:user_id, :tone, :style, :engagement_level, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                tone = :tone,
                style = :style,
                engagement_level = :engagement_level,
                updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            await database.execute(query, {
                "user_id": user_id,
                "tone": final_tone,
                "style": final_style,
                "engagement_level": final_engagement
            })
            logger.info(f"Updated communication preferences for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating preferences for {user_id}: {e}")
            raise


# Singleton instance
communication_preferences = CommunicationPreferences()

