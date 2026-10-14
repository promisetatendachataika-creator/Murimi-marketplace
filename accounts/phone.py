"""
normalize_phone: one way to write every Zimbabwe mobile number, the same rule as the Hub.

    "0771 234 567"      -> "+263771234567"
    "771234567"         -> "+263771234567"
    "263 77 123 4567"   -> "+263771234567"
    "+263-77-123-4567"  -> "+263771234567"
    "00263771234567"    -> "+263771234567"
    "12345"             -> ValueError

Zimbabwe mobile numbers are +263 7X XXX XXXX: "+263", then 9 digits starting with 7.
"""
import re

_PHONE_RE = re.compile(r"^\+2637\d{8}$")


def normalize_phone(raw):
    """Return the number as +2637XXXXXXXX, or raise ValueError if it isn't a Zimbabwe mobile."""
    if raw is None:
        raise ValueError("No phone number.")
    p = re.sub(r"[\s\-().]", "", str(raw))
    if p.startswith("00"):
        p = "+" + p[2:]
    if p.startswith("263"):
        p = "+" + p
    if p.startswith("0"):
        p = "+263" + p[1:]
    if re.fullmatch(r"7\d{8}", p):
        p = "+263" + p
    if not _PHONE_RE.match(p):
        raise ValueError("Enter a Zimbabwe mobile number, like 077 123 4567.")
    return p


def try_normalize_phone(raw):
    """Like normalize_phone, but returns None instead of raising."""
    try:
        return normalize_phone(raw)
    except ValueError:
        return None


def pretty_phone(p):
    """+263771234567 -> +263 77 123 4567 (for showing to people)."""
    m = re.fullmatch(r"\+263(\d{2})(\d{3})(\d{4})", p or "")
    return f"+263 {m.group(1)} {m.group(2)} {m.group(3)}" if m else p
