from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.broadcast_service import broadcast_service
from app.services.jsonl_service import jsonl_session
from app.services.tiktok_service import tiktok_service

router = APIRouter(
    tags=["WebSocket"]
)


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await broadcast_service.connect(ws)

    try:

        await ws.send_json({
            "type": "status",
            "running": tiktok_service.running,
            "username": tiktok_service.username,
            "session_id": jsonl_session.session_id,
            "room_id": jsonl_session.room_id,
            "file": jsonl_session.path,
            "comment_count": jsonl_session.comment_count,
        })

        while True:
            await ws.receive_text()

    except WebSocketDisconnect:
        pass

    finally:

        broadcast_service.disconnect(ws)
