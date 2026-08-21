from fastapi import WebSocket


class BroadcastService:

    def __init__(self):

        self.clients = set()

    async def connect(self, ws: WebSocket):

        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):

        self.clients.discard(ws)

    async def broadcast(self, data: dict):

        if not self.clients:
            return

        for ws in list(self.clients):

            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)


broadcast_service = BroadcastService()
