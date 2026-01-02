from fastapi import WebSocket
from typing import Dict, List, Any
import logging
import asyncio

logger = logging.getLogger("nexus.session_manager")

class SessionManager:
    """
    Manages active WebSocket connections for sessions.
    Path A of the Dual-Path Streaming Architecture.
    """
    def __init__(self):
        # session_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        """Accepts and stores a new WS connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WS Connected to Session {session_id}. Total: {len(self.active_connections[session_id])}")

    def disconnect(self, session_id: int, websocket: WebSocket):
        """Removes a WS connection."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
        logger.info(f"WS Disconnected from Session {session_id}")

    async def broadcast(self, session_id: int, data: Dict[str, Any]):
        """
        Push data to all connected clients for this session.
        (Path A: Immediate UI Update)
        """
        if session_id in self.active_connections:
            logger.debug(f"Broadcasting to {len(self.active_connections[session_id])} clients in Session {session_id}")
            # Broadcast to all connected sockets
            # Use asyncio.gather to broadcast in parallel? Or simple loop.
            # Simple loop is safer for connection handling usually.
            to_remove = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.warning(f"Failed to send to WS: {e}")
                    to_remove.append(connection)
            
            # Cleanup dead connections
            for dead in to_remove:
                self.disconnect(session_id, dead)

session_manager = SessionManager()
