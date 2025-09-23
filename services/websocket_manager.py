import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from models import WSMessage, WSMessageType, TradeUpdate

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Store active connections by execution ID
        self.connections: Dict[str, Set[WebSocket]] = {}
        # Store global connections (not tied to specific execution)
        self.global_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket, execution_id: Optional[str] = None):
        """Connect a WebSocket client"""
        await websocket.accept()
        
        if execution_id:
            if execution_id not in self.connections:
                self.connections[execution_id] = set()
            self.connections[execution_id].add(websocket)
            logger.info(f"WebSocket connected for execution {execution_id}")
        else:
            self.global_connections.add(websocket)
            logger.info("Global WebSocket connected")
        
        # Send welcome message
        await self.send_to_websocket(websocket, WSMessage(
            type=WSMessageType.STATUS_UPDATE,
            data={"status": "connected", "message": "WebSocket connection established"},
            timestamp=datetime.utcnow().isoformat(),
            executionId=execution_id
        ))
    
    def disconnect(self, websocket: WebSocket, execution_id: Optional[str] = None):
        """Disconnect a WebSocket client"""
        try:
            if execution_id and execution_id in self.connections:
                self.connections[execution_id].discard(websocket)
                if not self.connections[execution_id]:
                    del self.connections[execution_id]
                logger.info(f"WebSocket disconnected for execution {execution_id}")
            else:
                self.global_connections.discard(websocket)
                logger.info("Global WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")
    
    async def send_to_websocket(self, websocket: WebSocket, message: WSMessage):
        """Send message to a specific WebSocket"""
        try:
            await websocket.send_text(message.json())
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {str(e)}")
    
    async def broadcast_to_execution(self, execution_id: str, message: WSMessage):
        """Broadcast message to all connections for a specific execution"""
        if execution_id not in self.connections:
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections_copy = self.connections[execution_id].copy()
        disconnected = set()
        
        for websocket in connections_copy:
            try:
                await self.send_to_websocket(websocket, message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket, marking for removal: {str(e)}")
                disconnected.add(websocket)
        
        # Remove disconnected websockets
        for ws in disconnected:
            self.disconnect(ws, execution_id)
    
    async def broadcast_global(self, message: WSMessage):
        """Broadcast message to all global connections"""
        disconnected = set()
        
        # Create a copy to avoid modification during iteration
        connections_copy = self.global_connections.copy()
        
        for websocket in connections_copy:
            try:
                await self.send_to_websocket(websocket, message)
            except Exception as e:
                logger.warning(f"Failed to send to global WebSocket: {str(e)}")
                disconnected.add(websocket)
        
        # Remove disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_trade_update(self, execution_id: str, trade_update: TradeUpdate):
        """Send trade update for a specific execution"""
        message = WSMessage(
            type=WSMessageType.TRADE_UPDATE,
            data=trade_update.dict(),
            timestamp=datetime.utcnow().isoformat(),
            executionId=execution_id
        )
        await self.broadcast_to_execution(execution_id, message)
    
    async def send_status_update(self, execution_id: str, status: str, data: Dict[str, Any] = None):
        """Send status update for a specific execution"""
        message_data = {"status": status}
        if data:
            message_data.update(data)
        
        message = WSMessage(
            type=WSMessageType.STATUS_UPDATE,
            data=message_data,
            timestamp=datetime.utcnow().isoformat(),
            executionId=execution_id
        )
        await self.broadcast_to_execution(execution_id, message)
    
    async def send_error(self, execution_id: Optional[str], error: str, details: str = None):
        """Send error message"""
        error_data = {"error": error}
        if details:
            error_data["details"] = details
        
        message = WSMessage(
            type=WSMessageType.ERROR,
            data=error_data,
            timestamp=datetime.utcnow().isoformat(),
            executionId=execution_id
        )
        
        if execution_id:
            await self.broadcast_to_execution(execution_id, message)
        else:
            await self.broadcast_global(message)
    
    async def handle_websocket_messages(self, websocket: WebSocket, execution_id: Optional[str] = None):
        """Handle incoming WebSocket messages"""
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type")
                    
                    if message_type == "ping":
                        # Respond to ping with pong
                        pong_message = WSMessage(
                            type=WSMessageType.PONG,
                            data={"message": "pong"},
                            timestamp=datetime.utcnow().isoformat(),
                            executionId=execution_id
                        )
                        await self.send_to_websocket(websocket, pong_message)
                    
                    logger.debug(f"Received WebSocket message: {message_type}")
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from WebSocket: {data}")
                    
        except WebSocketDisconnect:
            self.disconnect(websocket, execution_id)
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            self.disconnect(websocket, execution_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        execution_connections = sum(len(conns) for conns in self.connections.values())
        return {
            "total_connections": execution_connections + len(self.global_connections),
            "execution_connections": execution_connections,
            "global_connections": len(self.global_connections),
            "active_executions": len(self.connections)
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()