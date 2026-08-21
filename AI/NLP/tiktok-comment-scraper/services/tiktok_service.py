import asyncio
import base64

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent
)
from app.models.comment import Comment
from app.services.broadcast_service import broadcast_service
from app.services.comment_service import comment_service
from app.services.jsonl_service import jsonl_session


class TikTokService:

    def __init__(self):

        self.client = None
        self.task = None

        self.running = False
        self.username = None

    async def on_connect(self, event: ConnectEvent):
        print(f"Connected -> {self.username}")

        jsonl_session.start(
            username=self.username,
            room_id=self.client.room_id,
        )

        await broadcast_service.broadcast({
            "type": "status",
            "running": True,
            "username": self.username,
            "session_id": jsonl_session.session_id,
            "room_id": jsonl_session.room_id,
            "file": jsonl_session.path,
            "comment_count": jsonl_session.comment_count,
        })

    async def on_disconnect(self, event: DisconnectEvent):
        print("Disconnected")

        await jsonl_session.stop()

        await broadcast_service.broadcast({
            "type": "status",
            "running": False,
            "username": None,
        })

        self.running = False
        self.task = None
        self.client = None

    async def on_comment(self, event: CommentEvent):

        comment = Comment.create(
            tiktok_user_id=event.user.id if event.user else None,
            username=event.user.display_id if event.user else None,
            nickname=event.user.nickname if event.user else None,
            sec_uid=event.user.sec_uid if event.user else None,
            message=event.comment,
        )

        await comment_service.process(comment, event)

    async def start(self, username: str):

        if self.running:
            raise Exception("Live sedang berjalan.")

        if not username.startswith("@"):
            username = "@" + username

        self.username = username

        self.client = TikTokLiveClient(
            unique_id=username
        )

        self.client.add_listener(
            ConnectEvent,
            self.on_connect
        )

        self.client.add_listener(
            DisconnectEvent,
            self.on_disconnect
        )

        self.client.add_listener(
            CommentEvent,
            self.on_comment
        )

        self.task = asyncio.create_task(
            self.client.start()
        )

        self.running = True

    async def stop(self):

        if not self.running:
            return

        await self.client.disconnect()

    def status(self):

        return {
            "running": self.running,
            "username": self.username
        }


tiktok_service = TikTokService()
