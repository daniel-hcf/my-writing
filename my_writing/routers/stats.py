from fastapi import APIRouter, HTTPException

from ..config import DIMENSIONS
from ..services import collect_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def stats(mode: str = "all"):
    try:
        data = collect_stats(mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    data["dimensions"] = DIMENSIONS
    data["mode"] = mode
    return data
