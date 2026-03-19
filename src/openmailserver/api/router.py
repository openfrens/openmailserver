from fastapi import APIRouter

from openmailserver.api import debug, domains, health, mail, mailboxes

router = APIRouter()
router.include_router(health.router)
router.include_router(domains.router, prefix="/v1")
router.include_router(mailboxes.router, prefix="/v1")
router.include_router(mail.router, prefix="/v1")
router.include_router(debug.router, prefix="/v1")
