"""
Log in with ANY of: WhatsApp number, username, or email.

Django calls authenticate(request, username=<what was typed>, password=...).
We work out which of the three it is, find the user, and check the password.
"""
from django.contrib.auth.backends import ModelBackend

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


class PhoneUsernameEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = find_user(username or kwargs.get("phone"))
        if user is None:
            User().set_password(password)   # spend the same time as a real check, so timing doesn't reveal accounts
            return None
        if user.check_password(password) and self.user_can_authenticate(user):   # inactive users can't log in
            return user
        return None
