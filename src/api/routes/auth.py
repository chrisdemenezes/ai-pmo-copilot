import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.rate_limiter import enforce_rate_limit
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.services.identity.auth_service import AuthService
from src.services.identity.password_hashing import Argon2PasswordHasher

logger = logging.getLogger(__name__)

# Server-to-server only (BFF -> backend), same as every other route in this
# API -- never called directly by the browser.
router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


class LoginRequest(BaseModel):
    # Stable external organization identifier (EO-015 Organizational
    # Identity Scope Correction) -- resolution is organization + email, a
    # global email search across organizations is never performed.
    organization: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    user_id: int
    organization_id: int
    # Server-minted session id (item 5, resolves TD-010) -- the BFF signs
    # this into its HMAC cookie instead of generating its own, so the
    # backend's `sessions` table can list/revoke it before natural expiry.
    session_id: str


class LogoutRequest(BaseModel):
    session_id: str
    user_id: int


class LogoutResponse(BaseModel):
    acknowledged: bool = True


@lru_cache
def build_repository() -> AnalysisRepository:
    return AnalysisRepository()


@lru_cache
def build_auth_service() -> AuthService:
    # Reuses the same engine/session factory as every other repository in
    # the app (build_repository) -- no parallel database connection.
    repository = build_repository()
    return AuthService(repository.SessionLocal, Argon2PasswordHasher())


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, auth_service: AuthService = Depends(build_auth_service)):
    result = auth_service.authenticate(request.organization, request.email, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid organization, email or password")
    user, organization = result
    session_id = auth_service.create_session(
        user_id=user.user_id, organization_id=organization.organization_id
    )
    return LoginResponse(
        user_id=user.user_id,
        organization_id=organization.organization_id,
        session_id=session_id,
    )


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(request: LogoutRequest, auth_service: AuthService = Depends(build_auth_service)):
    auth_service.logout(session_id=request.session_id, user_id=request.user_id)
    return LogoutResponse()
