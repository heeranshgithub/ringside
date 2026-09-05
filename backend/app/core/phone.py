"""Phone normalisation and validation.

Shared, because two callers now depend on the same rules: candidate import, which is
forgiving, and the dial-target flow, which decides what we are willing to ring. The
strictness lives here so those two can never drift apart.
"""

from __future__ import annotations

import re

from app.core.errors import ValidationFailed

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
DEFAULT_COUNTRY_CODE = "+91"

# Indian mobile numbers are ten digits opening 6-9. Landlines and service codes are not
# reachable by a voice agent in any useful way, so they are rejected rather than dialled.
INDIA_MOBILE = re.compile(r"^\+91[6-9]\d{9}$")


def normalize_phone(raw: str | None, *, default_cc: str = DEFAULT_COUNTRY_CODE) -> str | None:
    """Coerce human input to E.164. Returns None for empty input, raises on garbage.

    Accepts the shapes people actually type: "9876543210", "+91 98765 43210",
    "098765-43210", "(+91) 98765 43210", "0091 98765 43210".
    """
    if raw is None or not str(raw).strip():
        return None

    digits = re.sub(r"[^\d+]", "", str(raw).strip())
    # a plus anywhere but the front is noise, not a country code
    digits = ("+" if digits.startswith("+") else "") + digits.replace("+", "")

    if digits.startswith("00"):
        digits = "+" + digits[2:]

    if not digits.startswith("+"):
        bare = digits.lstrip("0")
        if len(bare) == 10:
            digits = default_cc + bare
        elif len(bare) > 10:
            digits = "+" + bare
        else:
            raise ValidationFailed(f"'{raw}' is too short to be a phone number")

    if not E164.match(digits):
        raise ValidationFailed(f"'{raw}' is not a valid phone number")
    return digits


def assert_dialable(number: str) -> str:
    """Stricter gate for a number we are about to actually ring.

    Everything `normalize_phone` accepts can be stored; only what passes here gets called.
    """
    national = number[3:] if number.startswith("+91") else number.lstrip("+")

    if len(set(national)) == 1:
        raise ValidationFailed("That number is a single repeated digit")

    if number.startswith("+91") and not INDIA_MOBILE.match(number):
        raise ValidationFailed("Indian mobile numbers are ten digits starting with 6, 7, 8 or 9")
    return number


def mask(number: str | None) -> str:
    """Enough to recognise your own number, not enough to read someone else's."""
    if not number:
        return "—"
    if len(number) <= 6:
        return "•" * len(number)
    return f"{number[:3]}{'•' * (len(number) - 6)}{number[-3:]}"


def pretty(number: str) -> str:
    """+919876543210 -> +91 98765 43210, for echoing input back to the person typing it."""
    if INDIA_MOBILE.match(number):
        return f"+91 {number[3:8]} {number[8:]}"
    return number
