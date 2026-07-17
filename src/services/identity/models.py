"""Identity model -- objects propagated through the application, never raw
IDs (Architecture Review AR-001, item 1). All immutable: resolving them
(querying the database) is auth_service's job, not theirs.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    email: str
    display_name: str
    identity_type: str = "standard"  # "standard" | "demo" (AR-001 item 5)

    @property
    def is_demo(self) -> bool:
        return self.identity_type == "demo"


@dataclass(frozen=True)
class OrganizationIdentity:
    organization_id: int
    name: str
    # Stable external identifier -- what login/APIs/integrations address the
    # organization by (EO-015 Organizational Identity Scope Correction).
    # Prepared for future organizational_unit/department/team/competency/
    # roles/permissions fields (out of scope for this épico) without adding
    # unused placeholders now.
    slug: str


@dataclass(frozen=True)
class SessionIdentity:  # AR-001 item 2
    session_id: str
    # The BFF is the source of truth for expiry (it owns the signed cookie
    # payload and TTL) and always sets this. The backend reconstructs
    # RequestContext from headers alone, which do not carry expiry
    # (Institutional Headers, TDS Section 10/15.6, unchanged by this
    # implementation) -- it is not the source of truth for session expiry,
    # so it leaves this unset rather than fabricate a value.
    expires_at: datetime | None = None


@dataclass(frozen=True)
class RequestContext:
    user: AuthenticatedUser
    organization: OrganizationIdentity
    session: SessionIdentity
    request_id: str
