from fastapi import APIRouter, Depends

from app.api.v1.rate_limit import enforce_rate_limit

router = APIRouter(tags=["v1"])


@router.get("/resource", dependencies=[Depends(enforce_rate_limit)])
async def get_resource() -> dict[str, str]:
    return {"message": "ScalePulse payload", "status": "success"}
