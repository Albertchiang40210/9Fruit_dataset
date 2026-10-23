import db_manager


def test_hash_roundtrip():
    h = db_manager.hash_password("secret")
    assert h.startswith("pbkdf2$")
    assert db_manager._check_password("secret", h)
    assert not db_manager._check_password("wrong", h)


def test_hash_is_salted():
    assert db_manager.hash_password("x") != db_manager.hash_password("x")


def test_legacy_plaintext_still_verifies():
    assert db_manager._check_password("abc", "abc")
    assert not db_manager._check_password("abd", "abc")
