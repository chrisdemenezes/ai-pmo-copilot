from src.services.identity.password_hashing import Argon2PasswordHasher


def test_hash_produces_different_strings_for_the_same_password():
    hasher = Argon2PasswordHasher()
    h1 = hasher.hash("correct horse battery staple")
    h2 = hasher.hash("correct horse battery staple")
    assert h1 != h2  # random salt per hash


def test_verify_accepts_the_correct_password():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct horse battery staple")
    assert hasher.verify("correct horse battery staple", stored) is True


def test_verify_rejects_any_other_password():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct horse battery staple")
    assert hasher.verify("wrong", stored) is False


def test_verify_rejects_malformed_hash_without_raising():
    hasher = Argon2PasswordHasher()
    assert hasher.verify("anything", "not-a-real-argon2-hash") is False


def test_needs_rehash_is_false_for_a_hash_from_current_parameters():
    hasher = Argon2PasswordHasher()
    stored = hasher.hash("correct horse battery staple")
    assert hasher.needs_rehash(stored) is False


def test_needs_rehash_is_true_when_parameters_changed(monkeypatch):
    monkeypatch.setenv("ARGON2_TIME_COST", "2")
    old_hasher = Argon2PasswordHasher()
    stored = old_hasher.hash("correct horse battery staple")

    monkeypatch.setenv("ARGON2_TIME_COST", "4")
    new_hasher = Argon2PasswordHasher()
    assert new_hasher.needs_rehash(stored) is True
