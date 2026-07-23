"""Single normalization rule for user email addresses (User Management,
Wave 2). Reused wherever an email is written or looked up, so storage and
lookups always agree on what "the same email" means -- never duplicated
inline.
"""


def normalize_email(email: str) -> str:
    return email.strip().lower()
