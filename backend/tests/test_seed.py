"""Regression test for a real bug found while manually exercising the app:
seed.py previously generated demo accounts on the '@predictwise.test'
domain, but '.test' is an IANA/RFC 2606 reserved special-use TLD that
pydantic's EmailStr (schemas.py::LoginRequest/RegisterRequest) rejects as
a syntax-level validation failure — meaning every demo account the seed
script created could be inserted directly via the ORM but could never
actually log in through the real `/api/v1/auth/login` endpoint. This test
would have caught that regression immediately: it validates every email
seed.py would generate through the exact same pydantic schema the login
route uses, rather than only checking that the ORM insert succeeds (which
it always did — the ORM has no email-format validation of its own).
"""
from pydantic import ValidationError

from backend.schemas import LoginRequest
from backend.seed import DEMO_EMAIL_DOMAIN


def _assert_passes_login_schema(email: str):
    try:
        LoginRequest(email=email, password="irrelevant-for-this-check")
    except ValidationError as exc:
        raise AssertionError(f"{email!r} failed EmailStr validation: {exc}") from exc


class TestSeedEmailsPassRealValidation:
    def test_admin_email_is_a_valid_login_email(self):
        _assert_passes_login_schema(f"admin@{DEMO_EMAIL_DOMAIN}")

    def test_teacher_and_parent_email_patterns_are_valid_login_emails(self):
        for prefix in ("teacher", "parent"):
            for i in range(1, 4):
                _assert_passes_login_schema(f"{prefix}{i}@{DEMO_EMAIL_DOMAIN}")

    def test_demo_domain_is_not_a_reserved_special_use_tld(self):
        """Guards against a regression back to '.test'/'.example'/
        '.invalid'/'.localhost' specifically, even if someone changes
        DEMO_EMAIL_DOMAIN to something else reserved in the future."""
        reserved_tlds = {"test", "example", "invalid", "localhost"}
        tld = DEMO_EMAIL_DOMAIN.rsplit(".", 1)[-1]
        assert tld not in reserved_tlds
