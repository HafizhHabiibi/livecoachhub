from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class Comment:

    id: str

    tiktok_user_id: int
    username: str
    nickname: str
    sec_uid: str

    message: str

    received_at: datetime

    @classmethod
    def create(
        cls,
        tiktok_user_id,
        username,
        nickname,
        sec_uid,
        message,
    ):
        return cls(
            id=str(uuid4()),
            tiktok_user_id=tiktok_user_id,
            username=username,
            nickname=nickname,
            sec_uid=sec_uid,
            message=message,
            received_at=datetime.now(),
        )