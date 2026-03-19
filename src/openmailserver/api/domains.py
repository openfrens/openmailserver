from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key
from openmailserver.schemas import DomainAttachRequest, DomainStatusResponse, DomainVerifyRequest
from openmailserver.security import ADMIN_SCOPE, DEBUG_READ_SCOPE
from openmailserver.services.domain_service import (
    DomainError,
    DomainNotFoundError,
    attach_domain,
    get_domain_status,
    list_domains,
    verify_domain,
)

router = APIRouter()


@router.get("/domains", response_model=list[DomainStatusResponse])
def domains_list(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> list[DomainStatusResponse]:
    return list_domains(db)


@router.post("/domains/attach", response_model=DomainStatusResponse)
def attach(
    payload: DomainAttachRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> DomainStatusResponse:
    try:
        return attach_domain(db, payload)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/domains/{name}", response_model=DomainStatusResponse)
def status(
    name: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DomainStatusResponse:
    try:
        return get_domain_status(db, name)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/domains/{name}/verify", response_model=DomainStatusResponse)
def verify(
    name: str,
    payload: DomainVerifyRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> DomainStatusResponse:
    try:
        return verify_domain(db, name, payload)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
