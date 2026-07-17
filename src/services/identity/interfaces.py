"""Identity Layer contracts (AR-001 item 3). Argon2/local is the only
implementation in this epic; a future SSO/OAuth/LDAP provider (Release
0.2+) implements the same protocols without changing AuthService or any
consumer of RequestContext.
"""
from typing import Protocol

from src.services.identity.models import AuthenticatedUser


class CredentialVerifier(Protocol):
    def verify(self, plain_password: str, stored_hash: str) -> bool: ...

    def hash(self, plain_password: str) -> str: ...

    def needs_rehash(self, stored_hash: str) -> bool: ...


class IdentityResolver(Protocol):
    def resolve(self, email: str, password: str) -> AuthenticatedUser | None: ...
