from __future__ import annotations

from openmailserver import security


def test_generate_secret_and_api_key_have_expected_shape():
    secret = security.generate_secret(12)
    generated = security.generate_api_key(prefix="mailbox")

    assert len(secret) >= 12
    assert generated.raw_key.startswith("mailbox_")
    assert generated.hashed_key == security.hash_api_key(generated.raw_key)


def test_hash_and_verify_helpers_cover_api_keys_and_passwords():
    key_hash = security.hash_api_key("plain-key")
    password_hash = security.hash_mailbox_password("top-secret")

    assert security.verify_api_key("plain-key", key_hash) is True
    assert security.verify_api_key("wrong-key", key_hash) is False
    assert password_hash.startswith("{BLF-CRYPT}")
    assert security.verify_mailbox_password("top-secret", password_hash) is True
    assert security.verify_mailbox_password("wrong", password_hash) is False


def test_redaction_scope_parsing_and_scope_checks():
    redacted = security.redact_text(
        "api_key=abcdef123456 password: hunter2 authorization: bearer secret-token"
    )

    assert security.redact_value(None) == ""
    assert security.redact_value("short") == "***"
    assert security.redact_value("abcdefghij") == "abc***hij"
    assert "***REDACTED***" in redacted
    assert security.parse_scopes("mail:read, admin, mail:read") == ["admin", "mail:read"]
    assert security.parse_scopes([" mail:send ", "*", ""]) == ["*", "mail:send"]
    assert security.scopes_include("mail:read", ["mail:read"]) is True
    assert security.scopes_include("mail:read", ["*"]) is True
    assert security.scopes_include("mail:read", ["admin"]) is True
    assert security.scopes_include("mail:read", ["mail:send"]) is False
