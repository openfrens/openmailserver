from fastapi import APIRouter

from openmailserver.schemas import HealthResponse
from openmailserver.services.debug_service import health_report

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(**health_report())
