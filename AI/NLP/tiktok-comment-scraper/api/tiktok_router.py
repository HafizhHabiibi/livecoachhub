from fastapi import APIRouter, HTTPException

from app.schemas.tiktok_schema import StartLiveRequest
from app.services.tiktok_service import tiktok_service

router = APIRouter(
    prefix="/live",
    tags=["TikTok Live"]
)


@router.post("/start")
async def start_live(request: StartLiveRequest):

    try:

        await tiktok_service.start(request.username)

        return {
            "message": "Live dimulai."
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/stop")
async def stop_live():

    await tiktok_service.stop()

    return {
        "message": "Live dihentikan."
    }


@router.get("/status")
async def status():

    return tiktok_service.status()