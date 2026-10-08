from fastapi import APIRouter

router = APIRouter(tags=["v1"])


@router.get("/resource")
async def get_resource() -> dict[str, str]:
    return {"message": "ScalePulse payload", "status": "success"}
