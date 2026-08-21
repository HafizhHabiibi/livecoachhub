from pydantic import BaseModel


class StartLiveRequest(BaseModel):
    username: str