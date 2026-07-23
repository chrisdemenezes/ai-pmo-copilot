"""Authorization Layer contract (Wave 2, Sprint 3; `DOMAIN-BLUEPRINT-RBAC.md`).

Same shape as `src/services/identity/interfaces.py`'s `CredentialVerifier`/
`IdentityResolver`: one Protocol, one method, no inheritance hierarchy.
`SqlPermissionChecker` (`checker.py`) is the only implementation today; the
Protocol exists so a future implementation (e.g. a cached/denormalized
checker) can replace it without touching `require_permission()` or any
route.
"""
from typing import Protocol


class PermissionChecker(Protocol):
    def has_permission(self, user_id: int, permission: str) -> bool: ...
