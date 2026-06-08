"""Health check endpoint"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}
