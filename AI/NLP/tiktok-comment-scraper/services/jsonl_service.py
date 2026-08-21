import asyncio
import json
import os
from datetime import datetime
from uuid import uuid4


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "raw")


class JsonlSession:

    def __init__(self):

        self.file = None
        self.path = None

        self.session_id = None
        self.username = None
        self.room_id = None

        self.comment_count = 0
        self.started_at = None

        self._queue = None
        self._writer = None

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="seconds")

    def start(self, username: str, room_id):

        self.session_id = str(uuid4())
        self.username = username
        self.room_id = room_id
        self.comment_count = 0
        self.started_at = self._now()

        os.makedirs(DATA_DIR, exist_ok=True)

        timestamp = self.started_at.replace(":", "").replace("-", "").replace("T", "-")[:17]
        filename = f"{username.replace('@', '')}_{room_id or 'unknown'}_{timestamp}.jsonl"
        self.path = os.path.join(DATA_DIR, filename)

        self.file = open(self.path, "a", encoding="utf-8")

        self._queue = asyncio.Queue()
        self._writer = asyncio.create_task(self._writer_loop())

        self._queue.put_nowait({
            "type": "session_start",
            "session_id": self.session_id,
            "username": username,
            "room_id": room_id,
            "started_at": self.started_at,
        })

        print(f"JSONL session started -> {self.path}")

    def write(self, type: str, **payload):

        if self.file is None or self._queue is None:
            return

        self._queue.put_nowait({
            "type": type,
            "session_id": self.session_id,
            **payload,
        })

    async def _writer_loop(self):

        while True:

            data = await self._queue.get()

            if data is None:
                break

            line = json.dumps(data, default=str, ensure_ascii=False)
            self.file.write(line + "\n")
            self.file.flush()

    async def stop(self):

        if self.file is None:
            return

        self._queue.put_nowait({
            "type": "session_end",
            "session_id": self.session_id,
            "ended_at": self._now(),
            "comment_count": self.comment_count,
        })

        self._queue.put_nowait(None)
        await self._writer

        self.file.close()
        self.file = None
        self._queue = None
        self._writer = None

        print(f"JSONL session ended -> {self.path} ({self.comment_count} comments)")


jsonl_session = JsonlSession()
