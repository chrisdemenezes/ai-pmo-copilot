"""Argon2id password hashing (TDS Epic 2, Section 13; AR-001 item 8).

Parameters follow the OWASP Password Storage Cheat Sheet's Argon2id
profile for a general web application without dedicated hashing hardware.
Each is overridable via environment variable so production hardware can
be tuned without a code change. The Argon2 hash string is self-describing
(algorithm, version, cost parameters, and salt are embedded in it), so no
separate salt column or parameter column is needed on `users`.
"""
import os

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from src.services.identity.interfaces import CredentialVerifier


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


class Argon2PasswordHasher(CredentialVerifier):
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=_int_env("ARGON2_TIME_COST", 3),
            memory_cost=_int_env("ARGON2_MEMORY_COST", 65536),
            parallelism=_int_env("ARGON2_PARALLELISM", 4),
            hash_len=32,
            salt_len=16,
        )

    def hash(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)

    def verify(self, plain_password: str, stored_hash: str) -> bool:
        # VerifyMismatchError (wrong password) is a VerificationError
        # subclass; InvalidHashError covers a stored value that isn't a
        # well-formed Argon2 hash at all -- both mean "not authenticated",
        # never a 500.
        try:
            return self._hasher.verify(stored_hash, plain_password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, stored_hash: str) -> bool:
        return self._hasher.check_needs_rehash(stored_hash)
