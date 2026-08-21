from TikTokLive.events import CommentEvent

from app.models.comment import Comment
from app.services.broadcast_service import broadcast_service
from app.services.jsonl_service import jsonl_session


class CommentService:

    async def process(self, comment: Comment, event: CommentEvent):

        print("=" * 50)
        print(f"ID       : {comment.id}")
        print(f"Username : {comment.username}")
        print(f"Nickname : {comment.nickname}")
        print(f"Comment  : {comment.message}")
        print(f"Time     : {comment.received_at}")
        print("=" * 50)

        common = getattr(event, "common", None)
        timestamp = common.create_time if common else None

        jsonl_session.write(
            "comment",
            timestamp=timestamp,
            text=comment.message,
        )

        jsonl_session.comment_count += 1

        await broadcast_service.broadcast({
            "type": "comment",
            "session_id": jsonl_session.session_id,
            "nickname": comment.nickname,
            "username": comment.username,
            "message": comment.message,
            "received_at": comment.received_at.isoformat(timespec="seconds"),
            "comment_count": jsonl_session.comment_count,
        })


comment_service = CommentService()
