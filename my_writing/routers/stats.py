from fastapi import APIRouter

from ..config import DIMENSIONS
from ..services import collect_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def stats():
    data = collect_stats()
    data["dimensions"] = DIMENSIONS
    return data
