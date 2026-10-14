"""
Log in with ANY of: WhatsApp number, username, or email.

Django calls authenticate(request, username=<what was typed>, password=...).
We work out which of the three it is, find the user, and check the password.
"""
import hashlib

from django.contrib.auth.backends import ModelBackend

from core.http import clear_failures, client_ip, record_failure, too_many_failures

from .models import User
from .phone import try_normalize_phone


def find_user(identifier):
    """Find a user from what they typed in the log-in box, or None."""
    text = (identifier or "").strip()
    if not text:
        return None
    if "@" in text:                                         # looks like an email
        return User.objects.filter(email=text.lower()).first()
    phone = try_normalize_phone(text)
    if phone:                                               # looks like a phone number
        return User.objects.filter(phone=phone).first()
    return User.objects.filter(username=text.lower()).first()   # otherwise a username


# Only WRONG tries count: 5 per account, 20 per network address, within 15 minutes.
# (A farmer logging in on two phones in one morning must not be locked out.)
# This is counted here, in the one place every log-in passes through, so the staff
# page at /admin/ is protected exactly like the website.
LOGIN_LIMIT = 5
LOGIN_WINDOW = 15 * 60


def login_keys(request, identifier, user=None):
    """Cache keys for the failure counts. Counted per ACCOUNT (so "0771234567", "077 123 4567" and the
    username all share one count) and per network address."""
    if user is None:
        user = find_user(identifier)
    who = f"user-{user.pk}" if user else "typed-" + hashlib.sha256((identifier or "").strip().lower().encode()).hexdigest()[:24]
    return f"login-fail:{who}", f"login-fail-ip:{client_ip(request) if request else 'none'}"


def locked_out(request, identifier):
    account, address = login_keys(request, identifier)
    return too_many_failures(account, LOGIN_LIMIT) or too_many_failures(address, LOGIN_LIMIT * 4)


class PhoneUsernameEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("phone")
        user = find_user(identifier)
        account, address = login_keys(request, identifier, user)
        if too_many_failures(account, LOGIN_LIMIT) or too_many_failures(address, LOGIN_LIMIT * 4):
            return None                      # even the right password is refused until the window ends
        if user is None:
            User().set_password(password)   # spend the same time as a real check, so timing doesn't reveal accounts
        elif user.check_password(password) and self.user_can_authenticate(user):   # inactive users can't log in
            clear_failures(account)          # a correct log-in wipes this account's count
            return user
        record_failure(account, LOGIN_WINDOW)
        record_failure(address, LOGIN_WINDOW)
        return None
