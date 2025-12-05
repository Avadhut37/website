from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..core.sockets import manager

router = APIRouter()

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            # We are just receiving messages, but not doing anything with them.
            # The main purpose is to keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
